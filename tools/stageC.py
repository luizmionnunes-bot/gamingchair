#!/usr/bin/env python3
"""Stage C: structure a flattened handler's state machine into native control flow.

Pipeline per handler:
  1. extract states + bodies (reuse sm.py)
  2. LOWER each state body into basic blocks with explicit terminators
     (Goto / Branch(cond,t,f) / Return(expr) / Break / Fallthrough)
     by stripping routing (loopvar assignments, num-temps feeding it, continue).
  3. STRUCTURE the basic-block CFG into native if/while (reducible relooper).
  4. EMIT Luau; VERIFY by symbolic-trace equivalence vs the lowered CFG.

This module first just prints the lowered CFG so we can validate the model.
"""
import json, sys
sys.path.insert(0, __file__.rsplit('/',1)[0])
import sm
nt = sm.nt
const_num = sm.const_num
local_name = sm.local_name

# ---------------- lowering ----------------
class Block:
    _n = 0
    def __init__(self, label):
        self.label = label          # state value (int) for entries, or ('x',id)
        self.effects = []           # list of source-text statements (verbatim)
        self.effect_locs = []       # parallel list of AST locations (coverage check)
        self.term = None            # terminator tuple
        self.term_loc = None        # location of the terminator statement, if any
    def __repr__(self):
        return f"B[{self.label}]"

def is_loopvar_assign(stmt, loopvar, nmap):
    """If stmt is `loopvar = <state-expr>` (maybe multi-assign), return successor spec:
       ('goto', N) | ('branch', condtext, Ntrue, Nfalse) | None."""
    if nt(stmt) != 'AstStatAssign': return None
    # find loopvar among targets
    idx = None
    for i, var in enumerate(stmt['vars']):
        if local_name(var) == loopvar: idx = i
    if idx is None: return None
    val = stmt['values'][idx] if idx < len(stmt['values']) else None
    if val is None: return None
    if nt(val) == 'AstExprIfElse':
        t = sm.resolve_states(val['trueExpr'], nmap)
        f = sm.resolve_states(val['falseExpr'], nmap)
        if len(t)==1 and len(f)==1:
            return ('branch_ternary', val['condition'], next(iter(t)), next(iter(f)))
    ss = sm.resolve_states(val, nmap)
    if len(ss) == 1:
        return ('goto', next(iter(ss)))
    return ('multi', ss)

def stmt_has_control(stmt, loopvar, nmap):
    """Does a statement (recursively) contain routing (loopvar assign / continue / break / return)?"""
    found = [False]
    def visit(n):
        if found[0]: return
        if isinstance(n, list):
            for x in n: visit(x)
            return
        if not isinstance(n, dict): return
        t = nt(n)
        if t in ('AstStatContinue','AstStatBreak','AstStatReturn'):
            found[0] = True; return
        if t == 'AstStatAssign':
            for var in n['vars']:
                if local_name(var) == loopvar: found[0] = True; return
        if t == 'AstExprFunction':   # don't descend into nested closures
            return
        for v in n.values():
            visit(v)
    visit(stmt)
    return found[0]

class Lowerer:
    def __init__(self, src, loopvar, nmap):
        self.src = src; self.loopvar = loopvar; self.nmap = nmap
        self.blocks = {}       # label -> Block
        self.xid = 0
        self.unmodeled = False  # set if routing appears in a construct we don't model
        self.exit_label = None  # if set, `break` and gotos to exit-states jump here
    def newx(self):
        self.xid += 1; return ('x', self.xid)
    def text(self, stmt): return self.src.slice(stmt['location'])

    def lower_state(self, N, stmts):
        b = Block(N); self.blocks[N] = b
        self.fill(b, stmts, 0)
        return b

    def fill(self, block, stmts, i, pending=None):
        """Fill `block` from stmts[i:]. `pending` = successor set by a prior
        `loopvar=` with no continue yet. Sets block.term."""
        while i < len(stmts):
            s = stmts[i]; t = nt(s)
            succ = is_loopvar_assign(s, self.loopvar, self.nmap)
            if succ is not None:
                if succ[0] == 'goto': pending = ('goto', succ[1])
                elif succ[0] == 'branch_ternary':
                    block.term = ('branch', succ[1], succ[2], succ[3]); return
                else:
                    self.unmodeled = True
                    block.term = ('raw', 'multi-successor '+str(succ)); return
                i += 1; continue
            if t == 'AstStatContinue':
                block.term = pending if pending else ('fallthrough',); return
            if t == 'AstStatBreak':
                block.term = ('goto', self.exit_label) if self.exit_label else ('break',); return
            if t == 'AstStatReturn':
                block.term = ('return', self.text(s)); block.term_loc=s['location']; return
            if t == 'AstStatIf' and stmt_has_control(s, self.loopvar, self.nmap):
                # routing branch: cond ? then : (else or fall-through-rest)
                cond = s['condition']
                thenb = self.newx(); self.blocks[thenb[1] if False else thenb] = Block(thenb)
                tb = self.blocks[thenb]
                self.fill(tb, sm.block_stmts(s['thenbody']), 0, pending)
                eb_stmts = sm.block_stmts(s['elsebody']) if s.get('elsebody') else stmts[i+1:]
                elseb = self.newx(); self.blocks[elseb] = Block(elseb)
                ebk = self.blocks[elseb]
                self.fill(ebk, eb_stmts, 0, pending)
                block.term = ('branch', cond, thenb, elseb); return
            # plain effect: if it hides routing (loopvar assign / continue / break /
            # return inside a loop/for or other unmodeled construct), flag it so the
            # handler is NOT nativised (safety: our model would be unsound).
            if stmt_has_control(s, self.loopvar, self.nmap):
                self.unmodeled = True
            block.effects.append(self.text(s)); block.effect_locs.append(s['location']); i += 1
        # end of stmts
        block.term = pending if pending else ('fallthrough',)

# ---------------- debug print ----------------
def dump_handler(root, src, N, func):
    info = sm.find_loop(func)
    if info is None: print(f"t[{N}]: no loop"); return
    lv = info['loopvar']; nmap = sm.numconst_map(func)
    states = sm.candidate_states(func, lv, nmap)
    if info['entry'] is not None: states.add(info['entry'])
    low = Lowerer(src, lv, nmap)
    for s in sorted(states):
        body = sm.find_body(info['inner'], lv, s)
        low.lower_state(s, body)
    print(f"\n===== t[{N}] loopvar={lv} entry={info['entry']} ({len(states)} states) =====")
    def tstr(term):
        k = term[0]
        if k=='goto': return f"goto {term[1]}"
        if k=='branch':
            c = term[1] if isinstance(term[1],str) else src.slice(term[1]['location'])
            return f"if ({c}) -> {term[2]} else {term[3]}"
        if k=='return': return term[1].replace('\n',' ')
        return k
    for lab, b in low.blocks.items():
        eff = ' ; '.join(e.replace('\n',' ')[:70] for e in b.effects)
        print(f"  {lab}: [{eff}]  => {tstr(b.term)}")

def main():
    ast_path, src_path = sys.argv[1], sys.argv[2]
    root = json.load(open(ast_path))['root']
    src = sm.Src(src_path)
    H = {N:f for N,f,l in sm.find_handlers(root)}
    targets = [int(x) for x in sys.argv[3:]] if len(sys.argv)>3 else sorted(H)
    for N in targets:
        dump_handler(root, src, N, H[N])

if __name__ == '__main__':
    main()
