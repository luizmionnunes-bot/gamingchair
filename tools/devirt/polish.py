"""polish.py — semantics-preserving readability rewrites on structured IR.

  method      CALL(IDX(o, "m"), [o, ...])          -> o:m(...)
  constants   single-definition webs holding a constant -> constant at every use
  conditions  if-not-then-empty-else inversion, `not not x` in tests,
              `not (a ~= b)` -> `a == b`, constant tests folded
  tails       redundant `return` at function end / `continue` at loop end
  while       `while true do if c then B (continue) else break end end` -> `while c do B end`
  genfor      coroutine-wrapped iterator loop -> native `for a, b in f, s, c do`
Each rewrite is local and exact; the differential test re-validates the result.
"""
VARS = ('R', 'T', 'S', 'ACC', 'W')
def is_var(x): return isinstance(x, tuple) and x and x[0] in VARS

def mapx(e, f):
    """bottom-up expression map"""
    if isinstance(e, tuple) and e and isinstance(e[0], str):
        e = tuple(mapx(y, f) if isinstance(y, (tuple, list)) else y for y in e)
        return f(e)
    if isinstance(e, list): return [mapx(y, f) for y in e]
    return e

def pure_obj(o):
    return is_var(o) or (isinstance(o, tuple) and o[0] in ('U', 'K'))

def method(e):
    if e[0] == 'CALL' and e[1][0] == 'IDX' and e[2] and e[2][0] == e[1][1] and pure_obj(e[1][1]):
        k = e[1][2]
        if k[0] == 'K' and isinstance(k[1], bytes):
            import re
            name = k[1].decode('latin1')
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
                return ('METHOD', e[1][1], name, e[2][1:])
    return e

def cond_simp(c):
    """simplify an expression used only for its truthiness"""
    if c[0] == 'UN' and c[1] == 'not' and c[2][0] == 'UN' and c[2][1] == 'not':
        return cond_simp(c[2][2])
    if c[0] == 'UN' and c[1] == 'not' and c[2][0] == 'BIN' and c[2][1] in ('~=', '=='):
        b = c[2]
        return ('BIN', '==' if b[1] == '~=' else '~=', b[2], b[3])
    return c

def neg(c):
    if c[0] == 'UN' and c[1] == 'not': return cond_simp(c[2])
    if c[0] == 'BIN' and c[1] in ('~=', '=='): return ('BIN', '==' if c[1] == '~=' else '~=', c[2], c[3])
    if c[0] == 'K': return ('K', c[1] is None or c[1] is False)
    return ('UN', 'not', c)

def truthy_k(c):
    if c[0] == 'K': return not (c[1] is None or c[1] is False)
    return None

def stmts_map(stmts, fs, fe):
    out = []
    for s in stmts:
        h = s[0]
        if h == 'IF': s = ('IF', mapx(s[1], fe), stmts_map(s[2], fs, fe), stmts_map(s[3], fs, fe))
        elif h == 'WHILE': s = ('WHILE', mapx(s[1], fe), stmts_map(s[2], fs, fe))
        elif h == 'FOR': s = ('FOR', s[1], mapx(s[2], fe), mapx(s[3], fe), mapx(s[4], fe), stmts_map(s[5], fs, fe))
        elif h == 'FORIN': s = ('FORIN', s[1], [mapx(x, fe) for x in s[2]], stmts_map(s[3], fs, fe))
        elif h == 'REPEAT': s = ('REPEAT', stmts_map(s[1], fs, fe), mapx(s[2], fe), stmts_map(s[3], fs, fe))
        else: s = mapx(s, fe) if h not in ('SET', 'MSET') else (h, mapx(s[1], fe) if h == 'SET' else s[1], mapx(s[2], fe))
        r = fs(s)
        if isinstance(r, list): out += r
        else: out.append(r)
    return out

def ifs(s):
    if s[0] != 'IF': return s
    c, a, b = cond_simp(s[1]), s[2], s[3]
    k = truthy_k(c)
    if k is True: return a
    if k is False: return b
    if not a and b: return ('IF', neg(c), b, [])
    return ('IF', c, a, b)

def strip_tail(stmts, kind):
    if stmts and stmts[-1][0] == kind and (kind != 'RETURN' or not stmts[-1][1]):
        return strip_tail(stmts[:-1], kind)
    if stmts and stmts[-1][0] == 'IF':
        s = stmts[-1]
        return stmts[:-1] + [('IF', s[1], strip_tail(s[2], kind), strip_tail(s[3], kind))]
    return stmts

def loops(s):
    """loop-level rewrites (applied after children are rewritten)"""
    if s[0] != 'WHILE': return s
    body = strip_tail(s[2], 'CONTINUE')
    # while true do if c then B else break end end  /  if not c then break end ...
    if s[1] == ('K', True) and body and body[0][0] == 'IF':
        f = body[0]
        if f[3] == [('BREAK',)] and len(body) == 1:
            return ('WHILE', f[1], strip_tail(f[2], 'CONTINUE'))
        if f[2] == [('BREAK',)] and not f[3]:
            return ('WHILE', neg(f[1]), body[1:])
        if f[2] == [('BREAK',)] and f[3] and len(body) == 1:
            return ('WHILE', neg(f[1]), strip_tail(f[3], 'CONTINUE'))
    return ('WHILE', s[1], body)

def has_break(stmts):
    """BREAK bound to the current loop (not to nested loops)"""
    for s in stmts:
        h = s[0]
        if h == 'BREAK': return True
        if h == 'IF' and (has_break(s[2]) or has_break(s[3])): return True
    return False

def genfor(stmts):
    """v = wrap(function() for xs in f,s,c do yield(true, xs) end end)
       while true do local ok, a, b = v(); if not ok then break else BODY end end"""
    out = []
    i = 0
    while i < len(stmts):
        s = stmts[i]
        if s[0] in ('SET', 'LOCALSET') and isinstance(s[2], tuple) and s[2][0] == 'GENITER' and i + 1 < len(stmts):
            it = s[1]; vals, nv = s[2][1], s[2][2]
            w = stmts[i + 1]
            if w[0] == 'WHILE' and w[2]:
                b0 = w[2][0]
                if b0[0] in ('MSET', 'LOCALMSET') and b0[2] == ('CALL', it, []) and len(b0[1]) == nv + 1:
                    ok = b0[1][0]; xs = b0[1][1:]
                    rest = w[2][1:]
                    body = None
                    if w[1] == ('K', True) and rest and rest[0][0] == 'IF' and rest[0][1] == ('UN', 'not', ok) and rest[0][2] == [('BREAK',)]:
                        body = rest[0][3] + rest[1:]
                    elif w[1] == ok or (w[1] == ('K', True) and rest and rest[0][0] == 'IF' and rest[0][1] == ok and rest[0][3] == [('BREAK',)]):
                        body = rest if w[1] == ok else rest[0][2] + rest[1:]
                    after = stmts[i + 2:]
                    if body is not None and not uses(body, ok) and not uses(body, it) and not uses(after, it) and not any(uses(after, x) for x in xs):
                        out.append(('FORIN', list(xs), vals, strip_tail(body, 'CONTINUE')))
                        i += 2; continue
        h = s[0]
        if h == 'IF': s = ('IF', s[1], genfor(s[2]), genfor(s[3]))
        elif h == 'WHILE': s = ('WHILE', s[1], genfor(s[2]))
        elif h == 'FOR': s = ('FOR', s[1], s[2], s[3], s[4], genfor(s[5]))
        elif h == 'FORIN': s = ('FORIN', s[1], s[2], genfor(s[3]))
        elif h == 'REPEAT': s = ('REPEAT', genfor(s[1]), s[2], genfor(s[3]))
        out.append(s)
        i += 1
    return out

def uses(x, v):
    found = [False]
    def f(e):
        if e == v: found[0] = True
        return e
    mapx(x, f)
    return found[0]

def run(body):
    body = genfor(body)
    body = stmts_map(body, lambda s: s, method)
    body = stmts_map(body, ifs, lambda e: e)
    body = stmts_map(body, loops, lambda e: e)
    body = stmts_map(body, ifs, lambda e: e)
    body = strip_tail(body, 'RETURN')
    return body
