"""final.py — readable *and runnable* Luau from the lifted IR.

Per prototype:
  lift -> nodes -> multret rewrite -> structure      (emit.py / structure.py)
  normalize    LOCAL/LOCALS -> assignments on variables
  prologue     parameter copy loop -> named parameters
  inline       single-def/single-use variables folded into their (adjacent) use,
               keeping Luau evaluation order
  scope        each variable declared `local` in the innermost block whose first
               occurrence is an unconditional assignment (per-iteration locals in
               loops stay per-iteration); forward declarations otherwise
  render       closures inline; captures by name when provably equivalent to the
               VM's by-value capture, otherwise through an IIFE
"""
import sys
from collections import defaultdict, Counter
import emit, structure, multret
from irfmt import Fmt

VARS = ('R', 'T', 'S', 'ACC')

def is_var(x): return isinstance(x, tuple) and x and x[0] in VARS

def walk(x, f):
    if isinstance(x, tuple) and x and isinstance(x[0], str):
        if f(x) is False: return
        for y in x[1:]:
            if isinstance(y, (tuple, list)): walk(y, f)
    elif isinstance(x, list):
        for y in x: walk(y, f)

# ---------------------------------------------------------------- normalize
def normalize(stmts):
    out = []
    for s in stmts:
        h = s[0]
        if h == 'LOCAL': out.append(('SET', s[1], s[2]))
        elif h == 'LOCALS': out.append(('MSET', list(s[1]), s[2]))
        elif h == 'IF': out.append(('IF', s[1], normalize(s[2]), normalize(s[3])))
        elif h == 'WHILE': out.append(('WHILE', s[1], normalize(s[2])))
        elif h == 'FOR': out.append(('FOR', s[1], s[2], s[3], s[4], normalize(s[5])))
        elif h == 'REPEAT': out.append(('REPEAT', normalize(s[1]), s[2], normalize(s[3])))
        elif h == 'SET' and s[1] == ('ACC',): out.append(('SET', ('ACC',), s[2]))
        else: out.append(s)
    return out

def strip_prologue(stmts, nparams):
    """drop `for t = 1, math.min(nva, nparams+1) do R[t] = va[t] end`"""
    if stmts and stmts[0][0] == 'FOR':
        f = stmts[0]
        if len(f[5]) == 1 and f[5][0][0] == 'SET' and f[5][0][1][0] == 'RX' and f[5][0][2][0] == 'VA':
            return stmts[1:], True
    return stmts, False

# ---------------------------------------------------------------- def/use
def defs_uses(body):
    defs, uses = Counter(), Counter()
    def stmt(s):
        h = s[0]
        if h == 'SET':
            l = s[1]
            if is_var(l): defs[l] += 1
            else: walk(l, lambda x: uses.__setitem__(x, uses[x] + 1) if is_var(x) else None)
            expr(s[2])
        elif h == 'MSET':
            for t in s[1]:
                if is_var(t): defs[t] += 1
            expr(s[2])
        elif h == 'IF':
            expr(s[1]); [stmt(x) for x in s[2]]; [stmt(x) for x in s[3]]
        elif h == 'WHILE':
            expr(s[1]); [stmt(x) for x in s[2]]
        elif h == 'FOR':
            defs[s[1]] += 1; expr(s[2]); expr(s[3]); expr(s[4]); [stmt(x) for x in s[5]]
        elif h == 'REPEAT':
            [stmt(x) for x in s[3]]; [stmt(x) for x in s[1]]; expr(s[2])
        else:
            for y in s[1:]:
                if isinstance(y, (tuple, list)): expr(y)
    def expr(e):
        walk(e, lambda x: uses.__setitem__(x, uses[x] + 1) if is_var(x) else None)
    for s in body: stmt(s)
    return defs, uses

# ---------------------------------------------------------------- inlining
def eval_order(e, out):
    if not (isinstance(e, tuple) and e and isinstance(e[0], str)): return
    h = e[0]
    if h == 'CALL':
        eval_order(e[1], out)
        for a in e[2]: eval_order(a, out)
    elif h == 'BIN':
        eval_order(e[2], out); eval_order(e[3], out)
    elif h == 'IDX':
        eval_order(e[1], out); eval_order(e[2], out)
    elif h == 'NEWT':
        for it in e[1]:
            for y in it[1:]: eval_order(y, out)
    elif h in ('CAPS', 'MULTI'):
        for y in e[1]: eval_order(y, out)
    elif h == 'NATIVE':
        for y in e[2]: eval_order(y, out)
    elif h == 'CLOSURE':
        eval_order(e[2], out)
    else:
        for y in e[1:]:
            if isinstance(y, tuple): eval_order(y, out)
            elif isinstance(y, list):
                for z in y: eval_order(z, out)
    out.append(e)

def effects(e):
    found = [False]
    walk(e, lambda x: found.__setitem__(0, True) if x[0] in ('CALL', 'IDX', 'NATIVE', 'CLOSURE', 'NEWT', 'CAPS') else None)
    return found[0]

def reads_vars(e):
    s = set()
    walk(e, lambda x: s.add(x) if is_var(x) else None)
    return s

def stmt_order(st):
    out = []
    h = st[0]
    if h == 'SET':
        l = st[1]
        if l[0] == 'IDX': eval_order(l[1], out); eval_order(l[2], out)
        elif l[0] in ('RX', 'SX', 'UX'): eval_order(l[1], out)
        eval_order(st[2], out)
    elif h == 'MSET': eval_order(st[2], out)
    elif h == 'EXPR': eval_order(st[1], out)
    elif h == 'RETURN':
        for v in st[1]: eval_order(v, out)
    elif h == 'IF': eval_order(st[1], out)
    elif h == 'SETLISTM': eval_order(st[1], out); eval_order(st[2], out)
    else: return None
    return out

def occurs(x, v):
    found = [False]
    walk(x, lambda y: found.__setitem__(0, True) if y == v else None)
    return found[0]

def subst(e, v, val):
    if e == v: return val
    if isinstance(e, tuple):
        return tuple(subst(y, v, val) if isinstance(y, (tuple, list)) else y for y in e)
    if isinstance(e, list): return [subst(y, v, val) for y in e]
    return e

def in_lazy(st, v):
    """v occurs where it is evaluated later than the statement (GENITER args)"""
    found = [False]
    def f(x):
        if x[0] == 'GENITER' and occurs(x, v): found[0] = True
    walk(st, f)
    return found[0]

def can_inline_into(st, v, val):
    h = st[0]
    if in_lazy(st, v): return False
    if h in ('WHILE', 'FOR', 'REPEAT'): return False
    if h == 'IF':
        if occurs(st[2], v) or occurs(st[3], v) or not occurs(st[1], v): return False
    elif h == 'SET' and st[1] == v: return False
    elif h == 'MSET' and v in st[1]: return False
    order = stmt_order(st)
    if order is None: return False
    # nothing observable may run before v's position if val has effects; and no
    # variable read by val may be written before v's position (none can be: only
    # calls write memory, registers are local)
    if effects(val):
        for x in order:
            if x == v: break
            if x[0] in ('CALL', 'IDX', 'NATIVE', 'CLOSURE'): return False
    return True

def inline(body):
    while True:
        defs, uses = defs_uses(body)
        changed = [False]
        def blk(stmts):
            out = []
            for st in stmts:
                st = rec(st)
                out.append(st)
                while len(out) >= 2:
                    d, cur = out[-2], out[-1]
                    if d[0] != 'SET' or not is_var(d[1]): break
                    v = d[1]
                    if defs[v] != 1 or uses[v] != 1 or not occurs(cur, v): break
                    if v in reads_vars(d[2]): break
                    if not can_inline_into(cur, v, d[2]): break
                    out[-2:] = [subst_stmt(cur, v, d[2])]
                    changed[0] = True
            return out
        def rec(st):
            h = st[0]
            if h == 'IF': return ('IF', st[1], blk(st[2]), blk(st[3]))
            if h == 'WHILE': return ('WHILE', st[1], blk(st[2]))
            if h == 'FOR': return ('FOR', st[1], st[2], st[3], st[4], blk(st[5]))
            if h == 'REPEAT': return ('REPEAT', blk(st[1]), st[2], blk(st[3]))
            return st
        body = blk(body)
        if not changed[0]: return body

def subst_stmt(st, v, val):
    if st[0] == 'IF': return ('IF', subst(st[1], v, val), st[2], st[3])
    if st[0] == 'SET':
        l = st[1]
        return ('SET', l if l == v else subst(l, v, val), subst(st[2], v, val))
    if st[0] == 'MSET': return ('MSET', st[1], subst(st[2], v, val))
    return subst(st, v, val)

def drop_dead(body):
    """remove assignments to never-read variables whose value has no effects"""
    while True:
        defs, uses = defs_uses(body)
        changed = [False]
        def blk(stmts):
            out = []
            for st in stmts:
                h = st[0]
                if h == 'SET' and is_var(st[1]) and uses[st[1]] == 0 and not effects(st[2]):
                    changed[0] = True; continue
                if h == 'SET' and is_var(st[1]) and uses[st[1]] == 0 and st[2][0] == 'CALL':
                    out.append(('EXPR', st[2])); changed[0] = True; continue
                if h == 'IF': st = ('IF', st[1], blk(st[2]), blk(st[3]))
                elif h == 'WHILE': st = ('WHILE', st[1], blk(st[2]))
                elif h == 'FOR': st = ('FOR', st[1], st[2], st[3], st[4], blk(st[5]))
                elif h == 'REPEAT': st = ('REPEAT', blk(st[1]), st[2], blk(st[3]))
                out.append(st)
            return out
        body = blk(body)
        if not changed[0]: return body

# ---------------------------------------------------------------- scoping
def scope(body, params):
    """decide where each variable is declared. Returns new body with
    ('LOCALSET', v, e) / ('LOCALMSET', [v], e) / ('DECL', [v]) statements."""
    # occurrences: var -> list of block paths (tuple of ids)
    occ = defaultdict(set)
    blocks = {}
    nid = [0]
    def visit(stmts, path):
        bid = nid[0]; nid[0] += 1
        blocks[bid] = stmts
        p = path + (bid,)
        for st in stmts:
            vs = set()
            sub = []
            h = st[0]
            if h == 'IF': walk(st[1], lambda x: vs.add(x) if is_var(x) else None); sub = [st[2], st[3]]
            elif h == 'WHILE': walk(st[1], lambda x: vs.add(x) if is_var(x) else None); sub = [st[2]]
            elif h == 'FOR':
                walk(st[2:5], lambda x: vs.add(x) if is_var(x) else None); sub = [st[5]]
            elif h == 'REPEAT': sub = [st[3] + st[1]]; walk(st[2], lambda x: vs.add(x) if is_var(x) else None)
            else: walk(st, lambda x: vs.add(x) if is_var(x) else None)
            for v in vs: occ[v].add(p)
            if h == 'FOR':
                occ[st[1]].add(p + ('for%d' % id(st),))
            for b in sub: visit(b, p)
    visit(body, ())
    decl_at = {}
    for v, paths in occ.items():
        if v in params: continue
        common = list(min(paths, key=len))
        for pth in paths:
            k = 0
            while k < len(common) and k < len(pth) and common[k] == pth[k]: k += 1
            common = common[:k]
        decl_at[v] = tuple(common)
    return decl_at, blocks

def loop_blocks(body):
    """ids of blocks that are loop bodies (same numbering as scope())"""
    res = set()
    nid = [0]
    def visit(stmts, isloop):
        bid = nid[0]; nid[0] += 1
        if isloop: res.add(bid)
        for st in stmts:
            h = st[0]
            if h == 'IF': visit(st[2], False); visit(st[3], False)
            elif h == 'WHILE': visit(st[2], True)
            elif h == 'FOR': visit(st[5], True)
            elif h == 'REPEAT': visit(st[3] + st[1], True)
    visit(body, False)
    return res

def first_is_def(stmts, v):
    for st in stmts:
        vs = set()
        walk(st, lambda x: vs.add(x) if is_var(x) else None)
        if v in vs:
            return (st[0] == 'SET' and st[1] == v and v not in reads_vars(st[2])) or \
                   (st[0] == 'MSET' and v in st[1] and not (reads_vars(st[2]) & set(st[1])))
    return False

def place_decls(body, params):
    decl_at, blocks = scope(body, params)
    loops = loop_blocks(body)
    for v, path in list(decl_at.items()):
        if not path: continue
        if first_is_def(blocks[path[-1]], v): continue
        # forward declaration: must not be inside any loop body
        k = len(path)
        for j, b in enumerate(path):
            if b in loops: k = j; break
        decl_at[v] = path[:k]
    by_block = defaultdict(set)
    for v, path in decl_at.items():
        by_block[path].add(v)
    # rebuild with the same block numbering
    nid = [0]
    def rebuild(stmts, path, pending_outer):
        bid = nid[0]; nid[0] += 1
        p = path + (bid,)
        mine = set(by_block.get(p, ()))
        # walk statements; a variable whose first occurrence here is an unconditional
        # SET at this level is declared there; others are forward-declared
        first_def = {}
        seen = set()
        for i, st in enumerate(stmts):
            vs = set()
            walk(st, lambda x: vs.add(x) if is_var(x) else None)
            for v in vs & mine:
                if v in seen: continue
                seen.add(v)
                ok = (st[0] == 'SET' and st[1] == v and v not in reads_vars(st[2])) or \
                     (st[0] == 'MSET' and v in st[1] and not (reads_vars(st[2]) & set(st[1])))
                first_def[v] = i if ok else None
        forward = sorted((v for v in mine if first_def.get(v) is None), key=vkey)
        out = []
        if forward: out.append(('DECL', forward))
        declared = set(forward)
        for i, st in enumerate(stmts):
            h = st[0]
            if h == 'IF': st = ('IF', st[1], rebuild(st[2], p, None), rebuild(st[3], p, None))
            elif h == 'WHILE': st = ('WHILE', st[1], rebuild(st[2], p, None))
            elif h == 'FOR':
                st = ('FOR', st[1], st[2], st[3], st[4], rebuild(st[5], p, None))
            elif h == 'REPEAT':
                inner = rebuild(st[3] + st[1], p, None)
                st = ('REPEAT', inner, st[2], [])
            if h == 'SET' and st[1] in mine and st[1] not in declared and first_def.get(st[1]) == i:
                declared.add(st[1]); out.append(('LOCALSET', st[1], st[2])); continue
            if h == 'MSET':
                newv = [t for t in st[1] if t in mine and t not in declared and first_def.get(t) == i]
                if newv and len(newv) == len(st[1]):
                    declared.update(newv); out.append(('LOCALMSET', st[1], st[2])); continue
                if newv:
                    declared.update(newv); out.append(('DECL', newv))
            out.append(st)
        return out
    return rebuild(body, (), None)

def vkey(v):
    return (v[0], v[1] if len(v) > 1 else 0)

# ---------------------------------------------------------------- rendering
class Names:
    def __init__(self):
        self.map = {}
        self.cnt = Counter()
    def get(self, v):
        if v not in self.map:
            base = {'R': 'v', 'T': 't', 'S': 's', 'ACC': 'acc'}[v[0]]
            self.cnt[base] += 1
            self.map[v] = '%s%d' % (base, self.cnt[base])
        return self.map[v]

class LuauFmt(Fmt):
    def __init__(self, gen, proto, upnames, params):
        super().__init__()
        self.gen, self.p, self.upnames = gen, proto, upnames
        self.N = Names()
        for i, v in enumerate(params, 1): self.N.map[v] = 'a%d' % i
        self.ind = ''
    def e(self, x, prec=0):
        h = x[0]
        if h in VARS: return self.N.get(x)
        if h == 'U': return self.upnames.get(x[1], 'u%d' % x[1])
        if h == 'IDX' and x[1] == ('ENV',):
            k = x[2]
            if k[0] == 'K' and isinstance(k[1], bytes):
                s = k[1].decode('latin1')
                import re
                if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', s) and s not in ('and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', 'while', 'continue') and s not in self.gen.shadowed:
                    return s
            return 'getfenv()[' + self.e(k) + ']'
        if h == 'CONTAINER':
            if x[1] in ('code', 'consts'):
                self.gen.vmdata.add(self.p.id)
                return '__VM_%s[%d]' % (x[1].upper(), self.p.id)
            if x[1] == 'upvals': return 'true'      # `p2 and p2[i] or nil`: the upvalue list always exists
            return '__VM_REGS'
        if h == 'FN':
            if x[1] == 'shared118': return '__VM_SHARED'
            if x[1] in ('band', 'bor', 'bnot', 'bxor', 'lshift', 'rshift'): return self.gen.std('bit32.' + x[1])
            return self.gen.std(x[1])
        if h == 'GENITER':
            vs = ', '.join('i%d' % i for i in range(1, x[2] + 1))
            return '%s(function() for %s in %s do %s(true, %s) end end)' % (self.gen.std('coroutine.wrap'), vs, ', '.join(self.e(a) for a in x[1]), self.gen.std('coroutine.yield'), vs)
        if h == 'CLOSURE':
            return self.gen.closure(self, x)
        if h == 'NATIVE':
            return '__NATIVE[%d](%s)' % (x[1], ', '.join(self.e(a) for a in x[2]))
        if h == 'CAPS':
            return '{' + ', '.join(self.e(a) for a in x[1]) + '}'
        if h == 'METHOD':
            return super().e(x, prec)
        return super().e(x, prec)
    def s(self, st, ind=''):
        self.ind = ind
        h = st[0]
        if h == 'LOCALSET': return ind + 'local ' + self.e(st[1]) + ' = ' + self.e(st[2]) + '\n'
        if h == 'LOCALMSET': return ind + 'local ' + ', '.join(self.e(v) for v in st[1]) + ' = ' + self.e(st[2]) + '\n'
        if h == 'DECL': return ind + 'local ' + ', '.join(self.e(v) for v in st[1]) + '\n'
        if h == 'MSET': return ind + ', '.join(self.e(v) for v in st[1]) + ' = ' + self.e(st[2]) + '\n'
        if h == 'CLOSEUPV': return ''
        if h == 'ERRPATH': return ind + 'error("devirt: unreachable path")\n'
        if h == 'CRASH': return ind + 'error("integrity check failed")  -- anti-tamper: the VM jumps to an invalid pc (%d)\n' % st[1]
        if h == 'FOR':
            return ind + 'for %s = %s, %s%s do\n' % (self.e(st[1]), self.e(st[2]), self.e(st[3]), '' if st[4] == ('K', 1) else ', ' + self.e(st[4])) + self.block(st[5], ind + '    ') + ind + 'end\n'
        if h == 'RAW': return ''.join(ind + l + '\n' for l in st[1].split('\n'))
        if h == 'SET' and st[1] == ('L', '__n'): return ind + '__n = ' + self.e(st[2]) + '\n'
        return super().s(st, ind)


class Generator:
    def __init__(self, lifter):
        self.L = lifter
        self.vmdata = set()
        self.shadowed = set()
        self.stats = Counter()
        self.stdused = {}

    def std(self, name):
        """library functions the VM captured at load time (not read from the script env)"""
        alias = '__std_' + name.replace('.', '_')
        self.stdused[alias] = 'table.unpack' if name == 'unpack' else name
        return alias

    def std_preamble(self):
        return ''.join('local %s = %s\n' % (a, n) for a, n in sorted(self.stdused.items()))

    def body(self, p):
        ir, errs = self.L.lift_proto(p)
        nodes = emit.apply_multret(emit.merge_chains(emit.to_nodes(ir), 1))
        nodes[1], _ = strip_prologue(nodes[1], p.nparams)
        out, S = structure.structure(nodes, 1)
        if S.labels:
            self.stats['dispatcher'] += 1
            out = emit.dispatcher(nodes, 1)
        out = normalize(out)
        out = inline(out)
        out = drop_dead(out)
        out = inline(out)
        params = [('R', i) for i in range(1, p.nparams + 1)]
        out = place_decls(out, set(params))
        return out, params

    def render(self, p, ind, upnames):
        body, params = self.body(p)
        F = LuauFmt(self, p, upnames, params)
        F.ind = ind
        head = 'function(' + ', '.join(F.e(v) for v in params) + ')'
        return head + '\n' + F.block(body, ind + '    ') + ind + 'end'

    def closure(self, F, x):
        sub, caps = x[1], (x[2][1] if x[2][0] == 'CAPS' else [])
        # by-name capture when the captured expression is a plain variable or
        # constant; the IIFE form keeps by-value semantics in every other case
        simple = all(c[0] in ('K', 'U') for c in caps)
        if simple:
            names = {i: F.e(c) for i, c in enumerate(caps, 1)}
            return self.render(sub, F.ind, names)
        names = {i: 'u%d' % i for i in range(1, len(caps) + 1)}
        inner = self.render(sub, F.ind + '    ', names)
        return '(function(%s)\n%s    return %s\n%send)(%s)' % (
            ', '.join(names.values()), F.ind, inner, F.ind, ', '.join(F.e(c) for c in caps))
