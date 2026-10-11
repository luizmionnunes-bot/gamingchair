#!/usr/bin/env python3
"""Produce a *runnable* copy of the deob script for the forced static-resolution
experiment: hoist `local vN` declarations out of `repeat..until` loops whose
`until` reads vN (Luau rejects `continue` jumping over such a local). Run:
  luau-compile in a loop, parse each error (line, var), hoist, recompile.
This copy is for emulation only (tools/mkharness.py builds the sandbox harness);
it is NOT the deliverable. See STATIC_RESOLUTION.md for the outcome."""
import subprocess, re, sys
path = sys.argv[1]; LUAU = sys.argv[2] if len(sys.argv)>2 else 'luau-compile'
for _ in range(500):
    r = subprocess.run([LUAU,'-O0',path], capture_output=True, text=True)
    m = re.findall(r'\((\d+),\d+\): CompileError: Local (v\d+) used in the repeat', r.stderr+r.stdout)
    if not m: break
    ul, var = int(m[0][0]), m[0][1]
    lines = open(path,encoding='utf-8',errors='surrogateescape').read().split('\n')
    ri = next(j for j in range(ul-1,-1,-1) if lines[j].strip()=='repeat')
    ind = lines[ri][:len(lines[ri])-len(lines[ri].lstrip())]
    for k in range(ri, ul):
        lines[k] = re.sub(r'^(\s*)local '+var+r'(\s*=)', r'\1'+var+r'\2', lines[k], count=1)
    lines.insert(ri, ind+'local '+var+' = nil')
    open(path,'w',encoding='utf-8',errors='surrogateescape').write('\n'.join(lines))
