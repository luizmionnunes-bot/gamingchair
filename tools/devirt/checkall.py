#!/usr/bin/env python3
"""checkall.py — run cfgcheck over every prototype.

usage: checkall.py <workdir> [trials]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.setrecursionlimit(1000000)
import cfgcheck, emit, lift, model, structure, webs

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W = sys.argv[1]
TRIALS = int(sys.argv[2]) if len(sys.argv) > 2 else 120

L = lift.Lifter(os.path.join(R, 'gamingchairac.deob.lua'),
                W + '/deob.json', W + '/t1post.txt', W + '/proto.json')
ok = bad = unstructured = 0
for p in model.all_protos(L.root):
    ir, errs = L.lift_proto(p)
    nodes = emit.apply_multret(emit.merge_chains(emit.to_nodes(ir), 1))
    params = [('R', i) for i in range(1, p.nparams + 1)]
    nodes = webs.apply(nodes, 1, params)
    nodes = structure.split_irreducible(nodes, 1)
    res, n, detail = cfgcheck.check(nodes, 1, structure.structure, TRIALS)
    if res is True:
        ok += 1
    elif res is None:
        unstructured += 1
        print('proto %-5s %s' % (p.id, detail))
    else:
        bad += 1
        print('proto %-5s FAIL %s' % (p.id, detail))
print('equivalent %d  divergent %d  unstructured %d  (%d trials each)'
      % (ok, bad, unstructured, TRIALS))
sys.exit(1 if bad or unstructured else 0)
