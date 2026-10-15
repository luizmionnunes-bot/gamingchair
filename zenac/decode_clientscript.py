#!/usr/bin/env python3
"""
Static decoder for the ZenAC ClientScript (Volt decompile).

The script hides every literal behind:
  * u1(data, key)  -- repeating-key XOR  (out[i] = data[i] XOR key[i % #key])
  * small lookup helpers  NAME(k) -> ARGTABLE[k +/- OFFSET]
    where ARGTABLE is the constant table a nested IIFE receives as its 1st arg.

Both are PURE (only constants + string ops), so we evaluate them offline and
inline the results, turning the obfuscated source into readable Lua.

Usage: python3 -I decode_clientscript.py in.lua out.lua
"""
import re
import sys

# ---------------------------------------------------------------- tokenizer
def _long_bracket_level(s, i):
    # s[i] == '['  -> return (level, content_start) if it opens a long bracket, else None
    j = i + 1
    eq = 0
    while j < len(s) and s[j] == '=':
        eq += 1
        j += 1
    if j < len(s) and s[j] == '[':
        return eq, j + 1
    return None

def _skip_long_bracket(s, i, eq):
    close = ']' + '=' * eq + ']'
    k = s.find(close, i)
    if k < 0:
        return len(s)
    return k + len(close)

def skip_insignificant(s, i):
    """If s[i] starts a comment or string, return index just past it; else i."""
    if s[i] == '-' and i + 1 < len(s) and s[i + 1] == '-':
        # comment
        if i + 2 < len(s) and s[i + 2] == '[':
            lb = _long_bracket_level(s, i + 2)
            if lb:
                eq, start = lb
                return _skip_long_bracket(s, start, eq)
        # line comment
        k = s.find('\n', i)
        return len(s) if k < 0 else k
    if s[i] == '[':
        lb = _long_bracket_level(s, i)
        if lb:
            eq, start = lb
            return _skip_long_bracket(s, start, eq)
    if s[i] in '"\'':
        _, end = parse_short_string(s, i)
        return end
    return i

OPEN = {'(': ')', '[': ']', '{': '}'}

def find_matching(s, open_idx):
    """s[open_idx] in ([{ -> index past its matching close."""
    stack = [s[open_idx]]
    i = open_idx + 1
    while i < len(s) and stack:
        j = skip_insignificant(s, i)
        if j != i:
            i = j
            continue
        c = s[i]
        if c in OPEN:
            stack.append(c)
        elif c in (')', ']', '}'):
            stack.pop()
            if not stack:
                return i + 1
        i += 1
    return i

# ---------------------------------------------------------------- strings
_ESC = {'a': 7, 'b': 8, 'f': 12, 'n': 10, 'r': 13, 't': 9, 'v': 11,
        '\\': 92, '"': 34, "'": 39, '\n': 10}

def parse_short_string(s, i):
    """s[i] is opening quote. Return (bytes_value, end_index_exclusive)."""
    q = s[i]
    i += 1
    out = bytearray()
    while i < len(s):
        c = s[i]
        if c == q:
            return bytes(out), i + 1
        if c == '\\':
            i += 1
            e = s[i]
            if e in _ESC:
                out.append(_ESC[e])
                i += 1
            elif e == 'x':
                h = s[i + 1:i + 3]
                out.append(int(h, 16))
                i += 3
            elif e == 'z':
                i += 1
                while i < len(s) and s[i] in ' \t\n\r\f\v':
                    i += 1
            elif e.isdigit():
                d = e
                i += 1
                for _ in range(2):
                    if i < len(s) and s[i].isdigit():
                        d += s[i]
                        i += 1
                    else:
                        break
                out.append(int(d) & 0xFF)
            elif e == 'u':
                # \u{XXXX} -> utf8
                j = s.index('}', i)
                cp = int(s[i + 2:j], 16)
                out.extend(chr(cp).encode('utf-8'))
                i = j + 1
            else:
                out.append(ord(e))
                i += 1
        else:
            out.append(ord(c) & 0xFF if ord(c) < 256 else ord(c))
            if ord(c) >= 256:
                out = bytearray(bytes(out[:-1]) + c.encode('utf-8'))
            i += 1
    raise ValueError("unterminated string at %d" % i)

def emit_lua_string(b):
    """bytes -> a readable Lua double-quoted literal."""
    out = ['"']
    for x in b:
        ch = chr(x)
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif ch == '\t':
            out.append('\\t')
        elif 32 <= x < 127:
            out.append(ch)
        else:
            out.append('\\%d' % x)
    out.append('"')
    return ''.join(out)

# ---------------------------------------------------------------- u1 XOR
def u1(data, key):
    if not key:
        return data
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))

# ---------------------------------------------------------------- value eval
def eval_value(s, i):
    """Evaluate a constant expression starting at s[i] (ws already skipped).
    Returns (python_value, end_index). Supports: true/false/nil, numbers,
    short strings, and u1(str,str)."""
    while s[i] in ' \t\n\r':
        i += 1
    if s.startswith('true', i):
        return True, i + 4
    if s.startswith('false', i):
        return False, i + 5
    if s.startswith('nil', i):
        return None, i + 3
    if s[i] in '"\'':
        return parse_short_string(s, i)
    if s.startswith('u1(', i):
        argpos = i + 2  # at '('
        end = find_matching(s, argpos)
        inner = s[argpos + 1:end - 1]
        d, p = parse_short_string(inner, _first_nonspace(inner, 0))
        # skip comma
        k = p
        while inner[k] in ' \t\n\r,':
            k += 1
        key, _ = parse_short_string(inner, k)
        return u1(d, key), end
    # number (int / float / hex)
    m = re.match(r'-?\s*(0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+)', s[i:])
    if m:
        txt = m.group(0).replace(' ', '')
        val = int(txt, 16) if txt.lower().startswith('0x') or txt.lower().startswith('-0x') else float(txt) if ('.' in txt or 'e' in txt.lower()) else int(txt)
        return val, i + m.end()
    raise ValueError("cannot eval value at: %r" % s[i:i + 40])

def _first_nonspace(s, i):
    while i < len(s) and s[i] in ' \t\n\r':
        i += 1
    return i

# ---------------------------------------------------------------- arg tables
def first_top_arg(inner):
    """Return the first top-level comma-separated argument substring."""
    depth = 0
    i = 0
    n = len(inner)
    while i < n:
        j = skip_insignificant(inner, i)
        if j != i:
            i = j
            continue
        c = inner[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ',' and depth == 0:
            return inner[:i]
        i += 1
    return inner

def table_from_variable(s, var):
    """Reconstruct {int_key: value} from 'local var = {..}' + 'var[k] = v' lines."""
    d = {}
    m = re.search(r'local ' + re.escape(var) + r'\s*=\s*\{', s)
    if m:
        br = m.end() - 1  # at '{'
        end = find_matching(s, br)
        body = s[br + 1:end - 1].strip()
        if body:
            d.update(parse_table(body))
    for am in re.finditer(r'(?<![\w.:])' + re.escape(var) + r'\[', s):
        br = am.end() - 1  # at '['
        ke = find_matching(s, br)
        keytxt = s[br + 1:ke - 1].strip()
        key, _ = eval_value(keytxt, _first_nonspace(keytxt, 0))
        i = ke
        while s[i] in ' \t\n\r':
            i += 1
        if s[i] != '=' or s[i + 1] == '=':   # skip comparisons / not an assignment
            continue
        i += 1
        val, _ = eval_value(s, _first_nonspace(s, i))
        d[int(key)] = val
    return d

def extract_table(s, var):
    """Resolve the constant table bound to parameter `var`, via either an IIFE
    argument or a named closure call; the arg may be a literal or a named table."""
    m = re.search(r'\(function\(' + re.escape(var) + r'[,)]', s)
    if m:
        paren = m.start()                 # '(' before 'function'
        close = find_matching(s, paren)   # past ')' ending (function...)
        i = _first_nonspace(s, close)
        assert s[i] == '(', "expected call ( after IIFE for %s" % var
        call_end = find_matching(s, i)
        arg = first_top_arg(s[i + 1:call_end - 1]).strip()
    else:
        fm = re.search(r'(\w+)\s*=\s*function\(' + re.escape(var) + r'[,)]', s)
        funcname = fm.group(1)
        cm = re.search(r'(?<![\w.:])' + re.escape(funcname) + r'\(', s)
        i = cm.end() - 1                  # at '('
        call_end = find_matching(s, i)
        arg = first_top_arg(s[i + 1:call_end - 1]).strip()
    if arg.startswith('{'):
        return parse_table(arg[1:find_matching(arg, 0) - 1])
    # arg is a variable name referring to a table built by assignments
    return table_from_variable(s, arg)

def parse_table(tbl):
    """Parse '[k]=v, [k]=v, ...' (constant keys/values) -> dict."""
    d = {}
    i = 0
    n = len(tbl)
    while i < n:
        while i < n and tbl[i] in ' \t\n\r,':
            i += 1
        if i >= n:
            break
        if tbl[i] == '[':
            ke = find_matching(tbl, i)
            keyexpr = tbl[i + 1:ke - 1].strip()
            key, _ = eval_value(keyexpr, _first_nonspace(keyexpr, 0))
            i = ke
            while tbl[i] in ' \t\n\r':
                i += 1
            assert tbl[i] == '=', "expected = in table entry near %r" % tbl[i:i+20]
            i += 1
            while tbl[i] in ' \t\n\r':
                i += 1
            val, i = eval_value(tbl, i)
            d[int(key)] = val
        else:
            raise ValueError("array-style table entry near %r" % tbl[i:i+30])
    return d

# ---------------------------------------------------------------- helpers
def find_helpers(s):
    """local function NAME(param) ... return TBLVAR[param OP OFFSET] end"""
    helpers = {}
    for m in re.finditer(
        r'local function (\w+)\((\w+)\)[\s\S]{0,300}?return (\w+)\[(\w+)\s*([-+])\s*(\d+)\]\s*\n\s*end',
        s):
        name, param, tblvar, p2, sign, off = m.groups()
        if p2 != param:
            continue
        helpers[name] = (tblvar, 1 if sign == '+' else -1, int(off))
    return helpers

# ---------------------------------------------------------------- main
def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    s = open(src, encoding='utf-8-sig').read()

    helpers = find_helpers(s)
    tables = {}
    for name, (tblvar, sgn, off) in helpers.items():
        if tblvar not in tables:
            tables[tblvar] = extract_table(s, tblvar)
    sys.stderr.write("helpers: %r\n" % {k: v for k, v in helpers.items()})
    for tv, d in tables.items():
        sys.stderr.write("table %s: %r\n" % (tv, {k: (v if not isinstance(v, bytes) else v.decode('latin-1')) for k, v in d.items()}))

    def resolve_helper(name, arg):
        tblvar, sgn, off = helpers[name]
        key = arg + sgn * off
        return tables[tblvar][key]

    # single left-to-right rewrite pass, tokenizer-aware
    out = []
    i = 0
    n = len(s)
    repl_u1 = 0
    repl_h = 0
    ident_re = re.compile(r'[A-Za-z_]\w*')
    while i < n:
        # preserve comments and strings verbatim
        j = skip_insignificant(s, i)
        if j != i:
            out.append(s[i:j])
            i = j
            continue
        m = ident_re.match(s, i)
        if m:
            name = m.group(0)
            k = m.end()
            # must be a call: name '(' ... but ensure not preceded by '.'/':' (method/field)
            prev = s[i - 1] if i > 0 else ''
            is_call = k < n and s[k] == '('
            if name == 'u1' and is_call and prev not in '.:':
                argpos = k
                end = find_matching(s, argpos)
                inner = s[argpos + 1:end - 1]
                a = _first_nonspace(inner, 0)
                d, p = parse_short_string(inner, a)
                c = p
                while inner[c] in ' \t\n\r,':
                    c += 1
                key, _ = parse_short_string(inner, c)
                out.append(emit_lua_string(u1(d, key)))
                i = end
                repl_u1 += 1
                continue
            if name in helpers and is_call and prev not in '.:':
                argpos = k
                end = find_matching(s, argpos)
                inner = s[argpos + 1:end - 1].strip()
                mm = re.fullmatch(r'-?\s*\d+', inner)
                if mm:
                    val = resolve_helper(name, int(inner.replace(' ', '')))
                    if isinstance(val, bytes):
                        out.append(emit_lua_string(val))
                    elif val is True:
                        out.append('true')
                    elif val is False:
                        out.append('false')
                    elif val is None:
                        out.append('nil')
                    elif isinstance(val, float):
                        out.append(repr(val))
                    else:
                        out.append(str(val))
                    i = end
                    repl_h += 1
                    continue
            out.append(s[i:k])
            i = k
            continue
        out.append(s[i])
        i += 1

    open(dst, 'w', encoding='utf-8').write(''.join(out))
    sys.stderr.write("replaced u1: %d, helper calls: %d\n" % (repl_u1, repl_h))

if __name__ == '__main__':
    main()
