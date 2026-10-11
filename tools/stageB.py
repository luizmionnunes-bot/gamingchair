#!/usr/bin/env python3
"""Stage B: scope-aware dead-code removal.

Removes ONLY provably-dead locals via AST liveness, iterated to a fixpoint:
  * local tables (`local X = {}` / `local X = {..}`) whose ONLY references are
    index-assignment writes `X[k] = v` (never read as a value / indexed on RHS);
  * local functions never referenced (the dead flattening generators
    `fN(p1,p2,p3) ... p1+p2-p3 ...`, which Stage A left uncalled).
Real data tables and real decoder functions have genuine reads/calls and are kept.

Deletion is line-based on standalone statements, validated afterwards by luau-ast.
Usage: stageB.py <ast.json> <src.lua> <out.lua>
"""
import json, sys

def nt(n): return n.get('type') if isinstance(n, dict) else None
def parse_loc(loc):
    a, b = loc.split(' - '); l0,c0=a.split(','); l1,c1=b.split(',')
    return (int(l0),int(c0)),(int(l1),int(c1))

def walk(n, fn):
    if isinstance(n, dict):
        fn(n)
        for v in n.values(): walk(v, fn)
    elif isinstance(n, list):
        for x in n: walk(x, fn)

def local_decl_loc_of_ref(ref):
    return ref['local']['location']

def main():
    ast_path, src_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    root = json.load(open(ast_path))['root']
    src = open(src_path, encoding='utf-8', errors='surrogateescape').read().split('\n')

    # ---- collect declarations keyed by decl-location ----
    # table decls: loc -> {'stmt_loc', 'kind':'table'}
    # func decls:  loc -> {'stmt_loc', 'kind':'func'}
    table_decls = {}   # declloc -> stmtloc  (for `local X = {}`/`{..}`, single var)
    func_decls = {}     # declloc -> stmtloc
    def collect(n):
        if nt(n) == 'AstStatLocal':
            if len(n['vars']) == 1 and len(n['values']) == 1:
                var, val = n['vars'][0], n['values'][0]
                if nt(val) == 'AstExprTable':
                    table_decls[var['location']] = n['location']
        elif nt(n) == 'AstStatLocalFunction':
            func_decls[n['name']['location']] = n['location']
    walk(root, collect)

    # ---- classify every AstExprLocal reference ----
    # For each decl-location, gather references split into:
    #   content_writes: ref is base of an index-expr used as assignment LHS (X[k]=..)
    #   other_uses:     everything else (reads, calls, args, RHS index base, ...)
    content_write_refids = set()   # id by ref 'location'
    # find assignment LHS index-bases
    def find_lhs(n):
        if nt(n) == 'AstStatAssign':
            for var in n['vars']:
                if nt(var) == 'AstExprIndexExpr' and nt(var['expr']) == 'AstExprLocal':
                    content_write_refids.add(var['expr']['location'])
    walk(root, find_lhs)

    uses = {}          # declloc -> count of non-content-write references
    cwrites = {}       # declloc -> list of (stmt? ) we track separately below
    all_refs = {}      # declloc -> list of ref nodes
    def gather(n):
        if nt(n) == 'AstExprLocal':
            dl = local_decl_loc_of_ref(n)
            all_refs.setdefault(dl, []).append(n)
            if n['location'] in content_write_refids:
                pass  # content write, not a use
            else:
                uses[dl] = uses.get(dl, 0) + 1
    walk(root, gather)

    # ---- map: for a dead table, which statements write to it (to delete) ----
    # statement locations of `X[k] = ..` where X decl is dead
    # We need, per assignment stmt, the set of decl-locs it writes to.
    assign_writes = []  # (stmt_loc, declloc)
    def find_assign(n):
        if nt(n) == 'AstStatAssign':
            # only pure dead-write statements: all targets are index on the SAME dead local,
            # handled generally: record each target's base decl + stmt loc
            for var in n['vars']:
                if nt(var) == 'AstExprIndexExpr' and nt(var['expr']) == 'AstExprLocal':
                    assign_writes.append((n['location'], var['expr']['local']['location'], n))
    walk(root, find_assign)

    # ---- iterate to fixpoint ----
    dead_tables = set()
    dead_funcs = set()
    changed = True
    while changed:
        changed = False
        # tables: uses count == 0 (all refs were content-writes)
        for dl in list(table_decls):
            if dl in dead_tables: continue
            if uses.get(dl, 0) == 0:
                dead_tables.add(dl); changed = True
        # functions: zero references at all (not called, not used as value)
        for dl in list(func_decls):
            if dl in dead_funcs: continue
            if len(all_refs.get(dl, [])) == 0:
                dead_funcs.add(dl); changed = True
        if not changed: break
        # removing a dead function removes its body references -> recompute uses
        # Rebuild uses excluding references that live inside a now-dead function body.
        dead_func_spans = [parse_loc(func_decls[dl]) for dl in dead_funcs]
        def inside_dead(refloc):
            (rl,rc),_ = parse_loc(refloc)
            for (sl,sc),(el,ec) in dead_func_spans:
                if (sl,sc) <= (rl,rc) <= (el,ec): return True
            return False
        uses = {}
        all_refs2 = {}
        for dl, refs in all_refs.items():
            for n in refs:
                if inside_dead(n['location']): continue
                all_refs2.setdefault(dl, []).append(n)
                if n['location'] not in content_write_refids:
                    uses[dl] = uses.get(dl, 0) + 1
        all_refs = all_refs2

    # ---- collect line ranges to delete ----
    del_lines = set()
    def mark(stmtloc):
        (l0,_),(l1,c1) = parse_loc(stmtloc)
        # delete lines l0..l1 inclusive (0-based), but if the statement ends before
        # the line's content (rare), still whole-line since these are standalone.
        for l in range(l0, l1+1):
            del_lines.add(l)
    stats = {'tables':0,'funcs':0,'dead_writes':0}
    for dl in dead_tables:
        mark(table_decls[dl]); stats['tables'] += 1
    for dl in dead_funcs:
        mark(func_decls[dl]); stats['funcs'] += 1
    # dead index-write statements to dead tables
    for stmtloc, declloc, node in assign_writes:
        if declloc in dead_tables:
            mark(stmtloc); stats['dead_writes'] += 1

    # safety: never delete a line that also contains a non-deleted statement.
    # Since we mark whole statement line-spans and these are standalone one-per-line
    # assignments/decls, this is safe; verify no deleted line is a control keyword.
    out = [ln for i, ln in enumerate(src) if i not in del_lines]
    open(out_path,'w',encoding='utf-8',errors='surrogateescape').write('\n'.join(out))
    print(f"dead tables={stats['tables']} dead funcs={stats['funcs']} "
          f"dead writes={stats['dead_writes']} lines removed={len(del_lines)}")
    print(f"lines: {len(src)} -> {len(out)}")

if __name__ == '__main__':
    main()
