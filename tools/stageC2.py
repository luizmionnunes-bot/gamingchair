#!/usr/bin/env python3
"""Stage C transform: acyclic handlers -> native if/else, verified by symbolic traces.

For each handler:
  - lower to a basic-block CFG (stageC.Lowerer)
  - drop dead state-temps and collapse empty forwarders
  - if acyclic & every state body recovered: structure into an IR tree via
    post-dominators, VERIFY (enumerate condition assignments: CFG trace == IR trace),
    emit native Luau, and splice it into the handler.
  - otherwise leave the handler untouched (safe).
Writes the new file; caller validates with luau-ast.
"""
import json, sys, itertools, collections
sys.path.insert(0, __file__.rsplit('/',1)[0])
import sm, stageC
nt = sm.nt; const_num = sm.const_num; local_name = sm.local_name
EXIT = ('EXIT',)

# ---------- IR ----------
class Eff:  # verbatim effect statement(s)
    def __init__(self, text): self.text=text
class Ret:
    def __init__(self, text): self.text=text
class Brk: pass
class If:
    def __init__(self, cond, then, els): self.cond=cond; self.then=then; self.els=els
class Seq:
    def __init__(self, items): self.items=items

# ---------- build + clean CFG ----------
def is_state_temp_decl(src, stmt, nmap):
    """`local X = <num>` with the --[[s]] marker => dead routing temp."""
    if nt(stmt) != 'AstStatLocal': return False
    if len(stmt['vars'])!=1 or len(stmt['values'])!=1: return False
    if const_num(stmt['values'][0]) is None: return False
    txt = src.slice(stmt['location'])
    return '--[[s]]' in txt

class CFG:
    def __init__(self, N, info, low):
        self.N=N; self.entry=info['entry']; self.blocks=low.blocks
    def succs(self, lab):
        t=self.blocks[lab].term; k=t[0]
        if k=='goto': return [t[1]]
        if k=='branch': return [t[2],t[3]]
        return []

EXITLABEL=('exit',)

def while_exit_states(loop, lv, nmap):
    """For `while <cond> do`, the loopvar values that make <cond> FALSE (=> loop exits).
    Handles `lv ~= K` and conjunctions thereof. Returns set, or None if not modelable.
    `while true` -> empty set. repeat-loops -> None (not modeled here)."""
    if nt(loop)!='AstStatWhile': return None
    cond=loop['condition']
    # true
    if nt(cond)=='AstExprConstantBool' and cond.get('value') is True:
        return set()
    def collect(c):
        if nt(c)=='AstExprGroup': return collect(c['expr'])
        if nt(c)=='AstExprBinary' and c['op']=='And':
            l=collect(c['left']); r=collect(c['right'])
            return None if l is None or r is None else (l|r)
        cc=sm.loopvar_cmp(c, lv)
        if cc and cc[0]=='~=': return {cc[1]}
        return None
    return collect(cond)

def build_cfg(N, func, src):
    info=sm.find_loop(func)
    if info is None: return None
    lv=info['loopvar']; nmap=sm.numconst_map(func)
    states=sm.candidate_states(func,lv,nmap)
    if info['entry'] is not None: states.add(info['entry'])
    exitset=while_exit_states(info['loop'], lv, nmap)
    low=stageC.Lowerer(src,lv,nmap)
    if exitset is not None:
        low.exit_label=EXITLABEL
    empty=False
    for s in sorted(states):
        if exitset and s in exitset:   # pure exit sentinel: no in-loop body
            continue
        body=sm.find_body(info['inner'],lv,s)
        if not body: empty=True
        low.lower_state(s,body)
    # redirect gotos/branches to exit states -> EXITLABEL, and build the POST block
    if exitset is not None:
        for b in low.blocks.values():
            t=b.term
            if t[0]=='goto' and t[1] in exitset: b.term=('goto',EXITLABEL)
            elif t[0]=='branch':
                a=EXITLABEL if t[2] in exitset else t[2]
                c=EXITLABEL if t[3] in exitset else t[3]
                b.term=('branch',t[1],a,c)
        # POST block from statements after the loop
        body_stmts=func['body']['body']; ki=body_stmts.index(info['loop'])
        post=body_stmts[ki+1:]
        ex=stageC.Block(EXITLABEL); low.blocks[EXITLABEL]=ex
        low.fill(ex, post, 0)
        if ex.term==('fallthrough',): ex.term=('return','return')
    cfg=CFG(N,info,low)
    cfg.unmodeled=low.unmodeled
    cfg.entry=info['entry']
    if exitset and info['entry'] in exitset:
        cfg.entry=EXITLABEL
    cfg.uncovered=coverage_gap(info, lv, nmap, low)
    return cfg, lv, nmap, empty, info

def effect_locs_in_loop(info, lv, nmap):
    """Independently enumerate observable effect-statement locations inside the
    dispatch loop (descending through if/while/for blocks, NOT into closures),
    skipping routing (loopvar assigns, state-temp decls, continue/break)."""
    locs=set()
    def visit(n):
        if isinstance(n, list):
            for x in n: visit(x);
            return
        if not isinstance(n, dict): return
        t=nt(n)
        if t=='AstExprFunction': return  # don't descend into nested closures
        if t=='AstStatAssign':
            if any(local_name(v)==lv for v in n['vars']): return  # routing
            locs.add(n['location']); return
        if t=='AstStatLocal':
            # state-temp decl `local X=<num>` -> routing; else an effect
            if len(n['vars'])==1 and len(n['values'])==1 and const_num(n['values'][0]) is not None \
               and local_name(n['vars'][0]) in nmap:
                return
            locs.add(n['location']); return
        if t=='AstStatReturn':
            # bare `return` (no value) inside the dispatch is a routing guard
            # ("no valid state -> return nil"), captured by our fallthrough model.
            # Only value-returns are observable effects that must be covered.
            if n.get('list'): locs.add(n['location'])
            return
        if t=='AstStatExpr':
            locs.add(n['location']); return
        if t in ('AstStatContinue','AstStatBreak'): return
        # structural (if/while/for/repeat/block): descend
        for v in n.values(): visit(v)
    for s in info['inner']: visit(s)
    return locs

def coverage_gap(info, lv, nmap, low):
    allfx=effect_locs_in_loop(info, lv, nmap)
    covered=set()
    for b in low.blocks.values():
        covered|=set(b.effect_locs)
        if b.term_loc is not None: covered.add(b.term_loc)
    return allfx - covered

import re as _re
_TEMPDECL=_re.compile(r'^\s*local (v\d+)\s*=\s*-?\d+\s*$')
def _idents(text):
    return set(_re.findall(r'\bv\d+\b', text))

def drop_dead_temps(cfg):
    """Drop `local vN = <number>` effects whose vN is referenced nowhere else
    in the handler (dead routing temps). Pure-constant RHS => removal is safe.
    Iterated to a fixpoint."""
    changed=True
    while changed:
        changed=False
        # referenced names across all effects (non-decl uses), conds, returns
        used=set()
        decls={}  # name -> (block, index)
        for b in cfg.blocks.values():
            for i,e in enumerate(b.effects):
                m=_TEMPDECL.match(e)
                if m:
                    decls.setdefault(m.group(1), (b,i))
                    # the decl line's own name is not a "use"
                    continue
                used|=_idents(e)
            t=b.term
            if t[0]=='branch':
                c=t[1] if isinstance(t[1],str) else SRC.slice(t[1]['location'])
                used|=_idents(c)
            elif t[0]=='return':
                used|=_idents(t[1])
        # also: a temp decl may be used by ANOTHER temp decl's RHS (rare) -> count those
        for b in cfg.blocks.values():
            for e in b.effects:
                m=_TEMPDECL.match(e)
                if m:  # RHS is just a number -> no uses, skip
                    pass
        # drop unused temp decls
        for name,(b,i) in list(decls.items()):
            if name not in used:
                b.effects=[e for j,e in enumerate(b.effects)
                           if not (_TEMPDECL.match(e) and _TEMPDECL.match(e).group(1)==name)]
                changed=True
                break

def collapse_forwarders(cfg):
    """Redirect edges through blocks that have no effects and an unconditional goto."""
    def final(lab, seen):
        b=cfg.blocks.get(lab)
        if b is None: return lab
        if not b.effects and b.term[0]=='goto' and lab not in seen:
            seen.add(lab); return final(b.term[1], seen)
        return lab
    for lab,b in cfg.blocks.items():
        t=b.term
        if t[0]=='goto':
            b.term=('goto', final(t[1], {lab}))
        elif t[0]=='branch':
            b.term=('branch', t[1], final(t[2],{lab}), final(t[3],{lab}))

# ---------- dominators / post-dominators ----------
def postdom(cfg):
    # nodes reachable from entry
    order=[]; seen=set()
    def dfs(u):
        if u in seen or u==EXIT: return
        seen.add(u); order.append(u)
        for v in cfg.succs(u): dfs(v)
    dfs(cfg.entry)
    nodes=order[:]
    # successors incl EXIT for terminal
    def S(u):
        t=cfg.blocks[u].term; k=t[0]
        if k=='goto': return [t[1]]
        if k=='branch': return [t[2],t[3]]
        return [EXIT]   # return/break/fallthrough -> EXIT
    preds=collections.defaultdict(list)
    alln=set(nodes)|{EXIT}
    for u in nodes:
        for v in S(u): preds[v].append(u)
    # iterative post-dominators: reverse CFG dominators from EXIT
    rpo=list(reversed(order))  # approx reverse postorder of forward => for reverse graph
    idom={EXIT:EXIT}
    # process nodes in reverse postorder of the reverse graph ~ forward RPO reversed
    # Use simple iterative dataflow with full sets (CFGs are small).
    allset=set(nodes)|{EXIT}
    pd={u:set(allset) for u in nodes}; pd[EXIT]={EXIT}
    changed=True
    while changed:
        changed=False
        for u in order:
            new={u}
            ss=S(u)
            inter=None
            for v in ss:
                sv=pd.get(v, {v})
                inter = sv if inter is None else (inter & sv)
            if inter is None: inter=set()
            new=new|inter
            if new!=pd[u]:
                pd[u]=new; changed=True
    # immediate post-dominator = closest strict pd
    ipdom={}
    for u in nodes:
        cand=pd[u]-{u}
        # immediate post-dominator = the NEAREST strict post-dominator:
        # the candidate c that is post-dominated by every other candidate
        # (i.e. all other candidates d satisfy d in pd[c]).
        best=None
        for c in cand:
            if all((d in pd[c]) for d in cand if d!=c):
                best=c; break
        ipdom[u]=best if best is not None else EXIT
    return ipdom, allset

# ---------- structuring (acyclic) ----------
def structure(cfg):
    ipdom,_=postdom(cfg)
    def region(node, stop):
        items=[]; cur=node
        guard=0
        while cur is not None and cur!=stop and cur!=EXIT:
            guard+=1
            if guard>100000: raise RuntimeError("runaway")
            b=cfg.blocks[cur]
            for e in b.effects: items.append(Eff(e))
            t=b.term; k=t[0]
            if k=='return': items.append(Ret(t[1])); cur=None
            elif k=='break': items.append(Brk()); cur=None
            elif k=='fallthrough': items.append(Ret('return')); cur=None  # unknown-state -> return nil
            elif k=='goto': cur=t[1]
            elif k=='branch':
                j=ipdom[cur]
                cond=t[1] if isinstance(t[1],str) else cfg_condtext(cfg,t[1])
                tl=region(t[2], j); fl=region(t[3], j)
                items.append(If(cond, tl, fl)); cur=j
            else: raise RuntimeError("bad term "+str(t))
        return Seq(items)
    return region(cfg.entry, EXIT)

def cfg_condtext(cfg, condnode):
    return SRC.slice(condnode['location'])

# ---------- emit ----------
def emit(ir, indent=0):
    pad='    '*indent; out=[]
    if isinstance(ir, Seq):
        for it in ir.items: out+=emit(it, indent)
    elif isinstance(ir, Eff):
        out.append(_reindent(ir.text, pad))
    elif isinstance(ir, Ret):
        out.append(pad+ir.text.strip())
    elif isinstance(ir, Brk):
        out.append(pad+'break')
    elif isinstance(ir, If):
        thenlines=emit(Seq(ir.then) if isinstance(ir.then,list) else ir.then, indent+1)
        elselines=emit(Seq(ir.els) if isinstance(ir.els,list) else ir.els, indent+1)
        cond=ir.cond.strip()
        if elselines and not thenlines:
            out.append(f'{pad}if not ({cond}) then'); out+=elselines; out.append(pad+'end')
        elif thenlines and elselines:
            out.append(f'{pad}if {cond} then'); out+=thenlines
            out.append(pad+'else'); out+=elselines; out.append(pad+'end')
        elif thenlines:
            out.append(f'{pad}if {cond} then'); out+=thenlines; out.append(pad+'end')
        else:
            out.append(f'{pad}-- (empty branch on {cond})')
    return out

def _reindent(text, pad):
    lines=text.split('\n')
    if len(lines)==1: return pad+lines[0].strip()
    # keep relative indentation of multiline statements
    base=min((len(l)-len(l.lstrip()) for l in lines if l.strip()), default=0)
    return '\n'.join(pad+l[base:] if l.strip() else '' for l in lines)

# ---------- verify (symbolic traces) ----------
def cfg_traces(cfg, assign):
    cur=cfg.entry; ev=[]; guard=0
    while cur is not None and cur!=EXIT:
        guard+=1
        if guard>100000: return None
        b=cfg.blocks[cur]
        for e in b.effects: ev.append(('E', _norm(e)))
        t=b.term; k=t[0]
        if k=='goto': cur=t[1]
        elif k in ('return',): ev.append(('T',_norm(t[1]))); cur=None
        elif k=='break': ev.append(('T','<break>')); cur=None
        elif k=='fallthrough': ev.append(('T','return')); cur=None
        elif k=='branch':
            cond=t[1] if isinstance(t[1],str) else cfg_condtext(cfg,t[1])
            d=assign[_norm(cond)]
            ev.append(('B',_norm(cond),d))
            cur=t[2] if d else t[3]
    return tuple(ev)

def ir_traces(ir, assign):
    ev=[]
    def go(x):
        if isinstance(x,Seq):
            for it in x.items: go(it)
        elif isinstance(x,list):
            for it in x: go(it)
        elif isinstance(x,Eff): ev.append(('E',_norm(x.text)))
        elif isinstance(x,Ret): ev.append(('T',_norm(x.text)))
        elif isinstance(x,Brk): ev.append(('T','<break>'))
        elif isinstance(x,If):
            d=assign[_norm(x.cond)]
            ev.append(('B',_norm(x.cond),d))
            go(x.then if d else x.els)
    go(ir)
    return tuple(ev)

def _norm(s): return ' '.join(s.split())

def all_conditions(cfg):
    conds=set()
    for b in cfg.blocks.values():
        if b.term[0]=='branch':
            c=b.term[1] if isinstance(b.term[1],str) else cfg_condtext(cfg,b.term[1])
            conds.add(_norm(c))
    return sorted(conds)

def verify(cfg, ir):
    conds=all_conditions(cfg)
    if len(conds)<=16:
        assigns=[dict(zip(conds,bits)) for bits in itertools.product([False,True],repeat=len(conds))]
    else:
        import random; random.seed(1)
        assigns=[{c:random.random()<0.5 for c in conds} for _ in range(4000)]
    for a in assigns:
        if cfg_traces(cfg,a)!=ir_traces(ir,a): return False
    return True

def find_loop_stmt(func):
    for s in func['body']['body']:
        if nt(s) in ('AstStatWhile','AstStatRepeat'): return s
    return None

def loop_is_last(func, loopstmt):
    body=func['body']['body']
    return body and body[-1] is loopstmt

def brk_to_return(ir):
    """Replace Brk (exit dispatch loop) with `return` — valid only when the loop
    is the last statement of the handler (break => fall off the end => return nil)."""
    def conv(x):
        if isinstance(x, Brk): return Ret('return')
        if isinstance(x, Seq): x.items=[conv(i) for i in x.items]; return x
        if isinstance(x, If):
            x.then=conv(x.then) if not isinstance(x.then,list) else [conv(i) for i in x.then]
            x.els =conv(x.els)  if not isinstance(x.els,list)  else [conv(i) for i in x.els]
            return x
        return x
    return conv(ir)

def has_break(ir):
    found=[False]
    def go(x):
        if isinstance(x,Brk): found[0]=True
        elif isinstance(x,Seq):
            for i in x.items: go(i)
        elif isinstance(x,If):
            for s in ((x.then if isinstance(x.then,list) else [x.then])+
                      (x.els if isinstance(x.els,list) else [x.els])): go(s)
    go(ir); return found[0]

def dead_local_cleanup(lines):
    """Whole-file: drop `local vN = <number|identifier>` whose vN is unreferenced
    elsewhere (removes now-dead state-entry temps left after splicing). Safe:
    pure-constant / pure-copy RHS, unreferenced target."""
    decl=_re.compile(r'^(\s*)local (v\d+)\s*=\s*(-?\d+|v\d+)\s*(--\[\[s\]\])?\s*$')
    changed=True
    while changed:
        changed=False
        text='\n'.join(lines)
        for i,ln in enumerate(lines):
            m=decl.match(ln)
            if not m: continue
            name=m.group(2)
            # count references to `name` in the whole file as a word
            cnt=len(_re.findall(r'\b'+name+r'\b', text))
            # one occurrence is this decl's own LHS
            if cnt<=1:
                lines[i]=None; changed=True
        if changed:
            lines=[l for l in lines if l is not None]
    return lines

SRC=None
def main():
    global SRC
    ast_path, src_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    only=[int(x) for x in sys.argv[4:]] if len(sys.argv)>4 else None
    root=json.load(open(ast_path))['root']
    SRC=sm.Src(src_path)
    lines=open(src_path,encoding='utf-8',errors='surrogateescape').read().split('\n')
    H={N:(f,l) for N,f,l in sm.find_handlers(root)}
    results={}
    splices=[]   # (start_line0, end_line0, native_lines)
    for N in sorted(H):
        func,loc=H[N]
        if only and N not in only:
            continue
        try:
            built=build_cfg(N,func,SRC)
        except Exception as ex:
            results[N]=('err-build',str(ex)); continue
        if built is None:
            results[N]=('no-loop',''); continue
        cfg,lv,nmap,empty,info=built
        if empty:
            results[N]=('empty-body',''); continue
        if cfg.unmodeled:
            results[N]=('unmodeled-control',''); continue
        if cfg.uncovered:
            results[N]=('incomplete-extract', f'{len(cfg.uncovered)} stmts'); continue
        drop_dead_temps(cfg)
        collapse_forwarders(cfg)
        if _cyclic(cfg):
            results[N]=('cyclic',''); continue
        try:
            ir=structure(cfg)
            ok=verify(cfg,ir)
        except Exception as ex:
            results[N]=('err-struct',str(ex)); continue
        if not ok:
            results[N]=('verify-fail',''); continue
        # splice: replace the dispatch loop statement with native code
        loopstmt=find_loop_stmt(func)
        if has_break(ir):
            if not loop_is_last(func, loopstmt):
                results[N]=('post-loop-break',''); continue
            ir=brk_to_return(ir)
        (l0,c0),(l1,c1)=sm.parse_loc(loopstmt['location'])
        # swallow immediately-preceding loopvar-init decls:
        #   `local <tmp> = <entry number>`  and  `local <loopvar> = <tmp>`
        body=func['body']['body']
        ki=body.index(loopstmt)
        j=ki-1
        while j>=0:
            s=body[j]
            if nt(s)=='AstStatLocal' and len(s['vars'])==1 and len(s['values'])==1:
                var,val=s['vars'][0],s['values'][0]
                if const_num(val) is not None or local_name(val) in nmap or local_name(val)==lv:
                    (sl,sc),_=sm.parse_loc(s['location']); l0=sl; j-=1; continue
            break
        pad=' '*c0
        native=[(pad+ln if ln.strip() else '') for ln in emit(ir,0)]
        native=[f"{pad}-- [state machine structured to native control flow]"]+native
        splices.append((l0,l1,native))
        results[N]=('native','')
    # apply splices descending
    for l0,l1,native in sorted(splices,key=lambda x:-x[0]):
        lines[l0:l1+1]=native
    lines=dead_local_cleanup(lines)
    open(out_path,'w',encoding='utf-8',errors='surrogateescape').write('\n'.join(lines))
    for N in sorted(results):
        print(f"t[{N}]: {results[N][0]} {results[N][1][:60]}")
    import collections as c
    print("summary:", dict(c.Counter(v[0] for v in results.values())))
    print(f"native handlers spliced: {len(splices)}")

def _cyclic(cfg):
    WHITE,GRAY,BLACK=0,1,2
    color=collections.defaultdict(int)
    cyc=[False]
    def dfs(u):
        color[u]=GRAY
        for v in cfg.succs(u):
            if color[v]==GRAY: cyc[0]=True
            elif color[v]==WHITE: dfs(v)
        color[u]=BLACK
    if cfg.entry in cfg.blocks: dfs(cfg.entry)
    return cyc[0]

if __name__=='__main__':
    main()
