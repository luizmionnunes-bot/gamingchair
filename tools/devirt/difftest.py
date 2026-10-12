#!/usr/bin/env python3
"""difftest.py — run the original VM and the devirtualized code in the same
logging environment and compare their global-access traces.

usage: difftest.py <workdir> <luau-bin-dir>
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lift, emit, opmap
T = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(os.path.dirname(T))
W, LB = sys.argv[1], sys.argv[2]

def lua_consts(C):
    tree = {}
    for k, v in C.items():
        path = [int(x) for x in re.findall(r'\[(\d+)\]', k)]
        if path[0] != 1: continue
        d = tree
        for p in path[:-1]:
            d = d.setdefault(p, {})
            if not isinstance(d, dict): break
        else:
            d[path[-1]] = v
    def ser(d):
        if isinstance(d, dict): return '{' + ', '.join('[%d] = %s' % (k, ser(v)) for k, v in sorted(d.items())) + '}'
        if isinstance(d, bool): return 'true' if d else 'false'
        return repr(d)
    return 'local t = {[1] = %s}\n' % ser(tree[1])

def build_devirt():
    L = lift.Lifter(os.path.join(R, 'gamingchairac.deob.lua'), W + '/deob.json', W + '/t1post.txt', W + '/proto.json')
    E = emit.Emitter(L)
    natives = open(W + '/natives.lua', encoding='utf-8', errors='surrogateescape').read()
    body = E.render_run(L.root)
    import model
    src = open(T + '/robloxmock.lua').read() + open(T + '/proxyenv.lua').read() + emit.RUNTIME + emit.vm_data(E, list(model.all_protos(L.root))) + lua_consts(L.C) + \
        'local __NATIVE = ' + natives + '\n' + 'local __ENV = PROXYENV\n' + \
        'local __main = (' + body + ')({})\n' + \
        'local ok, err = pcall(__main)\nprint("RESULT", ok, err)\nRUNMOCK()\nprint("END")\n'
    open(W + '/devirt_run.lua', 'w', encoding='utf-8', errors='surrogateescape').write(src)

def build_final():
    import final, model
    L = lift.Lifter(os.path.join(R, 'gamingchairac.deob.lua'), W + '/deob.json', W + '/t1post.txt', W + '/proto.json')
    G = final.Generator(L)
    natives = open(W + '/natives.lua', encoding='utf-8', errors='surrogateescape').read()
    body = G.render(L.root, '', {})
    pre = emit.RUNTIME + G.std_preamble() + emit.vm_data(G, list(model.all_protos(L.root))) + lua_consts(L.C) + 'local __NATIVE = ' + natives + '\n'
    open(W + '/devirt_final.lua', 'w', encoding='utf-8', errors='surrogateescape').write(pre + 'local __main = ' + body + '\nreturn __main\n')
    src = open(T + '/robloxmock.lua').read() + open(T + '/proxyenv.lua').read() + pre + \
        'local __main = ' + body + '\n' + 'setfenv(__main, PROXYENV)\n' + \
        'local ok, err = pcall(__main)\nprint("RESULT", ok, err)\nRUNMOCK()\nprint("END")\n'
    open(W + '/final_run.lua', 'w', encoding='utf-8', errors='surrogateescape').write(src)
    print('final stats', dict(G.stats), file=sys.stderr)

def build_orig():
    h = open(W + '/harness.lua', encoding='utf-8', errors='surrogateescape').read()
    pre = open(T + '/base.lua').read() + open(T + '/reconstructed.lua').read() + open(T + '/robloxmock.lua').read() + open(T + '/proxyenv.lua').read()
    open(W + '/pre_diff.lua', 'w').write(pre)
    subprocess.check_call([sys.executable, T + '/hook.py', W + '/harness.lua', W + '/h_diff.lua', W + '/pre_diff.lua'])
    s = open(W + '/h_diff.lua', encoding='utf-8', errors='surrogateescape').read()
    s = s.replace('t[122] = t[119](t[121], {}, getfenv_())', 't[122] = t[119](t[121], {}, PROXYENV)')
    s = s.replace('MODV = f1(', 'local okk, errr = pcall(function() MODV = f1(', 1)
    i = s.rindex('string.format, ...)')
    s = s[:i] + 'string.format) end) realprint("RESULT", okk, errr) RUNMOCK() realprint("END")' + s[i + len('string.format, ...)'):]
    open(W + '/h_diff.lua', 'w', encoding='utf-8', errors='surrogateescape').write(s)

def run(path):
    r = subprocess.run(['sh', '-c', 'ulimit -v 2000000; exec "$0" "$1"', LB + '/luau', path], capture_output=True, timeout=900)
    out = r.stdout.decode('latin1').splitlines()
    return [l for l in out if l.startswith(('G\t', 'RESULT', 'XERR', 'PERR', 'M\t', 'END'))]

mode = sys.argv[3] if len(sys.argv) > 3 else 'run'
build_orig()
if mode == 'final':
    build_final(); target = W + '/final_run.lua'
else:
    build_devirt(); target = W + '/devirt_run.lua'
a = run(W + '/h_diff.lua'); b = run(target)

def canon(tr):
    """global reads have no side effects in the real environment: within a run of
    consecutive reads (no call / write in between) their order is not significant"""
    out, run_ = [], []
    for l in tr:
        f = l.split('\t')
        if f[0] == 'G' and f[2] == 'get':
            run_.append('G\tget\t' + '\t'.join(f[3:])); continue
        if f[0] == 'M' and f[1] == 'get':
            run_.append(l); continue
        out += sorted(run_); run_ = []
        out.append(l if f[0] != 'G' else 'G\t' + '\t'.join(f[2:]))
    return out + sorted(run_)
a, b = canon(a), canon(b)
open(W + '/trace_orig.txt', 'w').write('\n'.join(a)); open(W + '/trace_devirt.txt', 'w').write('\n'.join(b))
n = 0
for x, y in zip(a, b):
    if x != y: break
    n += 1
print('orig events', len(a), 'devirt events', len(b), 'identical prefix', n)
if n < max(len(a), len(b)):
    print('first difference:\n  orig  :', a[n] if n < len(a) else '<end>', '\n  devirt:', b[n] if n < len(b) else '<end>')
print('orig  ', a[-1] if a else '')
print('devirt', b[-1] if b else '')
