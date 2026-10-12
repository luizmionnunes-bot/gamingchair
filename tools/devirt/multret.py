"""multret.py — rewrite the VM's multiple-value plumbing into Lua multi-values.

Producer (a call whose results are all kept):
    local n = packn(E); top = A + n - 1; for k = 1, n do R[A+k-1] = ret[k] end
  -> ('MSTORE', A, E)                registers A..top hold every value of E
Consumers (all read the range A..top):
    local c = c0; for i = i0, top or i0-1 do S[c] = R[i]; c = c + 1 end
        ... unpack(S, j, c - 1)       -> S[j..] fixed slots followed by E
    local t = R[x]; for k = 1, top - b do t[k] = R[b + k] end   (SETLIST)
Everything is rewritten only when the producer and its consumer are in the
same straight-line node; otherwise the code is left as is (and stays correct
with the explicit register table).
"""

def is_k(e): return isinstance(e, tuple) and e[0] == 'K'

def lin_reg(e, tvar):
    """match A + tvar - 1 / A + tvar + c  -> return A + offset so that index = base + tvar"""
    # forms produced by peval: ('BIN','-',('BIN','+',('K',A),T),('K',1))
    if e[0] == 'BIN' and e[1] == '-' and is_k(e[3]):
        inner = e[2]
        if inner[0] == 'BIN' and inner[1] == '+' and is_k(inner[2]) and inner[3] == tvar:
            return inner[2][1] - e[3][1]
        if inner[0] == 'BIN' and inner[1] == '+' and inner[2] == tvar and is_k(inner[3]):
            return inner[3][1] - e[3][1]
    if e[0] == 'BIN' and e[1] == '+' and is_k(e[2]) and e[3] == tvar: return e[2][1]
    if e[0] == 'BIN' and e[1] == '+' and e[2] == tvar and is_k(e[3]): return e[3][1]
    return None

def match_producer(st, i):
    """returns (A, E, consumed) or None"""
    if i + 2 >= len(st): return None
    a, b, c = st[i], st[i + 1], st[i + 2]
    if not (a[0] == 'LOCAL' and a[2][0] == 'PACKN' and len(a[2][1]) == 1): return None
    T = a[1]
    if not (b[0] == 'SET' and b[1] == ('TOP',)): return None
    if not (c[0] == 'FOR' and c[2] == ('K', 1) and c[3] == T and len(c[5]) == 1): return None
    s = c[5][0]
    if not (s[0] == 'SET' and s[1][0] == 'RX' and s[2] == ('RET', c[1])): return None
    base = lin_reg(s[1][1], c[1])
    if base is None: return None
    A = base + 1
    return A, a[2][1][0], 3

def match_pushrange(st, i):
    """local c = c0; for i = i0, (top or i0-1) do S[c] = R[i]; c = c + 1 end
    returns (Tc, c0, i0, consumed)"""
    if i + 1 >= len(st): return None
    a, b = st[i], st[i + 1]
    if not (a[0] == 'LOCAL' and is_k(a[2])): return None
    Tc, c0 = a[1], a[2][1]
    if not (b[0] == 'FOR' and is_k(b[2]) and b[4] == ('K', 1)): return None
    hi = b[3]
    if not (hi[0] == 'BIN' and hi[1] == 'or' and hi[2] == ('TOP',)): return None
    body = b[5]
    if len(body) != 2: return None
    if not (body[0][0] == 'SET' and body[0][1] == ('SX', Tc) and body[0][2] == ('RX', b[1])): return None
    return Tc, c0, b[2][1], 2

def rewrite(stmts):
    out = []
    i = 0
    pending = {}     # A -> E  (MSTORE not yet consumed)
    ranges = {}      # Tc -> (c0, i0, A, E)
    while i < len(stmts):
        st = stmts[i]
        m = match_producer(stmts, i)
        if m:
            A, E, n = m
            pending = {A: E}
            out.append(('MSTORE', A, E, stmts[i:i + n]))
            i += n; continue
        m = match_pushrange(stmts, i)
        if m and pending:
            Tc, c0, i0, n = m
            A, E = next(iter(pending.items()))
            if i0 <= A:
                for k in range(i0, A):
                    out.append(('SET', ('S', c0 + k - i0), ('R', k)))
                ranges[Tc] = (c0 + A - i0, E)
                # drop the MSTORE: its value now lives in the stack tail
                for j in range(len(out) - 1, -1, -1):
                    if out[j][0] == 'MSTORE' and out[j][1] == A:
                        out[j] = ('MSTACK', c0 + A - i0, E)
                        break
                pending = {}
                i += n; continue
        # SETLIST from top
        if st[0] == 'LOCAL' and i + 1 < len(stmts) and pending:
            nx = stmts[i + 1]
            if nx[0] == 'FOR' and nx[2] == ('K', 1) and nx[3][0] == 'BIN' and nx[3][1] == '-' and nx[3][2] == ('TOP',) and is_k(nx[3][3]) and len(nx[5]) == 1:
                b = nx[3][3][1]
                s = nx[5][0]
                A, E = next(iter(pending.items()))
                if s[0] == 'SET' and s[1] == ('IDX', st[1], nx[1]) and A >= b + 1:
                    out.append(st)
                    for k in range(1, A - b):
                        out.append(('SET', ('IDX', st[1], ('K', k)), ('R', b + k)))
                    out.append(('SETLISTM', st[1], E, A - b))
                    for j in range(len(out) - 1, -1, -1):
                        if out[j][0] == 'MSTORE' and out[j][1] == A:
                            del out[j]; break
                    pending = {}
                    i += 2; continue
        # generic-for with >2 variables: packn(iter()); if ret[1] then ... ret[k] ...
        if st[0] == 'EXPR' and st[1][0] == 'PACKN' and len(st[1][1]) == 1 and i + 1 < len(stmts) and stmts[i + 1][0] == 'IF':
            nxt = stmts[i + 1]
            ks = rets_used(nxt)
            if ks and all(isinstance(k, int) for k in ks):
                n = max(ks)
                Ts = [('T', 800000 + next(_ctr)) for _ in range(n)]
                out.append(('LOCALS', Ts, st[1][1][0]))
                out.append(sub_ret(nxt, Ts))
                i += 2; continue
        st = subst_unpack(st, ranges)
        if st[0] == 'IF': st = ('IF', st[1], rewrite(st[2]), rewrite(st[3]))
        elif st[0] == 'WHILE': st = ('WHILE', st[1], rewrite(st[2]))
        out.append(st)
        i += 1
    return out

import itertools
_ctr = itertools.count()

def rets_used(e):
    ks = set()
    def f(x):
        if isinstance(x, tuple) and x and isinstance(x[0], str):
            if x[0] == 'RET': ks.add(x[1][1] if x[1][0] == 'K' else None)
            for y in x[1:]: f(y)
        elif isinstance(x, list):
            for y in x: f(y)
    f(e)
    return ks

def sub_ret(e, Ts):
    if isinstance(e, tuple) and e and isinstance(e[0], str):
        if e[0] == 'RET' and e[1][0] == 'K': return Ts[e[1][1] - 1]
        return tuple(sub_ret(y, Ts) if isinstance(y, (tuple, list)) else y for y in e)
    if isinstance(e, list): return [sub_ret(y, Ts) for y in e]
    return e

def subst_unpack(e, ranges):
    if isinstance(e, tuple) and e and isinstance(e[0], str):
        if e[0] == 'CALL':
            args = [subst_unpack(a, ranges) for a in e[2]]
            if args and args[-1][0] == 'UNPACKSTACK':
                u = args[-1]
                hi = u[2]
                for Tc, (tail, E) in ranges.items():
                    if hi == ('BIN', '-', Tc, ('K', 1)) and is_k(u[1]):
                        j = u[1][1]
                        args = args[:-1] + [('S', k) for k in range(j, tail)] + [('MSTACKREF', tail, E)]
                        break
            return ('CALL', subst_unpack(e[1], ranges), args)
        return tuple(subst_unpack(y, ranges) if isinstance(y, (tuple, list)) else y for y in e)
    if isinstance(e, list): return [subst_unpack(y, ranges) for y in e]
    return e

def finalize(stmts):
    """MSTACK(k, E) ... MSTACKREF(k, E) -> E inlined at the reference (evaluation
    order is preserved: the reference is the last argument, and every stack slot
    before it was computed before E in the original code)."""
    def drop(st):
        out = []
        for s in st:
            if s[0] == 'MSTACK': continue
            if s[0] == 'MSTORE':        # producer without a recognised consumer: keep as is
                out.extend(s[3]); continue
            if s[0] == 'IF': s = ('IF', s[1], drop(s[2]), drop(s[3]))
            elif s[0] == 'WHILE': s = ('WHILE', s[1], drop(s[2]))
            out.append(s)
        return out
    def ref(e):
        if isinstance(e, tuple) and e and isinstance(e[0], str):
            if e[0] == 'MSTACKREF': return e[2]
            return tuple(ref(y) if isinstance(y, (tuple, list)) else y for y in e)
        if isinstance(e, list): return [ref(y) for y in e]
        return e
    return ref(drop(stmts))
