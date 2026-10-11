#!/usr/bin/env python3
"""Stage R: rename f1's constant-pool parameters to readable stdlib names.

f1 receives the obfuscator's constant pool as positional parameters; the final
`return f1(error, next, string.match, ... , string.format, ...)` call fixes what
each parameter actually is. We alpha-rename every reference bound to one of those
33 parameters (disambiguated from shadowing inner `p1..pN` by declaration
location) to a descriptive name. Pure rename => behaviour preserved.

Usage: stageR.py <ast.json> <src.lua> <out.lua>
"""
import json, sys

# positional map (1-based) confirmed from the tail call `return f1(...)`
NAMES = {
    1:'error_', 2:'next_', 3:'str_match', 4:'tonumber_', 5:'str_gsub',
    6:'str_sub', 7:'tbl_insert', 8:'str_char', 9:'str_byte', 10:'co_yield',
    11:'co_wrap', 12:'str_rep', 13:'tbl_concat', 14:'math_floor', 15:'select_',
    16:'getfenv_', 17:'setmetatable_', 18:'next_b', 19:'tbl_unpack', 20:'const_nil',
    21:'math_min', 22:'decode_p22', 23:'str_len', 24:'tbl_remove', 25:'tbl_sort',
    26:'str_unpack', 27:'str_gmatch', 28:'str_find', 29:'str_reverse', 30:'tostring_',
    31:'math_abs', 32:'rawget_', 33:'str_format',
}

def nt(n): return n.get('type') if isinstance(n, dict) else None
def ploc(loc):
    a,b=loc.split(' - '); l0,c0=a.split(','); l1,c1=b.split(',')
    return (int(l0),int(c0)),(int(l1),int(c1))

def walk(n, fn):
    if isinstance(n, dict):
        fn(n)
        for v in n.values(): walk(v, fn)
    elif isinstance(n, list):
        for x in n: walk(x, fn)

def main():
    ast_path, src_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    root = json.load(open(ast_path))['root']
    lines = open(src_path, encoding='utf-8', errors='surrogateescape').read().split('\n')

    f1 = None
    for s in root['body']:
        if nt(s) == 'AstStatLocalFunction' and s['name']['name'] == 'f1':
            f1 = s['func']; break
    assert f1 is not None, "f1 not found"
    args = f1['args']
    assert len(args) == 33, f"expected 33 params, got {len(args)}"
    # decl-location -> newname
    declloc2name = {}
    param_decl_locs = []
    for i, a in enumerate(args, 1):
        declloc2name[a['location']] = NAMES[i]
        param_decl_locs.append((a['location'], NAMES[i], a['name']))

    # collect edit sites: (loc, oldname, newname)
    edits = []
    # 1) the parameter declarations themselves
    for loc, newname, old in param_decl_locs:
        edits.append((loc, old, newname))
    # 2) every reference bound to a param decl-location
    def visit(n):
        if nt(n) == 'AstExprLocal':
            dl = n['local']['location']
            if dl in declloc2name:
                edits.append((n['location'], n['local']['name'], declloc2name[dl]))
    walk(root, visit)

    # apply edits per line, descending column (identifiers never span lines)
    by_line = {}
    for loc, old, new in edits:
        (l0,c0),(l1,c1) = ploc(loc)
        assert l0 == l1, f"identifier spans lines? {loc}"
        by_line.setdefault(l0, []).append((c0,c1,old,new))
    nrefs = 0
    for l, lst in by_line.items():
        line = lines[l]
        for c0,c1,old,new in sorted(lst, key=lambda x:-x[0]):
            cur = line[c0:c1]
            assert cur == old, f"line {l+1} col {c0}: expected {old!r} got {cur!r}"
            line = line[:c0] + new + line[c1:]
            nrefs += 1
        lines[l] = line

    open(out_path,'w',encoding='utf-8',errors='surrogateescape').write('\n'.join(lines))
    print(f"renamed {len(param_decl_locs)} params + {nrefs-len(param_decl_locs)} references "
          f"= {nrefs} sites across {len(by_line)} lines")

if __name__ == '__main__':
    main()
