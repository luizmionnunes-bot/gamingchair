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
import multret
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
    # jumps outside the code (anti-tamper): the VM crashes indexing v1[pc]
    def fix(st):
        out = []
        for x in st:
            if x[0] == 'GOTO' and x[1] not in nodes: out.append(('CRASH', x[1]))
            elif x[0] == 'IF': out.append(('IF', x[1], fix(x[2]), fix(x[3])))
            else: out.append(x)
        return out
    for n in list(nodes): nodes[n] = fix(nodes[n])
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

def apply_multret(nodes):
    for n in list(nodes):
        nodes[n] = multret.finalize(multret.rewrite(nodes[n]))
    # `top` is dead once no consumer reads it
    reads = [False]
    def f(x):
        if isinstance(x, tuple) and x and isinstance(x[0], str):
            if x[0] == 'SET' and x[1] == ('TOP',): f(x[2]); return
            if x == ('TOP',): reads[0] = True
            for y in x[1:]: f(y)
        elif isinstance(x, list):
            for y in x: f(y)
    f(list(nodes.values()))
    if not reads[0]:
        def drop(st):
            out = []
            for s in st:
                if s[0] == 'SET' and s[1] == ('TOP',): continue
                if s[0] == 'IF': s = ('IF', s[1], drop(s[2]), drop(s[3]))
                elif s[0] == 'WHILE': s = ('WHILE', s[1], drop(s[2]))
                out.append(s)
            return out
        for n in nodes: nodes[n] = drop(nodes[n])
    return nodes

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
        self.vmdata = set()

    def proto_body(self, p):
        ir, errs = self.L.lift_proto(p)
        nodes = to_nodes(ir)
        nodes = apply_multret(merge_chains(nodes, 1))
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


# ------------------------------------------------------------------ runnable
RUNTIME = r'''
local __VM_SHARED = {}
local __VM_REGS = {}
local __unpack = table.unpack or unpack
'''

class RunFmt(Fmt):
    """executable rendering with VM-exact semantics (for differential testing)"""
    def __init__(self, em, p):
        super().__init__()
        self.em, self.p = em, p
        self.ind = ''
    def e(self, x, prec=0):
        h = x[0]
        if h == 'R': return 'R[%d]' % x[1]
        if h == 'S': return 'S[%d]' % x[1]
        if h == 'U': return 'U[%d]' % x[1]
        if h == 'UX': return 'U[' + self.e(x[1]) + ']'
        if h == 'VA': return 'va[' + self.e(x[1]) + ']'
        if h == 'NVA': return 'nva'
        if h == 'CONTAINER':
            if x[1] in ('code', 'consts'):
                self.em.vmdata.add(self.p.id)
                return '__VM_%s[%d]' % (x[1].upper(), self.p.id)
            return {'regs': 'R'}.get(x[1], '__VM_' + x[1])
        if h == 'FN':
            if x[1] == 'shared118': return '__VM_SHARED'
            if x[1] == 'unpack': return '__unpack'
            if x[1] in ('band', 'bor', 'bnot', 'bxor', 'lshift', 'rshift'): return 'bit32.' + x[1]
            return x[1]
        if h == 'PACKN':
            return 'packn(' + ', '.join(self.e(a) for a in x[1]) + ')'
        if h == 'UNPACKSTACK':
            return '__unpack(S, %s, %s)' % (self.e(x[1]), self.e(x[2]))
        if h == 'GENITER':
            vs = ', '.join('i%d' % i for i in range(1, x[2] + 1))
            return 'coroutine.wrap(function() for %s in %s do coroutine.yield(true, %s) end end)' % (vs, ', '.join(self.e(a) for a in x[1]), vs)
        if h == 'CLOSURE':
            caps = x[2][1] if x[2][0] == 'CAPS' else []
            return '(%s)({%s})' % (self.em.render_run(x[1], self.ind), ', '.join(self.e(c) for c in caps))
        if h == 'NATIVE':
            return '__NATIVE[%d](%s)' % (x[1], ', '.join(self.e(a) for a in x[2]))
        if h == 'CAPS':
            return '{' + ', '.join(self.e(a) for a in x[1]) + '}'
        if h == 'VMVAR': return 'vm_' + x[1]
        if h == 'T': return 'T[%d]' % x[1]
        if h == 'L': return x[1]
        if h == 'IDX' and x[1] == ('ENV',):
            return '_E[' + self.e(x[2]) + ']'
        return super().e(x, prec)
    def s(self, st, ind=''):
        self.ind = ind
        if st[0] == 'LABEL': return ind + '::L%s::\n' % st[1]
        if st[0] == 'GOTO': return ind + 'goto L%s\n' % st[1]
        if st[0] == 'CLOSEUPV': return ''
        if st[0] == 'LOCAL': return ind + self.e(st[1]) + ' = ' + self.e(st[2]) + '\n'
        if st[0] == 'LOCALS': return ind + ', '.join(self.e(t) for t in st[1]) + ' = ' + self.e(st[2]) + '\n'
        if st[0] == 'FOR':
            v = '__i%d' % st[1][1]
            return (ind + 'for %s = %s, %s, %s do\n' % (v, self.e(st[2]), self.e(st[3]), self.e(st[4])) +
                    ind + '    T[%d] = %s\n' % (st[1][1], v) + self.block(st[5], ind + '    ') + ind + 'end\n')
        if st[0] == 'ERRPATH': return ind + 'error("devirt: unreachable path")\n'
        if st[0] == 'CRASH': return ind + 'error("attempt to index nil with number")  -- VM jump to invalid pc %d\n' % st[1]
        if st[0] == 'SETLISTM':
            return ind + 'do local __m = table.pack(%s) for __k = 1, __m.n do %s[%d + __k] = __m[__k] end end\n' % (self.e(st[2]), self.e(st[1]), st[3] - 1)
        return super().s(st, ind)

def render_run(self, p, ind=''):
    ir, errs = self.L.lift_proto(p)
    nodes = apply_multret(merge_chains(to_nodes(ir), 1))
    body, S = structure.structure(nodes, 1)
    if S.labels:
        body = dispatcher(nodes, 1)
    F = RunFmt(self, p)
    t = ['function(U) return function(...)']
    t.append(ind + '    local R, S, ret, va, nva = {}, {}, {}, {...}, select("#", ...)')
    t.append(ind + '    local acc, top, vm_v8, T = nil, nil, 0, {}')
    t.append(ind + '    local _E = __ENV')
    t.append(ind + '    local function packn(...) local n = select("#", ...) for i = 1, n do ret[i] = select(i, ...) end for j = n + 1, vm_v8 do ret[j] = nil end vm_v8 = n return n end')
    text = '\n'.join(t) + '\n' + F.block(body, ind + '    ') + ind + 'end end'
    return text
Emitter.render_run = render_run

def lua_lit(v):
    from irfmt import Fmt
    if isinstance(v, list): return '{' + ', '.join(lua_lit(x) for x in v) + '}'
    if hasattr(v, 'raw'): return '"<enc>"'
    if isinstance(v, dict):
        return '{' + ', '.join('[%s] = %s' % (lua_lit(k), lua_lit(x)) for k, x in v.items()) + '}'
    return Fmt().k(v)

def vm_data(em, protos):
    """instruction / constant tables for protos whose code inspects VM internals"""
    import model
    out = ['local __VM_CODE, __VM_CONSTS = {}, {}']
    for p in protos:
        if p.id not in em.vmdata: continue
        recs = []
        for pc in sorted(p.code):
            r = p.code[pc]
            recs.append('[%d] = {%s}' % (pc, ', '.join('[%d] = %s' % (k, lua_lit(model.arr(v))) for k, v in r.items())))
        out.append('__VM_CODE[%d] = {%s}' % (p.id, ', '.join(recs)))
        out.append('__VM_CONSTS[%d] = {%s}' % (p.id, ', '.join('[%d] = %s' % (k, lua_lit(c)) for k, c in sorted(p.consts.items()) if c is not None)))
    return '\n'.join(out) + '\n'

def dispatcher(nodes, entry):
    """exact unstructured form: while-loop over node ids (used when gotos remain)"""
    def conv(st):
        out = []
        for x in st:
            if x[0] == 'GOTO': out += [('SET', ('L', '__n'), ('K', x[1])), ('CONTINUE',)]
            elif x[0] == 'IF': out.append(('IF', x[1], conv(x[2]), conv(x[3])))
            else: out.append(x)
        return out
    chain = []
    for n in sorted(nodes):
        chain = [('IF', ('BIN', '==', ('L', '__n'), ('K', n)), conv(nodes[n]) + [('BREAK',)], chain)] if False else chain
    # build if/elseif chain
    cases = [(n, conv(nodes[n])) for n in sorted(nodes)]
    tree = [('RAW', 'error("devirt: bad state")')]
    for n, b in reversed(cases):
        tree = [('IF', ('BIN', '==', ('L', '__n'), ('K', n)), b, tree)]
    return [('RAW', 'local __n = %d' % entry), ('WHILE', ('K', True), tree)]


def lua_consts(C):
    """the VM's runtime constant table t[1] (captured after init) as a Lua literal"""
    import re as _re
    tree = {}
    for k, v in C.items():
        path = [int(x) for x in _re.findall(r'\[(\d+)\]', k)]
        if path[0] != 1: continue
        d = tree
        for p in path[:-1]:
            d = d.setdefault(p, {})
            if not isinstance(d, dict): break
        else:
            d[path[-1]] = v
    def ser(d):
        if isinstance(d, dict):
            return '{' + ', '.join('[%d] = %s' % (k, ser(v)) for k, v in sorted(d.items())) + '}'
        if isinstance(d, bool): return 'true' if d else 'false'
        return repr(d)
    return 'local t = {[1] = %s}\n' % ser(tree[1])
