#!/usr/bin/env python3
"""A small, faithful Lua(u)-subset tree-walking interpreter over luau-ast JSON.

Purpose: STATIC resolution of the obfuscated string pool. We interpret only the
PURE decoder subgraph (t[18] and its callees) using the file's literal constants
(t[1]) — no Luau runtime, no game environment, no VM. Partial evaluation of a pure
function on constant input.

Supports the node set the decoder uses; raises LuaError('unsupported ...') otherwise
so we can extend iteratively.
"""
import sys, math

# ---------- Lua values ----------
class LuaError(Exception): pass

class LuaTable:
    __slots__=('hash','meta')
    def __init__(self): self.hash={}; self.meta=None
    def get(self,k):
        if isinstance(k,float) and k.is_integer(): k=int(k)
        return self.hash.get(k)
    def set(self,k,v):
        if isinstance(k,float) and k.is_integer(): k=int(k)
        if v is None: self.hash.pop(k,None)
        else: self.hash[k]=v
    def length(self):
        n=0
        while (n+1) in self.hash and self.hash[n+1] is not None: n+=1
        return n

class LuaFunction:
    __slots__=('node','env','name')
    def __init__(self,node,env,name=None): self.node=node; self.env=env; self.name=name

# python callable wrapper = builtin

# ---------- environment ----------
class Env:
    __slots__=('vars','parent')
    def __init__(self,parent=None): self.vars={}; self.parent=parent
    def get(self,name):
        e=self
        while e is not None:
            if name in e.vars: return e.vars[name]
            e=e.parent
        return None  # global miss -> nil
    def set_existing(self,name,val):
        e=self
        while e is not None:
            if name in e.vars: e.vars[name]=val; return True
            e=e.parent
        return False
    def define(self,name,val): self.vars[name]=val

# sentinel for control flow
class Return(Exception):
    def __init__(self,vals): self.vals=vals
class Break(Exception): pass
class Continue(Exception): pass
class StopDecode(Exception):
    def __init__(self,val): self.val=val

def nt(n): return n.get('type') if isinstance(n,dict) else None
def truthy(v): return not (v is None or v is False)

def tostr(v):
    if v is None: return 'nil'
    if v is True: return 'true'
    if v is False: return 'false'
    if isinstance(v,float):
        if v.is_integer(): return str(int(v))
        return repr(v)
    if isinstance(v,int): return str(v)
    if isinstance(v,str): return v
    return '<table>' if isinstance(v,LuaTable) else '<fn>'

def tonum(v):
    if isinstance(v,(int,float)): return v
    if isinstance(v,str):
        try:
            if v.strip().lower().startswith('0x'): return float(int(v.strip(),16))
            f=float(v); return f
        except: return None
    return None

class Interp:
    def __init__(self, root_env):
        self.root=root_env
        self.watch_table=None   # LuaTable
        self.watch_key=None     # key -> raise StopDecode(value) on assign
        self.steps=0
        self.cur_loc=None
        self.max_steps=0        # 0 = no cap
        self.progress_every=0
    # ---- call ----
    def call(self, fn, args):
        if callable(fn) and not isinstance(fn,(LuaFunction,)):
            r=fn(*args)
            if r is None: return []
            if isinstance(r,list): return r
            if isinstance(r,tuple): return list(r)
            return [r]
        if isinstance(fn,LuaFunction):
            env=Env(fn.env)
            params=fn.node['args']
            for i,p in enumerate(params):
                env.define(p['name'], args[i] if i<len(args) else None)
            if fn.node.get('vararg'):
                env.define('...', args[len(params):])
            try:
                self.exec_block(fn.node['body'], env)
            except Return as r:
                return r.vals
            return []
        raise LuaError('attempt to call a %s value'%type(fn).__name__)
    # ---- statements ----
    def exec_block(self, block, env):
        stmts = block['body'] if nt(block)=='AstStatBlock' else block
        for s in stmts:
            self.exec_stat(s, env)
    def exec_stat(self, s, env):
        t=nt(s)
        self.steps+=1
        if s.get('location') is not None: self.cur_loc=s['location']
        if self.progress_every and self.steps % self.progress_every==0:
            sys.stderr.write('steps=%d at %s\n'%(self.steps,self.cur_loc)); sys.stderr.flush()
        if self.max_steps and self.steps>self.max_steps:
            raise LuaError('step cap exceeded near %s'%self.cur_loc)
        if t=='AstStatLocal':
            vals=self.eval_list(s['values'], env, len(s['vars']))
            for i,var in enumerate(s['vars']):
                env.define(var['name'], vals[i] if i<len(vals) else None)
        elif t=='AstStatAssign':
            vals=self.eval_list(s['values'], env, len(s['vars']))
            for i,var in enumerate(s['vars']):
                self.assign(var, vals[i] if i<len(vals) else None, env)
        elif t=='AstStatCompoundAssign':
            # a op= b
            cur=self.eval(s['var'],env)
            rhs=self.eval(s['value'],env)
            op=s['op'].replace('Compound','') if False else s['op']
            res=self.binop(s['op'], cur, rhs)
            self.assign(s['var'], res, env)
        elif t=='AstStatExpr':
            self.eval(s['expr'], env)  # discard
        elif t=='AstStatLocalFunction':
            env.define(s['name']['name'], LuaFunction(s['func'], env, s['name']['name']))
        elif t=='AstStatFunction':
            self.assign(s['name'], LuaFunction(s['func'], env), env)
        elif t=='AstStatReturn':
            raise Return(self.eval_list(s['list'], env, -1))
        elif t=='AstStatBreak':
            raise Break()
        elif t=='AstStatContinue':
            raise Continue()
        elif t=='AstStatIf':
            if truthy(self.eval(s['condition'],env)):
                self.exec_block_scoped(s['thenbody'], env)
            elif s.get('elsebody') is not None:
                eb=s['elsebody']
                if nt(eb)=='AstStatIf': self.exec_stat(eb, env)
                else: self.exec_block_scoped(eb, env)
        elif t=='AstStatWhile':
            while truthy(self.eval(s['condition'],env)):
                try: self.exec_block_scoped(s['body'], env)
                except Break: break
                except Continue: continue
        elif t=='AstStatRepeat':
            while True:
                benv=Env(env)
                brk=False
                try:
                    self.exec_block(s['body'], benv)
                except Break: break
                except Continue: pass
                if truthy(self.eval(s['condition'], benv)): break
        elif t=='AstStatFor':
            var=s['var']['name']
            a=tonum(self.eval(s['from'],env)); b=tonum(self.eval(s['to'],env))
            step=tonum(self.eval(s['step'],env)) if s.get('step') else 1
            i=a
            while (step>0 and i<=b) or (step<0 and i>=b):
                benv=Env(env); benv.define(var, i)
                try: self.exec_block(s['body'], benv)
                except Break: break
                except Continue: pass
                i+=step
        elif t=='AstStatForIn':
            # generic for: vars in explist   (support ipairs/pairs/next)
            exps=self.eval_list(s['values'],env,3)
            f=exps[0] if len(exps)>0 else None
            st=exps[1] if len(exps)>1 else None
            ctrl=exps[2] if len(exps)>2 else None
            names=[v['name'] for v in s['vars']]
            while True:
                res=self.call(f,[st,ctrl])
                if not res or res[0] is None: break
                ctrl=res[0]
                benv=Env(env)
                for i,nm in enumerate(names): benv.define(nm, res[i] if i<len(res) else None)
                try: self.exec_block(s['body'], benv)
                except Break: break
                except Continue: pass
        elif t=='AstStatBlock':
            self.exec_block_scoped(s, env)
        else:
            raise LuaError('unsupported stat '+str(t))
    def exec_block_scoped(self, block, env):
        self.exec_block(block, Env(env))
    def assign(self, var, val, env):
        t=nt(var)
        if t=='AstExprLocal':
            nm=var['local']['name']
            if not env.set_existing(nm, val): self.root.define(nm,val)
        elif t=='AstExprGlobal':
            self.root.define(var['global'], val)
        elif t=='AstExprIndexExpr':
            obj=self.eval(var['expr'],env); key=self.eval(var['index'],env)
            if not isinstance(obj,LuaTable): raise LuaError('index assign on non-table')
            if obj is self.watch_table and (key==self.watch_key or (isinstance(key,float) and key==float(self.watch_key))):
                raise StopDecode(val)
            obj.set(key,val)
        elif t=='AstExprIndexName':
            obj=self.eval(var['expr'],env)
            if not isinstance(obj,LuaTable): raise LuaError('field assign on non-table')
            obj.set(var['index'],val)
        else: raise LuaError('unsupported assign target '+str(t))
    # ---- expressions ----
    def eval_list(self, exprs, env, want):
        """Evaluate an expression list; last expr may expand to multiple values."""
        vals=[]
        for i,e in enumerate(exprs):
            if i==len(exprs)-1:
                r=self.eval_multi(e,env)
                vals.extend(r)
            else:
                vals.append(self.eval(e,env))
        return vals
    def eval_multi(self,e,env):
        t=nt(e)
        if t=='AstExprCall':
            return self.eval_call(e,env)
        if t=='AstExprVarargs':
            v=env.get('...'); return list(v) if v else []
        return [self.eval(e,env)]
    def eval(self, e, env):
        r=self.eval_multi(e,env) if nt(e) in ('AstExprCall','AstExprVarargs') else None
        if r is not None: return r[0] if r else None
        t=nt(e)
        if t=='AstExprConstantNumber': return float(e['value'])
        if t=='AstExprConstantString': return e['value']
        if t=='AstExprConstantBool': return e['value']
        if t=='AstExprConstantNil': return None
        if t=='AstExprLocal': return env.get(e['local']['name'])
        if t=='AstExprGlobal': return env.get(e['global'])
        if t=='AstExprGroup': return self.eval(e['expr'],env)
        if t=='AstExprIndexExpr':
            obj=self.eval(e['expr'],env); key=self.eval(e['index'],env)
            return self.index(obj,key)
        if t=='AstExprIndexName':
            obj=self.eval(e['expr'],env)
            return self.index(obj,e['index'])
        if t=='AstExprFunction':
            return LuaFunction(e, env)
        if t=='AstExprTable':
            return self.make_table(e,env)
        if t=='AstExprIfElse':
            return self.eval(e['trueExpr'],env) if truthy(self.eval(e['condition'],env)) else self.eval(e['falseExpr'],env)
        if t=='AstExprUnary': return self.unop(e['op'], self.eval(e['expr'],env))
        if t=='AstExprBinary':
            op=e['op']
            if op=='And':
                l=self.eval(e['left'],env); return l if not truthy(l) else self.eval(e['right'],env)
            if op=='Or':
                l=self.eval(e['left'],env); return l if truthy(l) else self.eval(e['right'],env)
            return self.binop(op, self.eval(e['left'],env), self.eval(e['right'],env))
        raise LuaError('unsupported expr '+str(t))
    def eval_call(self,e,env):
        if e.get('self'):
            fn_container=self.eval(e['func']['expr'],env)
            fn=self.index(fn_container, e['func']['index'])
            args=[fn_container]+self.eval_list(e['args'],env,-1)
        else:
            fn=self.eval(e['func'],env)
            args=self.eval_list(e['args'],env,-1)
        if not (callable(fn) or isinstance(fn,LuaFunction)):
            raise LuaError('call non-callable (%s) at func-loc %s'%(type(fn).__name__, e['func'].get('location')))
        return self.call(fn,args)
    def index(self,obj,key):
        if isinstance(obj,LuaTable):
            v=obj.get(key)
            if v is None and obj.meta is not None:
                idx=obj.meta.get('__index')
                if isinstance(idx,LuaTable): return self.index(idx,key)
                if idx is not None: return self.call(idx,[obj,key])[0] if self.call(idx,[obj,key]) else None
            return v
        if isinstance(obj,str):
            # string method access would need a string lib table; decoder shouldn't use it
            raise LuaError('index on string (unsupported)')
        if obj is None: raise LuaError('attempt to index nil with %r'%key)
        raise LuaError('attempt to index %s'%type(obj).__name__)
    def make_table(self,e,env):
        tbl=LuaTable(); arr=1
        items=e.get('items',[])
        for i,it in enumerate(items):
            kind=it.get('kind')
            if it.get('key') is not None:
                k=self.eval(it['key'],env); tbl.set(k,self.eval(it['value'],env))
            else:
                # positional; last may expand
                if i==len(items)-1:
                    for v in self.eval_multi(it['value'],env): tbl.set(arr,v); arr+=1
                else:
                    tbl.set(arr,self.eval(it['value'],env)); arr+=1
        return tbl
    def unop(self,op,v):
        if op=='Minus': return -tonum(v)
        if op=='Not': return not truthy(v)
        if op=='Len':
            if isinstance(v,str): return float(len(v.encode('latin-1','surrogateescape') if False else v))
            if isinstance(v,LuaTable): return float(v.length())
            raise LuaError('len on %s'%type(v).__name__)
        raise LuaError('unop '+op)
    def binop(self,op,l,r):
        if op in ('Add','Sub','Mul','Div','Mod','Pow','FloorDiv'):
            a=tonum(l); b=tonum(r)
            if a is None or b is None: raise LuaError('arith on non-number (%r %s %r)'%(l,op,r))
            if op=='Add': return a+b
            if op=='Sub': return a-b
            if op=='Mul': return a*b
            if op=='Div': return a/b
            if op=='Mod': return a-math.floor(a/b)*b
            if op=='Pow': return a**b
            if op=='FloorDiv': return math.floor(a/b)
        if op=='Concat': return self.concat(l)+self.concat(r)
        if op=='CompareEq': return self.eq(l,r)
        if op=='CompareNe': return not self.eq(l,r)
        if op in ('CompareLt','CompareLe','CompareGt','CompareGe'):
            if isinstance(l,str) and isinstance(r,str): a,b=l,r
            else:
                a=tonum(l); b=tonum(r)
                if a is None or b is None: raise LuaError('compare %r %s %r'%(l,op,r))
            if op=='CompareLt': return a<b
            if op=='CompareLe': return a<=b
            if op=='CompareGt': return a>b
            if op=='CompareGe': return a>=b
        raise LuaError('binop '+op)
    def concat(self,v):
        if isinstance(v,str): return v
        if isinstance(v,(int,float)): return tostr(v)
        raise LuaError('concat on %s'%type(v).__name__)
    def eq(self,l,r):
        if isinstance(l,(int,float)) and isinstance(r,(int,float)): return float(l)==float(r)
        return l is r or l==r if type(l)==type(r) else (l is r)
