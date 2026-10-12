"""names.py — name the locals after what they demonstrably hold.

The author's names are gone, so every name here is derived from evidence in
the code itself and nothing else: the global a local is a copy of, the field
or method that produced it, the class string passed to `Instance.new`, the
library function it aliases. A variable whose definitions disagree, or that
holds only an intermediate computation, keeps its number. An invented name
that turned out wrong would be worse than `v12`.

Rules, highest confidence first:

    local v = pcall                     -> pcall_      (a global, snapshotted)
    local v = string.char               -> char
    local v = v8.LocalPlayer            -> localPlayer
    local v = v8:GetService("Players")  -> players
    local v = v8:GetLogHistory()        -> logHistory
    local v = Instance.new("RemoteEvent") -> remoteEvent
    local ok, err = pcall(...)          -> ok, err
    local v = type(x) / #x / {}         -> ty / n / tbl
    local v = v8                        -> whatever v8 is called, + a number

A trailing underscore marks a snapshot of a global (`pcall_` holds `pcall`),
which the program does on purpose: it compares the snapshot against the live
global later, so the two must stay distinguishable. For the same reason no
local is ever named after a global that the program reads bare anywhere --
the name would capture that read.
"""
import re

IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
NUMBERED = re.compile(r'^[avtsu]\d+$')
KEYWORDS = set('and break do else elseif end false for function goto if in local'
               ' nil not or repeat return then true until while continue'.split())
# the generator's own names
RESERVED = {'acc', 't', 'self', '_'}

# a method whose name says what it returns
GETTERS = ('Get', 'Find', 'Create', 'New', 'Make', 'Build')
# a method whose string argument says what it returns
BY_ARG = ('GetService', 'FindService', 'FindFirstChild', 'WaitForChild',
          'FindFirstChildOfClass', 'FindFirstChildWhichIsA', 'GetAttribute')


def camel(s):
    """LocalPlayer -> localPlayer, JobId -> jobId, status -> status"""
    if not s:
        return s
    if s.isupper():
        return s.lower()
    return s[0].lower() + s[1:]


def kstr(x):
    """the string a ('K', b'...') node holds, if it is an identifier"""
    if isinstance(x, tuple) and len(x) == 2 and x[0] == 'K' \
            and isinstance(x[1], bytes):
        s = x[1].decode('latin1')
        if IDENT.match(s):
            return s
    return None


def global_read(x):
    """the global name `x` reads, if that is all it does"""
    if isinstance(x, tuple) and len(x) == 3 and x[0] == 'IDX' and x[1] == ('ENV',):
        return kstr(x[2])
    return None


def globals_in(x, out):
    """every global name read anywhere in `x` -- these must not be shadowed"""
    if isinstance(x, (tuple, list)):
        g = global_read(x) if isinstance(x, tuple) else None
        if g:
            out.add(g)
        for y in (x[1:] if isinstance(x, tuple) and x and isinstance(x[0], str)
                  else x):
            if isinstance(y, (tuple, list)):
                globals_in(y, out)


VARKINDS = ('R', 'T', 'S', 'ACC', 'W')


def is_var(x):
    return isinstance(x, tuple) and x and x[0] in VARKINDS


def base_of(x):
    """a name for a variable defined as `x`, or None.

    Returns ('copy', var) when the definition is another variable, which the
    caller resolves once that one has a name.
    """
    if not (isinstance(x, tuple) and x and isinstance(x[0], str)):
        return None
    h = x[0]
    if is_var(x):
        return ('copy', x)
    if h == 'U':
        return ('upval', x[1])
    if h == 'IDX':
        g = global_read(x)
        if g:
            return g + '_'                      # snapshot of a global
        lib = global_read(x[1])
        if lib:                                 # string.char, math.floor
            f = kstr(x[2])
            if f:
                return camel(f)
        if is_var(x[1]) or (isinstance(x[1], tuple) and x[1][0] == 'U'):
            f = kstr(x[2])
            if f:
                return camel(f)
        return None
    if h == 'METHOD':
        obj, meth, args = x[1], x[2], x[3]
        if meth in BY_ARG and args:
            s = kstr(args[0])
            if s:
                return camel(s)
        if meth.startswith(GETTERS):
            for pre in GETTERS:
                if meth.startswith(pre) and len(meth) > len(pre):
                    rest = meth[len(pre):]
                    if rest.startswith('FirstChild'):
                        break
                    return camel(rest)
        return None
    if h == 'CALL':
        f = x[1]
        # Instance.new("RemoteEvent")
        if isinstance(f, tuple) and f[0] == 'IDX' and global_read(f[1]) \
                and kstr(f[2]) == 'new' and x[2]:
            s = kstr(x[2][0])
            if s:
                return camel(s)
        g = global_read(f) or (f[1] if isinstance(f, tuple) and f[0] == 'FN'
                               else None)
        return {'type': 'ty', 'tostring': 'str', 'tonumber': 'num',
                'rawget': 'got', 'getmetatable': 'mt', 'newproxy': 'proxy',
                'getfenv': 'env', 'select': 'sel'}.get(g)
    if h == 'UN' and x[1] == '#':
        return 'n'
    if h == 'NEWT':
        return 'tbl'
    if h == 'CLOSURE':
        return 'fn'
    if h == 'NATIVE':
        return 'native%d' % x[1]
    if h == 'CONTAINER':
        return {'code': 'code', 'consts': 'consts', 'regs': 'regs'}.get(x[1])
    if h == 'FN':
        return camel(x[1].split('.')[-1])
    if h == 'K':
        s = kstr(x)
        # a constant string held in a variable is there to be used as a key
        return (s + 'Key') if s else None
    return None


def walk_stmts(stmts, fn):
    for st in stmts:
        fn(st)
        h = st[0]
        if h == 'IF':
            walk_stmts(st[2], fn); walk_stmts(st[3], fn)
        elif h == 'WHILE':
            walk_stmts(st[2], fn)
        elif h == 'FOR':
            walk_stmts(st[5], fn)
        elif h == 'REPEAT':
            walk_stmts(st[1], fn); walk_stmts(st[3], fn)
        elif h == 'FORIN':
            walk_stmts(st[3], fn)


def collect(body):
    """(vars in first-seen order, {var: [candidate, ...]})"""
    order, seen = [], set()
    cand = {}

    def note(v):
        if is_var(v) and v not in seen:
            seen.add(v); order.append(v)

    def note_all(x):
        if isinstance(x, tuple) and x and isinstance(x[0], str):
            note(x)
            for y in x[1:]:
                if isinstance(y, (tuple, list)):
                    note_all(y)
        elif isinstance(x, (tuple, list)):
            for y in x:
                note_all(y)

    def add(v, c):
        if c is not None:
            cand.setdefault(v, []).append(c)

    def stmt(st):
        h = st[0]
        if h in ('SET', 'LOCALSET'):
            note_all(st[1]); note_all(st[2])
            if is_var(st[1]):
                add(st[1], base_of(st[2]))
        elif h in ('MSET', 'LOCALMSET'):
            for v in st[1]:
                note_all(v)
            note_all(st[2])
            e = st[2]
            g = (global_read(e[1]) if isinstance(e, tuple) and e[0] == 'CALL'
                 else None)
            if g in ('pcall', 'xpcall') and len(st[1]) >= 2:
                for v, nm in zip(st[1], ['ok', 'err']):
                    if is_var(v):
                        add(v, nm)
            # a multi-value call says nothing about the rest
        elif h == 'DECL':
            for v in st[1]:
                note_all(v)
        else:
            for y in st[1:]:
                if isinstance(y, (tuple, list)):
                    note_all(y)

    walk_stmts(body, stmt)
    return order, cand


def assign(body, params, upnames, forbidden, taken):
    """{var: name} for the locals of one function body.

    `forbidden` are names no local may take (globals the program reads, Lua
    keywords); `taken` are names already in use by the enclosing functions,
    so a local never captures an upvalue reference rendered by name.
    """
    order, cand = collect(body)
    for v in params:
        cand.pop(v, None)
    pset = set(params)

    # resolve copies: a variable defined only as a copy of another inherits
    # its name. Iterate to a fixed point over copy chains.
    base = {}
    for v in order:
        cs = cand.get(v, [])
        names = {c for c in cs if isinstance(c, str)}
        copies = [c for c in cs if isinstance(c, tuple)]
        if len(names) == 1 and not copies:
            base[v] = next(iter(names))
        elif not names and len(copies) == 1:
            base[v] = copies[0]
        # disagreement, or a mix: no name

    for _ in range(len(order) + 1):
        changed = False
        for v, b in list(base.items()):
            if not isinstance(b, tuple):
                continue
            if b[0] == 'upval':
                nm = upnames.get(b[1])
                if nm and IDENT.match(nm):
                    base[v] = re.sub(r'\d+$', '', nm) or nm
                    changed = True
                else:
                    del base[v]; changed = True
            else:
                src = b[1]
                if src in pset or src not in base:
                    del base[v]; changed = True
                elif isinstance(base[src], str):
                    base[v] = base[src]; changed = True
        if not changed:
            break
    for v, b in list(base.items()):
        if not isinstance(b, str):
            del base[v]

    out = {}
    used = set(taken) | set(upnames.values())
    counts = {}
    for v in order:
        b = base.get(v)
        if b is None:
            continue
        if (not IDENT.match(b) or b in KEYWORDS or b in RESERVED
                or b in forbidden or NUMBERED.match(b) or b.startswith('__')):
            continue
        nm = b
        if nm in used:
            i = counts.get(b, 1)
            while True:
                i += 1
                nm = '%s%d' % (b, i)
                if nm not in used:
                    break
            counts[b] = i
        used.add(nm)
        out[v] = nm
    return out
