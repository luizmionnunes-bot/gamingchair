#!/usr/bin/env python3
"""emitsrc.py — write the devirtualized program as readable, runnable Luau.

usage: emitsrc.py <workdir> <out.lua>

Same generator as the differential test's `final` mode (final.py), so what is
written here is the artifact that test compares against the running VM,
plus a header saying what it is.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.setrecursionlimit(1000000)
import emit, final, lift, model

T = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(os.path.dirname(T))

HEADER = """-- gamingchairac, devirtualized: the program that ran inside the
-- obfuscator's virtual machine, as Luau.
--
-- Recovered statically from the VM's bytecode by tools/devirt (see
-- DEVIRT_PLAN.md); regenerate with tools/devirt/run.sh followed by
-- tools/devirt/emitsrc.py. The bytecode listing it was lifted from is
-- gamingchairac.protos.txt.
--
-- Every one of the %d prototypes is structured control flow: no goto, no
-- label, no interpreter dispatch loop left anywhere in this file. The
-- structuring is checked per prototype against the original control-flow
-- graph (tools/devirt/checkall.py: 179 equivalent, 0 divergent), and the
-- whole file is checked against the running VM by trace equality in a
-- simulated Roblox environment (tools/devirt/difftest.py).
--
-- What cannot be recovered from bytecode: the author's local names and
-- comments. Locals are therefore numbered (v1, v2, ...) and parameters are
-- a1, a2, ...; everything else -- control flow, constants, globals, field
-- names, call structure -- is the original's.
--
-- The tables below the runtime helpers are data the recovered program reads
-- about itself: a few opcodes hand it its own register, code and constant
-- tables, so they have to stay.
--
-- Returns the program's main function; it is not called on load.

"""


def main():
    W, out = sys.argv[1], sys.argv[2]
    L = lift.Lifter(os.path.join(R, 'gamingchairac.deob.lua'), W + '/deob.json',
                    W + '/t1post.txt', W + '/proto.json')
    G = final.Generator(L)
    natives = open(W + '/natives.lua', encoding='utf-8',
                   errors='surrogateescape').read()
    body = G.render(L.root, '', {})
    protos = list(model.all_protos(L.root))
    src = (HEADER % len(protos) + emit.RUNTIME + G.std_preamble()
           + emit.vm_data(G, protos) + emit.lua_consts(L.C)
           + 'local __NATIVE = ' + natives + '\n'
           + 'local __main = ' + body + '\nreturn __main\n')
    open(out, 'w', encoding='utf-8', errors='surrogateescape').write(src)
    print('%s: %d lines, %d prototypes, stats %s'
          % (out, src.count('\n'), len(protos), dict(G.stats)))


if __name__ == '__main__':
    main()
