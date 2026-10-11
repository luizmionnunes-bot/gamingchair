"""emit.py — from per-instruction IR to structured Lua text for every proto.

pipeline per proto:
  nodes      NEXT -> GOTO; computed jumps resolved by constant propagation
  merge      straight-line chains fused into blocks
  structure  loops / if-else (structure.py)
  cleanup    expression rebuilding (cleanup.py)
  render     nested closures rendered inline as `function(...) ... end`
"""
import sys
from collections import defaultdict
import structure
import cleanup
from irfmt import Fmt

sys.setrecursionlimit(1000000)

def to_nodes(ir):
    nodes = {}
    for pc, st in ir.items():
        if st is None:
            nodes[pc] = [('ERRPATH', 'not lifted')]
            continue
        nodes[pc] = conv(st)
    resolve_gotox(nodes)
    return nodes

def conv(stmts):
    out = []
    for s in stmts:
        h = s[0]
        if h == 'NEXT': out.append(('GOTO', s[1]))
        elif h == 'GOTOX': out.append(('GOTOX', s[1]))
        elif h == 'IF': out.append(('IF', s[1], conv(s[2]), conv(s[3])))
        elif h == 'LOOPEND': continue
        elif h in ('WHILE',): out.append((h, s[1], conv(s[2])))
        elif h == 'FOR': out.append((h, s[1], s[2], s[3], s[4], conv(s[5])))
        elif h == 'REPEAT': out.append((h, conv(s[1]), s[2], conv(s[3])))
        else: out.append(s)
    return out

def resolve_gotox(nodes):
    """GOTOX (R n + 1): the register holds a constant set on the unique path before"""
    preds = defaultdict(list)
    for n, st in nodes.items():
        for t in structure.term_targets(st): preds[t].append(n)
    for n, st in nodes.items():
        if not st or st[-1][0] != 'GOTOX': continue
        e = st[-1][1]
        if not (e[0] == 'BIN' and e[1] == '+' and e[2][0] == 'R' and e[3][0] == 'K'): continue
        reg, add = e[2], e[3][1]
        val = find_const(nodes, preds, n, reg, st[:-1])
        if isinstance(val, int):
            st[-1] = ('GOTO', val + add)

def find_const(nodes, preds, n, reg, prefix):
    seen = set()
    cur, body = n, prefix
    while True:
        for s in reversed(body):
            if s[0] == 'SET' and s[1] == reg:
                return s[2][1] if s[2][0] == 'K' else None
        ps = preds.get(cur, [])
        if len(ps) != 1 or ps[0] in seen: return None
        seen.add(cur)
        cur = ps[0]; body = nodes[cur]

def merge_chains(nodes, entry):
    preds = defaultdict(list)
    for n, st in nodes.items():
        for t in structure.term_targets(st): preds[t].append(n)
    changed = True
    while changed:
        changed = False
        for n in list(nodes):
            if n not in nodes: continue
            st = nodes[n]
            while st and st[-1][0] == 'GOTO':
                t = st[-1][1]
                if t == entry or t == n or t not in nodes or len(preds[t]) != 1: break
                st = st[:-1] + nodes.pop(t)
                for x in structure.term_targets(st): preds[x] = [n if p == t else p for p in preds[x]]
                changed = True
            nodes[n] = st
    return nodes

class Emitter:
    def __init__(self, lifter):
        self.L = lifter
        self.cache = {}
        self.report = {'gotos': 0, 'protos': 0, 'errpaths': 0}

    def proto_body(self, p):
        ir, errs = self.L.lift_proto(p)
        nodes = to_nodes(ir)
        nodes = merge_chains(nodes, 1)
        out, S = structure.structure(nodes, 1)
        self.report['gotos'] += S.gotos
        self.report['protos'] += 1
        out = cleanup.run(out, p)
        return out

    def render(self, p, ind='', capnames=None):
        body = self.proto_body(p)
        F = ProtoFmt(self, p, capnames or {})
        params = ['a%d' % i for i in range(1, p.nparams + 1)]
        uses_va = cleanup.uses_varargs(body)
        if uses_va or True: params.append('...')
        head = 'function(' + ', '.join(params) + ')'
        decl = cleanup.declare(body, p)
        text = head + '\n'
        if decl: text += ind + '    local ' + ', '.join(F.e(d) for d in decl) + '\n'
        text += F.block(body, ind + '    ')
        text += ind + 'end'
        return text

class ProtoFmt(Fmt):
    def __init__(self, em, p, capnames):
        super().__init__()
        self.em, self.p, self.capnames = em, p, capnames
        self.ind = ''
        for i in range(1, p.nparams + 1): self.names[('R', i)] = 'a%d' % i
        for i, nm in capnames.items(): self.names[('U', i)] = nm

    def e(self, x, prec=0):
        if x[0] == 'CONTAINER':
            return {'regs': '__VM_REGS', 'code': '__VM_CODE', 'consts': '__VM_CONSTS'}.get(x[1], '__VM_' + x[1].upper())
        if x[0] == 'FN' and x[1] == 'shared118': return '__VM_SHARED'
        if x[0] == 'CLOSURE':
            sub = x[1]
            caps = x[2][1] if x[2][0] == 'CAPS' else []
            names = {}
            for i, c in enumerate(caps, 1):
                names[i] = super().e(c) if c[0] in ('R', 'U', 'T') else '(' + super().e(c) + ')'
                names[i] = self.e(c)
            return self.em.render(sub, self.ind, names)
        return super().e(x, prec)

    def s(self, st, ind=''):
        self.ind = ind
        if st[0] == 'LABEL': return ind + '::L%s::\n' % st[1]
        if st[0] == 'GOTO': return ind + 'goto L%s\n' % st[1]
        return super().s(st, ind)
