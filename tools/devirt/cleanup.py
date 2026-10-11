"""cleanup.py — readability passes over structured IR (semantics-preserving).

1. temporaries/stack slots defined once and used once in the same block are
   inlined into their use, in evaluation order (stack-machine -> expressions)
2. helper queries (varargs use, register declarations)
"""
from collections import Counter

def walk_e(x, f):
    if isinstance(x, tuple) and x and isinstance(x[0], str):
        f(x)
        for y in x[1:]:
            if isinstance(y, (tuple, list)): walk_e(y, f)
    elif isinstance(x, list):
        for y in x: walk_e(y, f)

def uses_varargs(body):
    found = [False]
    walk_e(body, lambda x: found.__setitem__(0, True) if x[0] in ('VA', 'NVA') else None)
    return found[0]

def declare(body, p):
    regs = set()
    def f(x):
        if x[0] == 'R' and isinstance(x[1], int) and x[1] > p.nparams: regs.add(x[1])
    walk_e(body, f)
    return [('R', r) for r in sorted(regs)]

TEMPS = ('T', 'S')

def is_temp(x): return isinstance(x, tuple) and x and x[0] in TEMPS

def count_uses(body):
    c = Counter()
    def f(x):
        if x[0] in TEMPS: c[x] += 1
    walk_e(body, f)
    return c

def run(body, p):
    body = inline(body)
    return body

def subst(e, var, val):
    if e == var: return val
    if isinstance(e, tuple):
        return tuple(subst(y, var, val) if isinstance(y, (tuple, list)) else y for y in e)
    if isinstance(e, list):
        return [subst(y, var, val) for y in e]
    return e

def reads(e):
    s = []
    walk_e(e, lambda x: s.append(x) if x[0] in ('R', 'S', 'T', 'U', 'ACC', 'TOP') else None)
    return s

def has_effects(e):
    found = [False]
    walk_e(e, lambda x: found.__setitem__(0, True) if x[0] in ('CALL', 'PACKN', 'CLOSURE', 'NATIVE', 'IDX', 'NEWT') else None)
    return found[0]

def inline(body):
    """repeatedly inline single-use temps into the next statement that uses them"""
    uses = count_uses(body)
    defs = Counter()
    walk_e(body, lambda x: defs.__setitem__(x[1], defs[x[1]] + 1) if x[0] in ('SET', 'LOCAL') and isinstance(x[1], tuple) and x[1][0] in TEMPS else None)
    return inline_block(body, uses, defs)

def inline_block(stmts, uses, defs):
    out = []
    for st in stmts:
        st = rec(st, uses, defs)
        out.append(st)
        # try to fold pending definitions into this statement
        changed = True
        while changed and len(out) >= 2:
            changed = False
            # find the nearest earlier def of a temp used exactly once in `st`
            cur = out[-1]
            for j in range(len(out) - 2, -1, -1):
                d = out[j]
                if d[0] not in ('SET', 'LOCAL') or not is_temp(d[1]): break
                var = d[1]
                if uses[var] != 1 or defs[var] != 1: break
                if not occurs(cur, var): break
                # everything between j and cur must be temp defs that are themselves
                # inlined later into cur, in order; be conservative: only adjacent
                if j != len(out) - 2: break
                if not safe_target(cur, var, d[2]): break
                out[-1] = subst_stmt(cur, var, d[2])
                del out[j]
                changed = True
                break
    return out

def occurs(st, var):
    found = [False]
    walk_e(st, lambda x: found.__setitem__(0, True) if x == var else None)
    return found[0]

def eval_order(e, out):
    """Luau evaluation order of an IR expression (post-order: operands, then node)"""
    if not (isinstance(e, tuple) and e and isinstance(e[0], str)): return
    h = e[0]
    if h == 'CALL':
        eval_order(e[1], out)
        for a in e[2]: eval_order(a, out)
    elif h == 'BIN':
        eval_order(e[2], out); eval_order(e[3], out)
    elif h in ('IDX',):
        eval_order(e[1], out); eval_order(e[2], out)
    elif h == 'NEWT':
        for it in e[1]:
            for y in it[1:]: eval_order(y, out)
    elif h in ('CAPS', 'MULTI'):
        for y in e[1]: eval_order(y, out)
    else:
        for y in e[1:]:
            if isinstance(y, tuple): eval_order(y, out)
            elif isinstance(y, list):
                for z in y: eval_order(z, out)
    out.append(e)

def observable(x):
    return x[0] in ('CALL', 'IDX', 'PACKN', 'NATIVE', 'CLOSURE', 'VA', 'RET')

def stmt_order(st):
    out = []
    h = st[0]
    if h == 'SET':
        l = st[1]
        if l[0] == 'IDX': eval_order(l[1], out); eval_order(l[2], out)
        elif l[0] in ('RX', 'SX'): eval_order(l[1], out)
        eval_order(st[2], out)
    elif h in ('LOCAL', 'LOCALS'): eval_order(st[2], out)
    elif h == 'EXPR': eval_order(st[1], out)
    elif h == 'RETURN':
        for v in st[1]: eval_order(v, out)
    elif h == 'IF': eval_order(st[1], out)
    else: return None
    return out

def safe_target(st, var, val=None):
    """var must be read (not written) by st, and not inside a loop body;
    if val has effects, nothing observable may be evaluated before var"""
    h = st[0]
    if val is not None and has_effects(val):
        order = stmt_order(st)
        if order is None: return False
        for x in order:
            if x == var: break
            if observable(x): return False
        if h == 'SET' and st[1][0] in ('IDX',) and False: return False
    if h in ('WHILE', 'FOR', 'REPEAT', 'FORIN'): return False
    if h == 'IF': return occurs(st[1], var) and not occurs(st[2], var) and not occurs(st[3], var)
    if h in ('SET', 'LOCAL') and st[1] == var: return False
    return True

def subst_stmt(st, var, val):
    h = st[0]
    if h == 'IF': return ('IF', subst(st[1], var, val), st[2], st[3])
    if h in ('SET',):
        return ('SET', subst_lhs(st[1], var, val), subst(st[2], var, val))
    return subst(st, var, val)

def subst_lhs(l, var, val):
    if l == var: return l
    return subst(l, var, val)

def rec(st, uses, defs):
    h = st[0]
    if h == 'IF': return ('IF', st[1], inline_block(st[2], uses, defs), inline_block(st[3], uses, defs))
    if h == 'WHILE': return ('WHILE', st[1], inline_block(st[2], uses, defs))
    if h == 'FOR': return ('FOR', st[1], st[2], st[3], st[4], inline_block(st[5], uses, defs))
    if h == 'REPEAT': return ('REPEAT', inline_block(st[1], uses, defs), st[2], inline_block(st[3], uses, defs))
    return st
