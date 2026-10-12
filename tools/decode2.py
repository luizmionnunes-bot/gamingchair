#!/usr/bin/env python3
"""Static decode by interpreting f1's init in Python (no Luau, only this file).

We run f1's bootstrap in the luaeval interpreter with the file's stdlib + constants,
injecting a watched `t` table and stopping the moment `t[19] = t[18](<blob>)` is
assigned -- i.e. right after the string pool is decoded, before any VM/game code.
"""
import json, sys
sys.path.insert(0, __file__.rsplit('/',1)[0])
import sm, luaeval as L, stdlib_lua as S
from luaeval import LuaTable, LuaFunction, Env, Interp, LuaError, StopDecode
nt=sm.nt

AST=sys.argv[1]; SRCP=sys.argv[2]
root=json.load(open(AST))['root']

def find_f1():
    for s in root['body']:
        if nt(s)=='AstStatLocalFunction' and s['name']['name']=='f1':
            return s['func']
    raise SystemExit('f1 not found')

def find_decode_p22():
    # the 22nd argument of the bottom `return f1(...)` / `_G.. = f1(...)` call
    found=[None]
    def visit(n):
        if isinstance(n,list):
            for x in n: visit(x)
            return
        if not isinstance(n,dict): return
        if nt(n)=='AstExprCall' and nt(n['func'])=='AstExprLocal' and n['func']['local']['name']=='f1':
            args=n['args']
            if len(args)>=22 and nt(args[21])=='AstExprFunction':
                found[0]=args[21]
        for v in n.values(): visit(v)
    visit(root)
    return found[0]

def main():
    f1=find_f1()
    rootenv=Env(); interp=Interp(rootenv)
    S.install(rootenv, interp)
    S.install_globals(rootenv, interp)
    # getfenv returns an empty env table -> _ENV[name] lookups are nil -> fallbacks taken
    rootenv.define('getfenv_', lambda *a: LuaTable())
    # decode_p22 closure (pure number decoder) bound from the file
    dp=find_decode_p22()
    if dp is not None:
        rootenv.define('decode_p22', LuaFunction(dp, rootenv, 'decode_p22'))
        print('decode_p22 bound', file=sys.stderr)
    # the injected global t, watched at key 19
    t=LuaTable(); rootenv.define('t', t)
    interp.watch_table=t; interp.watch_key=19
    interp.progress_every=2_000_000
    interp.max_steps=400_000_000
    # run f1 body, skipping the initial `local t = {}`
    body=f1['body']['body']
    env=Env(rootenv)
    # bind f1 params to stdlib names already in rootenv; also bind vararg empty
    env.define('...', [])
    skipped=False
    pool=None
    try:
        for s in body:
            if (not skipped and nt(s)=='AstStatLocal' and len(s['vars'])==1
                    and s['vars'][0]['name']=='t'):
                skipped=True
                continue
            interp.exec_stat(s, env)
    except StopDecode as sd:
        pool=sd.val
        print('STOP at t[19] assignment (pool decoded)', file=sys.stderr)
    except LuaError as e:
        print('LuaError before decode:', e, file=sys.stderr); raise
    if pool is None:
        print('decode did not reach t[19]', file=sys.stderr); return
    print('=== pool type:', type(pool).__name__, file=sys.stderr)
    if isinstance(pool,str):
        open('/tmp/pool.bin','w',encoding='latin-1').write(pool)
        print('pool length:', len(pool))
        print('pool head:', repr(pool[:160]))
    elif isinstance(pool,LuaTable):
        n=pool.length(); print('pool table length:', n)
        for i in range(1,min(n,30)+1): print(i, repr(pool.get(i)))

if __name__=='__main__':
    main()
