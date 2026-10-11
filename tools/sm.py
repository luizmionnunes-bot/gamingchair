#!/usr/bin/env python3
"""State-machine extraction engine for the flattened Luau handlers.

Reads a luau-ast JSON + the source file, locates every `t[N] = function`
handler, finds its dispatch loop, and recovers the state graph:
  state value -> (body statements, outgoing transitions).

Transition-graph recovery is by *simulation*: for each candidate state value N
we walk the dispatch decision-tree evaluating only loopvar comparisons, which
deterministically leads to exactly one state body.
"""
import json, sys, re

# ---------- source slicing (luau locations are 0-based line, 0-based col) ----------
class Src:
    def __init__(self, path):
        self.lines = open(path, encoding='utf-8', errors='surrogateescape').read().split('\n')
    def slice(self, loc):
        (l0, c0), (l1, c1) = parse_loc(loc)
        if l0 == l1:
            return self.lines[l0][c0:c1]
        out = [self.lines[l0][c0:]]
        out += self.lines[l0+1:l1]
        out.append(self.lines[l1][:c1])
        return '\n'.join(out)

def parse_loc(loc):
    a, b = loc.split(' - ')
    l0, c0 = a.split(','); l1, c1 = b.split(',')
    return (int(l0), int(c0)), (int(l1), int(c1))

# ---------- AST helpers ----------
def nt(n): return n.get('type') if isinstance(n, dict) else None

def local_name(n):
    """name of an AstExprLocal / AstLocal."""
    if nt(n) == 'AstExprLocal':
        return n['local']['name']
    if nt(n) == 'AstLocal':
        return n['name']
    return None

def const_num(n):
    if nt(n) == 'AstExprConstantNumber':
        return n['value']
    # unary minus on a constant
    if nt(n) == 'AstExprUnary' and n.get('op') == 'Minus' and nt(n.get('expr')) == 'AstExprConstantNumber':
        return -n['expr']['value']
    return None

def block_stmts(b):
    if b is None: return []
    if nt(b) == 'AstStatBlock': return b['body']
    return [b]

def walk(n, fn):
    if isinstance(n, dict):
        fn(n)
        for v in n.values(): walk(v, fn)
    elif isinstance(n, list):
        for x in n: walk(x, fn)

# ---------- handler discovery ----------
def find_handlers(root):
    """Return list of (N, funcnode, assignloc) for every `t[N] = function`."""
    out = []
    def visit(n):
        if nt(n) == 'AstStatAssign':
            vars_, vals = n['vars'], n['values']
            for v, val in zip(vars_, vals):
                if (nt(v) == 'AstExprIndexExpr' and nt(v['expr']) == 'AstExprLocal'
                        and local_name(v['expr']) == 't'
                        and const_num(v['index']) is not None
                        and nt(val) == 'AstExprFunction'):
                    out.append((const_num(v['index']), val, n['location']))
    walk(root, visit)
    return out

# ---------- dispatch-loop / loopvar detection ----------
CMP = {'CompareEq':'==','CompareNe':'~=','CompareLt':'<','CompareLe':'<=',
       'CompareGt':'>','CompareGe':'>='}

def loopvar_cmp(cond, loopvar):
    """If cond is `loopvar <cmp> const` (either orientation), return (op,const).
    Returns None if cond is not a pure loopvar comparison."""
    if nt(cond) != 'AstExprBinary' or cond['op'] not in CMP:
        return None
    op = CMP[cond['op']]
    L, R = cond['left'], cond['right']
    if local_name(L) == loopvar and const_num(R) is not None:
        return (op, const_num(R))
    if local_name(R) == loopvar and const_num(L) is not None:
        # flip orientation
        flip = {'<':'>','<=':'>=','>':'<','>=':'<=','==':'==','~=':'~='}
        return (flip[op], const_num(L))
    return None

def eval_cmp(op, k, N):
    return {'==':N==k,'~=':N!=k,'<':N<k,'<=':N<=k,'>':N>k,'>=':N>=k}[op]

def cond_pure_dispatch(cond, loopvar):
    """Evaluate a (possibly and/or/not) boolean of loopvar comparisons.
    Return a callable N->bool if PURE (only loopvar cmps + and/or/not),
    else None (means: body condition, not dispatch)."""
    t = nt(cond)
    if t == 'AstExprGroup':
        return cond_pure_dispatch(cond['expr'], loopvar)
    if t == 'AstExprBinary' and cond['op'] in ('And','Or'):
        l = cond_pure_dispatch(cond['left'], loopvar)
        r = cond_pure_dispatch(cond['right'], loopvar)
        if l is None or r is None: return None
        if cond['op'] == 'And': return lambda N: l(N) and r(N)
        return lambda N: l(N) or r(N)
    if t == 'AstExprUnary' and cond['op'] == 'Not':
        o = cond_pure_dispatch(cond['expr'], loopvar)
        return None if o is None else (lambda N: not o(N))
    c = loopvar_cmp(cond, loopvar)
    if c is not None:
        op, k = c
        return lambda N: eval_cmp(op, k, N)
    return None

def is_exit(stmts):
    """True if the block is purely an exit (return/break) terminator path."""
    return len(stmts) >= 1 and nt(stmts[-1]) in ('AstStatReturn','AstStatBreak')

def find_loop(func):
    """Find dispatch loop node + loopvar + entry value within a handler func body."""
    body = func['body']['body']
    # loopvar: the local initialised with a number and later used in while/repeat dispatch.
    # Collect `local X = <num>` then `while true`/`repeat`. Prefer the var compared inside.
    loop = None
    for s in body:
        if nt(s) == 'AstStatWhile':
            loop = s; break
        if nt(s) == 'AstStatRepeat':
            loop = s; break
    if loop is None:
        return None
    inner = loop['body']['body'] if nt(loop['body'])=='AstStatBlock' else [loop['body']]
    # find loopvar: first AstStatIf whose condition is a comparison with a local vs const
    loopvar = None
    def first_cmpvar(stmts):
        for s in stmts:
            if nt(s) == 'AstStatIf':
                cond = s['condition']
                for side in ('left','right'):
                    pass
                # try both locals appearing
                if nt(cond)=='AstExprBinary' and cond['op'] in CMP:
                    for side in (cond['left'],cond['right']):
                        if local_name(side) and const_num({'AstExprConstantNumber':cond['left'] if side is cond['right'] else cond['right']}.get('x',cond['right'] if side is cond['left'] else cond['left'])) is not None:
                            return local_name(side)
                # fallback: any local on either side
                if nt(cond)=='AstExprBinary' and cond['op'] in CMP:
                    for side in (cond['left'],cond['right']):
                        if local_name(side): return local_name(side)
        return None
    loopvar = first_cmpvar(inner)
    # entry value: last `local loopvar = N` or `local X = N` before loop, chase copies
    entry = None
    numvars = {}
    for s in body:
        if s is loop: break
        if nt(s) == 'AstStatLocal':
            for var, val in zip(s['vars'], s['values']):
                nm = local_name(var); cn = const_num(val)
                if cn is not None: numvars[nm] = cn
                elif local_name(val) in numvars: numvars[nm] = numvars[local_name(val)]
    if loopvar in numvars: entry = numvars[loopvar]
    return {'loop':loop,'loopvar':loopvar,'inner':inner,'entry':entry}

# ---------- state body recovery by simulation ----------
def find_body(stmts, loopvar, N):
    """Walk a dispatch block for loopvar==N; return the list of body statements."""
    for i, s in enumerate(stmts):
        if nt(s) == 'AstStatIf':
            pred = cond_pure_dispatch(s['condition'], loopvar)
            if pred is None:
                # body condition -> state body starts here
                return stmts[i:]
            val = pred(N)
            # equality arrival?
            c = loopvar_cmp(s['condition'], loopvar)
            if val:
                if c is not None and c[0] == '==':
                    return block_stmts(s['thenbody'])
                return find_body(block_stmts(s['thenbody']), loopvar, N)
            else:
                eb = s.get('elsebody')
                if eb is not None and nt(eb) in ('AstStatBlock','AstStatIf'):
                    return find_body(block_stmts(eb), loopvar, N)
                # no else: guard; fall through to rest of block
                continue
        else:
            # first non-dispatch statement => body
            return stmts[i:]
    return []

def numconst_map(func):
    """name -> constant for `local X = <num>` decls (drop names assigned >1 distinct const)."""
    m = {}
    bad = set()
    def visit(n):
        if nt(n) == 'AstStatLocal':
            for var, val in zip(n['vars'], n['values']):
                nm = local_name(var); cn = const_num(val)
                if nm is None: continue
                if cn is not None:
                    if nm in m and m[nm] != cn: bad.add(nm)
                    m.setdefault(nm, cn)
    walk(func['body'], visit)
    for b in bad: m.pop(b, None)
    return m

def resolve_states(expr, nmap):
    """Possible constant state values an rhs expr can take (const / num-temp / if-else)."""
    cn = const_num(expr)
    if cn is not None: return {cn}
    nm = local_name(expr)
    if nm in nmap: return {nmap[nm]}
    if nt(expr) == 'AstExprIfElse':
        return resolve_states(expr['trueExpr'], nmap) | resolve_states(expr['falseExpr'], nmap)
    if nt(expr) == 'AstExprGroup':
        return resolve_states(expr['expr'], nmap)
    return set()

def transitions_in(stmts, loopvar, nmap):
    """Collect state targets assigned to loopvar inside a body (any depth)."""
    outs = []
    def visit(n):
        if nt(n) == 'AstStatAssign':
            for var, val in zip(n['vars'], n['values']):
                if local_name(var) == loopvar:
                    outs.extend(sorted(resolve_states(val, nmap)))
    for s in stmts: walk(s, visit)
    return outs

def candidate_states(func, loopvar, nmap):
    vals = set()
    def visit(n):
        if nt(n) == 'AstStatAssign':
            for var, val in zip(n['vars'], n['values']):
                if local_name(var) == loopvar:
                    vals.update(resolve_states(val, nmap))
    walk(func['body'], visit)
    return vals

def analyze_handler(N, func):
    info = find_loop(func)
    if info is None:
        return {'N':N,'states':0,'note':'no dispatch loop (stub/empty)'}
    lv = info['loopvar']
    nmap = numconst_map(func)
    states = candidate_states(func, lv, nmap)
    if info['entry'] is not None: states.add(info['entry'])
    graph = {}
    bad = []
    for s in sorted(states):
        body = find_body(info['inner'], lv, s)
        outs = transitions_in(body, lv, nmap)
        graph[s] = outs
        if not body: bad.append(s)
    return {'N':N,'loopvar':lv,'entry':info['entry'],'states':len(states),
            'graph':graph,'empty_bodies':bad,'looptype':nt(info['loop'])}

def main():
    ast_path, src_path = sys.argv[1], sys.argv[2]
    root = json.load(open(ast_path))['root']
    handlers = find_handlers(root)
    print(f"handlers found: {len(handlers)}")
    total_states = 0
    probs = []
    for N, func, loc in sorted(handlers):
        r = analyze_handler(N, func)
        total_states += r['states']
        flag = ''
        if r.get('empty_bodies'): flag = f" !! empty-body states: {r['empty_bodies'][:8]}"
        if 'note' in r: flag = ' -- '+r['note']
        print(f"  t[{N:>3}] states={r['states']:>4} loopvar={r.get('loopvar')} "
              f"entry={r.get('entry')} loop={r.get('looptype','-')}{flag}")
        if r.get('empty_bodies') or 'note' in r:
            probs.append(N)
    print(f"total states across handlers: {total_states}")
    print(f"handlers needing attention: {probs}")

if __name__ == '__main__':
    main()
