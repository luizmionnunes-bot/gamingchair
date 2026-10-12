"""irfmt.py — print peval IR as Lua-like text."""
import re

PREC = {'or': 1, 'and': 2, '<': 3, '>': 3, '<=': 3, '>=': 3, '~=': 3, '==': 3, '..': 4,
        '+': 5, '-': 5, '*': 6, '/': 6, '//': 6, '%': 6, '^': 8}
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
KW = set('and break do else elseif end false for function if in local nil not or repeat return then true until while continue'.split())

def lstr(b):
    if isinstance(b, str): b = b.encode('latin1', 'replace')
    out = []
    for i, c in enumerate(b):
        if c == 92: out.append('\\\\')
        elif c == 34: out.append('\\"')
        elif c == 10: out.append('\\n')
        elif c == 13: out.append('\\r')
        elif c == 9: out.append('\\t')
        elif 32 <= c < 127: out.append(chr(c))
        else:
            nxt = b[i + 1] if i + 1 < len(b) else None
            out.append('\\%03d' % c if nxt is not None and 48 <= nxt <= 57 else '\\%d' % c)
    return '"' + ''.join(out) + '"'

def num(v):
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, int): return str(v)
    if isinstance(v, float):
        if v != v: return '(0/0)'
        if v == float('inf'): return 'math.huge'
        if v == float('-inf'): return '-math.huge'
        if v.is_integer() and abs(v) < 2 ** 53: return str(int(v))
        r = repr(v)
        return r
    return str(v)

class Fmt:
    def __init__(self, names=None):
        self.names = names or {}

    def k(self, v):
        if v is None: return 'nil'
        if isinstance(v, bool): return 'true' if v else 'false'
        if isinstance(v, (int, float)): return num(v)
        if isinstance(v, bytes): return lstr(v)
        if hasattr(v, 'raw'): return '--[[encrypted]] ' + lstr(v.raw)
        return repr(v)

    def e(self, x, prec=0):
        h = x[0]
        if h == 'K': return self.k(x[1])
        if h == 'R': return self.names.get(('R', x[1]), 'r%d' % x[1])
        if h == 'RX': return 'R[' + self.e(x[1]) + ']'
        if h == 'ACC': return 'acc'
        if h == 'S': return self.names.get(('S', x[1]), 's%d' % x[1])
        if h == 'SX': return 'S[' + self.e(x[1]) + ']'
        if h == 'TOP': return 'top'
        if h == 'U': return self.names.get(('U', x[1]), 'u%d' % x[1])
        if h == 'UX': return 'U[' + self.e(x[1]) + ']'
        if h == 'ENV': return '_ENV'
        if h == 'VA': return 'va[' + self.e(x[1]) + ']'
        if h == 'NVA': return 'select("#", ...)'
        if h == 'RET': return 'ret[' + self.e(x[1]) + ']'
        if h == 'T': return self.names.get(('T', x[1]), 't%d' % x[1])
        if h == 'L': return x[1]
        if h == 'FN': return x[1]
        if h == 'VMVAR': return 'vm_' + x[1]
        if h == 'CONTAINER': return '<' + x[1] + '>'
        if h == 'IDX':
            o, key = x[1], x[2]
            if o == ('ENV',) and key[0] == 'K' and isinstance(key[1], bytes) and IDENT.match(key[1].decode('latin1')) and key[1].decode('latin1') not in KW:
                return key[1].decode('latin1')
            os_ = self.e(o, 10)
            if o[0] not in ('R', 'S', 'T', 'U', 'IDX', 'CALL', 'L', 'FN', 'K', 'W', 'ACC') and not os_.startswith('('): os_ = '(' + os_ + ')'
            if o[0] == 'K': os_ = '(' + os_ + ')'
            if key[0] == 'K' and isinstance(key[1], bytes):
                s = key[1].decode('latin1')
                if IDENT.match(s) and s not in KW: return os_ + '.' + s
            return os_ + '[' + self.e(key) + ']'
        if h == 'CALL':
            f = x[1]
            fs = self.e(f, 10)
            if f[0] in ('CLOSURE', 'NATIVE', 'BIN', 'UN', 'K', 'NEWT', 'IFE'): fs = '(' + fs + ')'
            return fs + '(' + ', '.join(self.e(a) for a in x[2]) + ')'
        if h == 'METHOD':
            return self.e(x[1], 10) + ':' + x[2] + '(' + ', '.join(self.e(a) for a in x[3]) + ')'
        if h == 'BIN':
            op = x[1]; p = PREC[op]
            ra = op in ('..', '^')
            s = self.e(x[2], p + (1 if ra else 0)) + ' ' + op + ' ' + self.e(x[3], p + (0 if ra else 1))
            return '(' + s + ')' if p < prec else s
        if h == 'UN':
            op = x[1]
            s = (op + ' ' if op == 'not' else op) + self.e(x[2], 7)
            if op == '-' and s.startswith('--'): s = '-(' + s[1:] + ')'
            return '(' + s + ')' if prec > 7 else s
        if h == 'IFE':
            s = 'if ' + self.e(x[1]) + ' then ' + self.e(x[2]) + ' else ' + self.e(x[3])
            return '(' + s + ')' if prec > 0 else s
        if h == 'NEWT':
            items = []
            for it in x[1]:
                if isinstance(it, tuple) and it[0] == 'ITEM': items.append(self.e(it[1]))
                elif isinstance(it, tuple) and it[0] == 'KV':
                    kk = it[1]
                    if kk[0] == 'K' and isinstance(kk[1], bytes) and IDENT.match(kk[1].decode('latin1')) and kk[1].decode('latin1') not in KW:
                        items.append(kk[1].decode('latin1') + ' = ' + self.e(it[2]))
                    else:
                        items.append('[' + self.e(kk) + '] = ' + self.e(it[2]))
                else: items.append(self.e(it))
            return '{' + (' ' + ', '.join(items) + ' ' if items else '') + '}'
        if h == 'CAPS':
            return '{' + ', '.join(self.e(a) for a in x[1]) + '}'
        if h == 'CLOSURE':
            return 'closure<p%d>(%s)' % (x[1].id, self.e(x[2]))
        if h == 'NATIVE':
            return 'native<%d>(%s)' % (x[1], ', '.join(self.e(a) for a in x[2]))
        if h == 'FUNC':     # lifted nested function (text already rendered)
            return x[1]
        if h == 'PACKN': return 'packn(' + ', '.join(self.e(a) for a in x[1]) + ')'
        if h == 'GENITER': return 'geniter(' + ', '.join(self.e(a) for a in x[1]) + ')'
        if h == 'MULTI': return ', '.join(self.e(a) for a in x[1])
        if h == 'UNPACKSTACK': return 'unpack(S, %s, %s)' % (self.e(x[1]), self.e(x[2]))
        if h == 'VARARGS': return '...'
        if h == 'GLOBALFN': return x[1]
        return '<%r>' % (x,)

    def s(self, st, ind=''):
        h = st[0]
        P = lambda t: ind + t + '\n'
        if h == 'SET':
            t = self.e(st[1]) + ' = ' + self.e(st[2])
            return P((';' if t.startswith('(') else '') + t)
        if h == 'MSET': return P(', '.join(self.e(a) for a in st[1]) + ' = ' + ', '.join(self.e(b) for b in st[2]))
        if h == 'LOCAL': return P('local ' + self.e(st[1]) + ' = ' + self.e(st[2]))
        if h == 'LOCALS': return P('local ' + ', '.join(self.e(t) for t in st[1]) + ' = ' + self.e(st[2]))
        if h == 'DECL': return P('local ' + ', '.join(self.e(t) for t in st[1]))
        if h == 'EXPR':
            t = self.e(st[1])
            return P((';' if t.startswith('(') else '') + t)
        if h == 'IF':
            out = P('if ' + self.e(st[1]) + ' then') + self.block(st[2], ind + '    ')
            els = st[3]
            while len(els) == 1 and els[0][0] == 'IF':
                e2 = els[0]
                out += P('elseif ' + self.e(e2[1]) + ' then') + self.block(e2[2], ind + '    ')
                els = e2[3]
            if els: out += P('else') + self.block(els, ind + '    ')
            return out + P('end')
        if h == 'FOR':
            return P('for %s = %s, %s%s do' % (self.e(st[1]), self.e(st[2]), self.e(st[3]), '' if st[4] == ('K', 1) else ', ' + self.e(st[4]))) + self.block(st[5], ind + '    ') + P('end')
        if h == 'FORIN':
            return P('for %s in %s do' % (', '.join(self.e(v) for v in st[1]), ', '.join(self.e(v) for v in st[2]))) + self.block(st[3], ind + '    ') + P('end')
        if h == 'WHILE':
            return P('while ' + self.e(st[1]) + ' do') + self.block(st[2], ind + '    ') + P('end')
        if h == 'REPEAT':
            return P('repeat') + self.block(st[3] + st[1], ind + '    ') + P('until ' + self.e(st[2]))
        if h == 'DO': return P('do') + self.block(st[1], ind + '    ') + P('end')
        if h == 'BREAK': return P('break')
        if h == 'CONTINUE': return P('continue')
        if h == 'LOOPEND': return ''
        if h == 'RETURN': return P(('return ' + ', '.join(self.e(v) for v in st[1])).rstrip())
        if h == 'NEXT': return P('goto %d' % st[1])
        if h == 'GOTO': return P('goto %d' % st[1])
        if h == 'GOTOX': return P('goto [' + self.e(st[1]) + ']')
        if h == 'CLOSEUPV': return P('-- close upvalues')
        if h == 'ERRPATH': return P('error("unreachable: %s")' % st[1].replace('"', "'"))
        if h == 'COMMENT': return P('-- ' + st[1])
        if h == 'SETLISTM':
            return P('do local __m = table.pack(%s) for __k = 1, __m.n do %s[%d + __k] = __m[__k] end end' % (self.e(st[2]), self.e(st[1]), st[3] - 1))
        if h == 'RAW': return ''.join(ind + l + '\n' for l in st[1].split('\n'))
        return P('--[[%r]]' % (st,))

    def block(self, sts, ind):
        return ''.join(self.s(x, ind) for x in sts)
