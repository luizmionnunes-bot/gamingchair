#!/usr/bin/env python3
"""Lua stdlib (subset) for luaeval, under the stageR renamed names.
Strings are byte strings represented as latin-1 Python str (1 char == 1 byte)."""
import math, functools
from luaeval import LuaTable, LuaError, tostr, tonum

def _s(x):
    if isinstance(x,str): return x
    if isinstance(x,(int,float)): return tostr(x)
    raise LuaError('expected string, got %s'%type(x).__name__)
def _i(x):
    n=tonum(x);
    if n is None: raise LuaError('expected number')
    return int(n)

# ---- string ----
def str_char(*a): return ''.join(chr(_i(x)&0xff if False else _i(x)) for x in a)
def str_byte(s,i=1,j=None):
    s=_s(s); i=_i(i); j=_i(j) if j is not None else i
    L=len(s)
    if i<0: i=L+i+1
    if j<0: j=L+j+1
    i=max(i,1); j=min(j,L)
    return [float(ord(s[k-1])) for k in range(i,j+1)]
def str_sub(s,i=1,j=-1):
    s=_s(s); L=len(s); i=_i(i); j=_i(j) if j is not None else -1
    if i<0: i=max(L+i+1,1)
    elif i==0: i=1
    if j<0: j=L+j+1
    elif j>L: j=L
    if i>j: return ''
    return s[i-1:j]
def str_rep(s,n,sep=None):
    s=_s(s); n=_i(n)
    if n<=0: return ''
    if sep: return _s(sep).join([s]*n)
    return s*n
def str_len(s): return float(len(_s(s)))
def str_reverse(s): return _s(s)[::-1]
def str_format(fmt,*a):
    # minimal: handle %d %s %x %c %02d etc via python after converting
    fmt=_s(fmt); out=[]; ai=0; i=0
    import re
    def repl(m):
        nonlocal ai
        spec=m.group(0)
        if spec=='%%': return '%'
        conv=spec[-1]; v=a[ai]; ai+=1
        if conv in 'dioxXu': return (spec[:-1]+('d' if conv in 'iu' else conv))%_i(v)
        if conv in 'eEfgG': return spec%float(tonum(v))
        if conv=='s': return spec% _s(v) if False else (spec[:-1]+'s')%tostr(v)
        if conv=='c': return chr(_i(v))
        if conv=='q': return '"'+_s(v).replace('\\','\\\\').replace('"','\\"')+'"'
        return spec
    return re.sub(r'%[-+ #0-9.]*[diouxXeEfgGqsc%]', repl, fmt)

def _lua_pat_to_re(pat):
    # translate a Lua pattern to a python regex (subset). Returns compiled or None.
    import re
    MAGIC=set('^$*+?.([%-])')
    classmap={'a':'[a-zA-Z]','A':'[^a-zA-Z]','d':'[0-9]','D':'[^0-9]','s':'[ \\t\\n\\r\\f\\v]',
              'S':'[^ \\t\\n\\r\\f\\v]','w':'[a-zA-Z0-9]','W':'[^a-zA-Z0-9]','l':'[a-z]','u':'[A-Z]',
              'p':'[\\!-/\\:-@\\[-`\\{-~]','c':'[\\x00-\\x1f]','x':'[0-9a-fA-F]'}
    out=[]; i=0; n=len(pat)
    while i<n:
        c=pat[i]
        if c=='%':
            i+=1; nc=pat[i]
            if nc in classmap: out.append(classmap[nc])
            else: out.append(re.escape(nc))
            i+=1
        elif c in '^$':
            out.append(c); i+=1
        elif c=='.':
            out.append('.'); i+=1
        elif c in '*+?':
            out.append(c); i+=1
        elif c=='-':
            out.append('*?'); i+=1  # lua '-' = lazy *
        elif c=='(' :
            out.append('('); i+=1
        elif c==')':
            out.append(')'); i+=1
        elif c=='[':
            # char class: copy until ]
            j=i+1; cls='['
            if j<n and pat[j]=='^': cls+='^'; j+=1
            while j<n and pat[j]!=']':
                if pat[j]=='%' and j+1<n:
                    nc=pat[j+1]
                    cls+= classmap.get(nc, re.escape(nc))[1:-1] if nc in classmap else re.escape(nc)
                    j+=2
                else:
                    cls+=re.escape(pat[j]) if pat[j] in '\\^]' else pat[j]; j+=1
            cls+=']'; out.append(cls); i=j+1
        else:
            out.append(re.escape(c)); i+=1
    try:
        return re.compile(''.join(out), re.DOTALL)
    except re.error:
        return None

def str_gsub(s,pat,repl,n=None):
    import re
    s=_s(s); pat=_s(pat)
    rx=_lua_pat_to_re(pat)
    if rx is None: raise LuaError('gsub pattern unsupported: %r'%pat)
    count=[0]; maxn=_i(n) if n is not None else -1
    def do(m):
        if maxn>=0 and count[0]>=maxn: return m.group(0)
        count[0]+=1
        if isinstance(repl,str) or isinstance(repl,(int,float)):
            r=_s(repl)
            # handle %0 %1..
            def sub2(mm):
                d=mm.group(1)
                if d=='0': return m.group(0)
                if d=='%': return '%'
                g=m.group(int(d)); return g if g is not None else ''
            return re.sub(r'%([0-9%])', sub2, r)
        raise LuaError('gsub repl type unsupported')
    out=rx.sub(do, s) if maxn<0 else rx.sub(do, s)
    return [out, float(count[0])]

def str_find(s,pat,init=1,plain=None):
    import re
    s=_s(s); pat=_s(pat); init=_i(init)
    if init<0: init=len(s)+init+1
    if init<1: init=1
    if plain:
        idx=s.find(pat, init-1)
        if idx<0: return [None]
        return [float(idx+1), float(idx+len(pat))]
    rx=_lua_pat_to_re(pat)
    if rx is None: raise LuaError('find pattern unsupported: %r'%pat)
    m=rx.search(s, init-1)
    if not m: return [None]
    res=[float(m.start()+1), float(m.end())]
    res+=[g for g in m.groups()]
    return res

def str_match(s,pat,init=1):
    import re
    s=_s(s); pat=_s(pat); init=_i(init)
    if init<0: init=len(s)+init+1
    if init<1: init=1
    rx=_lua_pat_to_re(pat)
    if rx is None: raise LuaError('match pattern unsupported: %r'%pat)
    m=rx.search(s, init-1)
    if not m: return [None]
    if m.groups(): return list(m.groups())
    return [m.group(0)]

def str_gmatch(s,pat):
    import re
    s=_s(s); rx=_lua_pat_to_re(_s(pat))
    if rx is None: raise LuaError('gmatch pattern unsupported')
    it=rx.finditer(s)
    def nxt(*_):
        try: m=next(it)
        except StopIteration: return [None]
        if m.groups(): return list(m.groups())
        return [m.group(0)]
    return nxt

# ---- table ----
def tbl_concat(t,sep=None,i=1,j=None):
    sep=_s(sep) if sep is not None else ''
    i=_i(i); j=_i(j) if j is not None else t.length()
    parts=[]
    for k in range(i,j+1):
        v=t.get(k); parts.append(tostr(v))
    return sep.join(parts)
def tbl_insert(t,a,b=None):
    if b is None:
        t.set(t.length()+1, a)
    else:
        pos=_i(a); n=t.length()
        for k in range(n,pos-1,-1): t.set(k+1,t.get(k))
        t.set(pos,b)
def tbl_remove(t,pos=None):
    n=t.length()
    if n==0 and pos is None: return None
    pos=_i(pos) if pos is not None else n
    v=t.get(pos)
    for k in range(pos,n): t.set(k,t.get(k+1))
    t.set(n,None)
    return v

# ---- math ----
def math_floor(x): return float(math.floor(tonum(x)))
def math_ceil(x): return float(math.ceil(tonum(x)))
def math_min(*a): return float(min(tonum(x) for x in a))
def math_max(*a): return float(max(tonum(x) for x in a))
def math_abs(x): return float(abs(tonum(x)))
def math_huge(): return math.inf

def install(env, interp):
    def reg(name, fn): env.define(name, fn)
    reg('str_char', str_char); reg('str_byte', str_byte); reg('str_sub', str_sub)
    reg('str_rep', str_rep); reg('str_len', str_len); reg('str_reverse', str_reverse)
    reg('str_format', str_format); reg('str_gsub', str_gsub); reg('str_find', str_find)
    reg('str_match', str_match); reg('str_gmatch', str_gmatch)
    reg('tbl_concat', tbl_concat); reg('tbl_insert', tbl_insert); reg('tbl_remove', tbl_remove)
    reg('math_floor', math_floor); reg('math_min', math_min); reg('math_abs', math_abs)
    reg('const_nil', None); reg('math_huge', math.inf)
    reg('tonumber_', lambda x,*a: tonum(x))
    reg('tostring_', lambda x: tostr(x))
    reg('select_', lambda i,*a: (float(len(a)) if (isinstance(i,str) and i=='#') else list(a)[int(tonum(i))-1:]))
    reg('error_', lambda *a: (_ for _ in ()).throw(LuaError('lua error: '+tostr(a[0] if a else None))))
    reg('next_', None); reg('next_b', None)
    reg('rawget_', lambda t,k: t.get(k) if hasattr(t,'get') else None)
    # table.sort needs the interpreter to call comparators
    def tbl_sort(t, comp=None):
        n=t.length(); arr=[t.get(k) for k in range(1,n+1)]
        if comp is None:
            arr.sort(key=functools.cmp_to_key(lambda a,b: -1 if _default_lt(a,b) else (1 if _default_lt(b,a) else 0)))
        else:
            def c(a,b):
                lt_ab = bool_is_true(interp.call(comp,[a,b]))
                if lt_ab: return -1
                lt_ba = bool_is_true(interp.call(comp,[b,a]))
                return 1 if lt_ba else 0
            arr.sort(key=functools.cmp_to_key(c))
        for k,v in enumerate(arr,1): t.set(k,v)
    reg('tbl_sort', tbl_sort)
    # setmetatable
    def setmeta(t, mt):
        t.meta=mt; return t
    reg('setmetatable_', setmeta)
    reg('getfenv_', lambda *a: None)
    # decode_p22 placeholder (a number-decoder closure); install real one if needed
    reg('decode_p22', None)
    reg('co_yield', None); reg('co_wrap', None)
    reg('tbl_unpack', _unpack); reg('str_unpack', None)

## ================= full Luau global runtime (static, universal semantics) ======
class Buffer:
    __slots__=('b',)
    def __init__(self,n): self.b=bytearray(int(n))
def _mk_table(d):
    t=LuaTable()
    for k,v in d.items(): t.set(k,v)
    return t
def install_globals(env, interp):
    import struct, random
    def ret(*vs): return list(vs)
    # ---- string library table (global) ----
    strlib={'char':str_char,'byte':str_byte,'sub':str_sub,'rep':str_rep,'len':str_len,
            'reverse':str_reverse,'format':str_format,'gsub':str_gsub,'find':str_find,
            'match':str_match,'gmatch':str_gmatch,'lower':lambda s:_s(s).lower(),
            'upper':lambda s:_s(s).upper(),'split':None}
    def str_unpack(fmt,data,pos=1): raise LuaError('string.unpack unsupported')
    strlib['unpack']=str_unpack; strlib['pack']=lambda *a:(_ for _ in ()).throw(LuaError('string.pack unsupported'))
    env.define('string', _mk_table(strlib))
    # ---- table library ----
    def tbl_create(n,v=None):
        t=LuaTable()
        for k in range(1,int(tonum(n))+1): t.set(k, v)
        return t
    def tbl_move(a1,f,e,tpos,a2=None):
        a2=a2 if a2 is not None else a1
        f=int(tonum(f)); e=int(tonum(e)); tpos=int(tonum(tpos))
        vals=[a1.get(k) for k in range(f,e+1)]
        for off,v in enumerate(vals): a2.set(tpos+off, v)
        return a2
    def tbl_find(t,val,init=1):
        n=t.length()
        for k in range(int(tonum(init)),n+1):
            if t.get(k)==val: return float(k)
        return None
    tbllib={'concat':tbl_concat,'insert':tbl_insert,'remove':tbl_remove,'sort':env.get('tbl_sort'),
            'unpack':_unpack,'create':tbl_create,'move':tbl_move,'find':tbl_find,
            'pack':lambda *a:_pack(a),'clear':lambda t:t.hash.clear(),'getn':lambda t:float(t.length()),
            'clone':_clone}
    env.define('table', _mk_table(tbllib))
    # ---- math ----
    rng=random.Random(0)
    def math_random(a=None,b=None):
        if a is None: return rng.random()
        a=int(tonum(a))
        if b is None: return float(rng.randint(1,a))
        return float(rng.randint(a,int(tonum(b))))
    mathlib={'floor':math_floor,'ceil':math_ceil,'abs':math_abs,'min':math_min,'max':math_max,
             'huge':math.inf,'pi':math.pi,'sqrt':lambda x:float(math.sqrt(tonum(x))),
             'random':math_random,'randomseed':lambda *a:None,'fmod':lambda a,b:math.fmod(tonum(a),tonum(b)),
             'modf':lambda x:[float(int(tonum(x))),tonum(x)-int(tonum(x))],'pow':lambda a,b:tonum(a)**tonum(b),
             'log':lambda x,*b:float(math.log(tonum(x),tonum(b[0])) if b else math.log(tonum(x))),
             'sin':lambda x:math.sin(tonum(x)),'cos':lambda x:math.cos(tonum(x)),
             'clamp':lambda x,lo,hi:float(max(tonum(lo),min(tonum(hi),tonum(x))))}
    env.define('math', _mk_table(mathlib))
    # ---- bit32 ----
    M=0xffffffff
    def _u(x): return int(tonum(x))&M
    def band(*a):
        r=M
        for x in a: r&=_u(x)
        return float(r)
    def bor(*a):
        r=0
        for x in a: r|=_u(x)
        return float(r)
    def bxor(*a):
        r=0
        for x in a: r^=_u(x)
        return float(r)
    def lshift(x,n): n=int(tonum(n)); return float((_u(x)<<n)&M) if 0<=n<32 else 0.0
    def rshift(x,n): n=int(tonum(n)); return float(_u(x)>>n) if 0<=n<32 else 0.0
    def arshift(x,n):
        n=int(tonum(n)); v=_u(x)
        if n<=0: return float((v<<(-n))&M)
        if n>=32: return float(M if (v>>31)&1 else 0)
        sign=(v>>31)&1
        r=v>>n
        if sign: r|=(M<<(32-n))&M
        return float(r)
    def extract(x,field,width=1):
        f=int(tonum(field)); w=int(tonum(width)); return float((_u(x)>>f)&((1<<w)-1))
    def replace(x,v,field,width=1):
        f=int(tonum(field)); w=int(tonum(width)); mask=((1<<w)-1)<<f
        return float((_u(x)&~mask | ((int(tonum(v))<<f)&mask))&M)
    bit32={'band':band,'bor':bor,'bxor':bxor,'bnot':lambda x:float((~_u(x))&M),
           'lshift':lshift,'rshift':rshift,'arshift':arshift,'extract':extract,'replace':replace,
           'btest':lambda *a:band(*a)!=0,'lrotate':lambda x,n:float(((_u(x)<<(int(tonum(n))%32))|(_u(x)>>(32-int(tonum(n))%32)))&M),
           'rrotate':lambda x,n:float(((_u(x)>>(int(tonum(n))%32))|(_u(x)<<(32-int(tonum(n))%32)))&M),
           'countlz':lambda x:float(32-(_u(x).bit_length())),'countrz':lambda x:float((_u(x)&-_u(x)).bit_length()-1 if _u(x) else 32)}
    env.define('bit32', _mk_table(bit32))
    # ---- buffer ----
    def buf_create(n): return Buffer(n)
    def buf_fromstring(s): b=Buffer(0); b.b=bytearray(_s(s).encode('latin-1','surrogateescape')); return b
    def buf_tostring(b): return b.b.decode('latin-1','surrogateescape')
    def buf_len(b): return float(len(b.b))
    def ru(b,o,n,signed=False):
        o=int(tonum(o)); val=int.from_bytes(b.b[o:o+n],'little',signed=signed); return float(val)
    def wu(b,o,v,n):
        o=int(tonum(o)); b.b[o:o+n]=(int(tonum(v))&((1<<(8*n))-1)).to_bytes(n,'little')
    buflib={'create':buf_create,'fromstring':buf_fromstring,'tostring':buf_tostring,'len':buf_len,
            'readu8':lambda b,o:ru(b,o,1),'readi8':lambda b,o:ru(b,o,1,True),
            'readu16':lambda b,o:ru(b,o,2),'readi16':lambda b,o:ru(b,o,2,True),
            'readu32':lambda b,o:ru(b,o,4),'readi32':lambda b,o:ru(b,o,4,True),
            'writeu8':lambda b,o,v:wu(b,o,v,1),'writei8':lambda b,o,v:wu(b,o,v,1),
            'writeu16':lambda b,o,v:wu(b,o,v,2),'writei16':lambda b,o,v:wu(b,o,v,2),
            'writeu32':lambda b,o,v:wu(b,o,v,4),'writei32':lambda b,o,v:wu(b,o,v,4),
            'readf32':lambda b,o:float(struct.unpack('<f',b.b[int(tonum(o)):int(tonum(o))+4])[0]),
            'readf64':lambda b,o:float(struct.unpack('<d',b.b[int(tonum(o)):int(tonum(o))+8])[0]),
            'readstring':lambda b,o,n:b.b[int(tonum(o)):int(tonum(o))+int(tonum(n))].decode('latin-1','surrogateescape'),
            'writestring':lambda b,o,s,*n:b.b.__setitem__(slice(int(tonum(o)),int(tonum(o))+len(_s(s))), _s(s).encode('latin-1','surrogateescape')),
            'copy':lambda d,do,s,so=0,n=None:d.b.__setitem__(slice(int(tonum(do)),int(tonum(do))+(int(tonum(n)) if n is not None else len(s.b)-int(tonum(so)))), s.b[int(tonum(so)):int(tonum(so))+(int(tonum(n)) if n is not None else len(s.b)-int(tonum(so)))]),
            'fill':lambda b,o,v,n=None:None}
    env.define('buffer', _mk_table(buflib))
    # ---- coroutine (synchronous enough for setup) / task (no-op scheduler) ----
    corolib={'create':lambda f:f,'wrap':lambda f:f,'resume':lambda c,*a:[True]+interp.call(c,list(a)),
             'yield':lambda *a:list(a),'status':lambda c:'suspended','isyieldable':lambda:False,'running':lambda:[None,True]}
    env.define('coroutine', _mk_table(corolib))
    tasklib={'spawn':lambda f,*a:None,'defer':lambda f,*a:None,'delay':lambda d,f,*a:None,
             'wait':lambda *a:0.0,'cancel':lambda *a:None}
    env.define('task', _mk_table(tasklib))
    env.define('os', _mk_table({'time':lambda *a:0.0,'clock':lambda:0.0,'date':lambda *a:''}))
    # ---- global builtins ----
    def _type(v):
        if v is None: return 'nil'
        if isinstance(v,bool): return 'boolean'
        if isinstance(v,(int,float)): return 'number'
        if isinstance(v,str): return 'string'
        if isinstance(v,LuaTable): return 'table'
        if isinstance(v,Buffer): return 'buffer'
        return 'function'
    env.define('type', _type)
    env.define('typeof', _type)
    env.define('tostring', tostr)
    env.define('tonumber', lambda x,*a: tonum(x))
    env.define('rawget', lambda t,k: t.get(k) if isinstance(t,LuaTable) else None)
    env.define('rawset', lambda t,k,v: (t.set(k,v),t)[1])
    env.define('rawequal', lambda a,b: a is b or a==b)
    env.define('rawlen', lambda t: float(t.length() if isinstance(t,LuaTable) else len(_s(t))))
    def _setmeta(t,mt): t.meta=mt; return t
    env.define('setmetatable', _setmeta)
    env.define('getmetatable', lambda t: getattr(t,'meta',None))
    env.define('assert', lambda v,*m: (_ for _ in ()).throw(LuaError('assertion failed'+((': '+tostr(m[0])) if m else ''))) if (v is None or v is False) else [v]+list(m))
    env.define('error', lambda *a: (_ for _ in ()).throw(LuaError('error: '+tostr(a[0] if a else None))))
    env.define('select', lambda i,*a: (float(len(a)) if (isinstance(i,str) and i=='#') else list(a)[int(tonum(i))-1:]))
    env.define('unpack', _unpack)
    env.define('newproxy', lambda *a: LuaTable())
    def _next(t,k=None):
        keys=list(t.hash.keys())
        if k is None: return [keys[0], t.hash[keys[0]]] if keys else [None]
        try: i=keys.index(k if not isinstance(k,float) or not k.is_integer() else int(k))
        except ValueError: return [None]
        if i+1<len(keys): nk=keys[i+1]; return [nk, t.hash[nk]]
        return [None]
    env.define('next', _next)
    def _pairs(t): return [_next, t, None]
    env.define('pairs', _pairs)
    def _ipairs(t):
        def it(tb,i):
            i=int(tonum(i))+1; v=tb.get(i)
            return [None] if v is None else [float(i),v]
        return [it, t, 0.0]
    env.define('ipairs', _ipairs)
    def _pcall(f,*a):
        try:
            r=interp.call(f,list(a)); return [True]+r
        except Exception as e:
            return [False, 'pcall: '+str(e)]
    env.define('pcall', _pcall)
    env.define('xpcall', lambda f,h,*a: _pcall(f,*a))
    env.define('_G', LuaTable())
    env.define('loadstring', lambda *a:[None,'loadstring disabled']); env.define('load', lambda *a:[None,'load disabled'])
    env.define('print', lambda *a: None)

def _pack(a):
    t=LuaTable()
    for i,v in enumerate(a,1): t.set(i,v)
    t.set('n', float(len(a)))
    return t
def _clone(t):
    n=LuaTable(); n.hash=dict(t.hash); n.meta=t.meta; return n

def _unpack(t,i=1,j=None):
    i=int(tonum(i)); j=int(tonum(j)) if j is not None else t.length()
    return [t.get(k) for k in range(i,j+1)]
def _default_lt(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)): return a<b
    if isinstance(a,str) and isinstance(b,str): return a<b
    return False
def bool_is_true(res):
    v=res[0] if isinstance(res,list) and res else (res if not isinstance(res,list) else None)
    return not (v is None or v is False)
