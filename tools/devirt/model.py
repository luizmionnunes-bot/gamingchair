"""model.py — decode the deserialized proto tree (harness dump) into Python.

Mirrors the runtime pieces that feed the executor:
  t[100]  layout accessor (section layouts selected by per-proto modes)
  t[101]  constant decoder (string / int / int64 / double / bool)
  t[116]  proto wrapper (reconstructed; see RECONSTRUCTED.md)

Instruction record field keys (t[48..55]) and the executor's field map
(proto[4]) are read from the dump, so nothing here is hard-coded per build
except the canonical kind numbers documented in FORMAT.md.
"""
import math, struct, sys
from ptree import load, LT, Fn
import vmcrypto

FK = dict(op=5, A=1, B=11, C=2, D=10, F1=9, F2=14, F3=13)   # t[48..55]

class Enc:
    """constant whose payload is encrypted with a key we could not derive statically"""
    def __init__(self, kind, raw, extra): self.kind, self.raw, self.extra = kind, raw, extra
    def __repr__(self): return '<enc %r key=%r>' % (self.raw, self.extra)

class Proto:
    _n = 0
    def __init__(self):
        Proto._n += 1
        self.id = Proto._n
        self.consts = {}; self.code = {}; self.protos = {}; self.upvals = {}
        self.idx = {}; self.nparams = 0; self.maxstack = 0; self.extra = None
        self.lineinfo = []; self.sec3 = []
        self.parent = None; self.name = None

def arr(x):
    return x.arr() if isinstance(x, LT) else x

def access(L, mode, g, is_instr):
    """port of t[100](layout, mode, globalIndex, isInstr)"""
    if L is None: return None
    base = L.get(1) or 0
    i = g - base
    if i < 1: return None
    data = L.get(2)
    if mode == 1:
        e = (data or {}).get(i)
        return None if e is None else e.get(1)
    if mode == 2:
        size = L.get(3) or 1
        n = L.get(4) or 0
        if n != 0 and n < i: return None
        grp = (data or {}).get((i - 1) // size + 1)
        return None if grp is None else grp.get((i - 1) % size + 1)
    if mode == 3:
        # closure layout: dump stores the closure result under key 'fnres'
        lst = L.get('fnres')
        return None if lst is None else lst.get(i)
    if mode == 4 and is_instr:
        cols = data or {}
        c = [cols.get(k) or {} for k in range(1, 9)]
        if i > len(c[0]): return None
        rec = LT()
        for key, col in zip((5, 1, 11, 2, 10, 9, 14, 13), c):
            if col.get(i) is not None: rec[key] = col[i]
        return rec
    return (data or {}).get(i)

def zz(u):
    f = u // 2
    return f if u % 2 == 0 else -f - 1

def leb(bs):
    s, m = 0, 1
    for b in bs:
        s += (b - 128 if b > 127 else b) * m
        if b < 128: break
        m *= 128
    return s

def decode_const(raw, g):
    """port of t[101](raw, p2, key=raw[4])"""
    if raw is None: return None
    kind, aux, data, extra = raw.get(1), raw.get(2), arr(raw.get(3)) or [], raw.get(4) or 0
    if extra != 0:
        return Enc(kind, bytes(data), arr(extra))
    if kind == 0:
        return bytes(data)
    if kind == 1:
        return zz(leb(data)) if aux == 1 else struct.unpack('<q', bytes(data[:8] + [0] * (8 - len(data))))[0]
    if kind == 2:
        return leb(data) if aux == 1 else struct.unpack('<Q', bytes(data[:8] + [0] * (8 - len(data))))[0]
    if kind in (3, 4):
        if kind == 4 and aux == 1: return zz(leb(data))
        return struct.unpack('<d', bytes(data[:8] + [0] * (8 - len(data))))[0]
    if kind == 5:
        return (data[0] if data else 0) == 1
    return None

def build(p, parent=None):
    P = p[123][31]
    H, keys, S, fmap = P[1], arr(P[2]), P[3], P[4]
    secinfo = arr(H[keys[5]]); modes = arr(H[keys[2]])
    pr = Proto(); pr.parent = parent
    pr.fmap = dict(fmap)
    pr.misc = arr(H[keys[6]])
    for i, si in enumerate(secinfo, 1):
        si = arr(si); ty, base, n = si[0], si[1], si[2]
        L = S.get(i)
        if ty == 0:
            for j in range(1, n + 1):
                pr.consts[base + j] = decode_const(access(L, modes[0], base + j, False), base + j)
        elif ty == 1:
            for j in range(1, n + 1):
                pr.code[base + j] = access(L, modes[1], base + j, True)
        elif ty == 7:
            for j in range(1, n + 1):
                sp = access(L, modes[2], base + j, False)
                pr.protos[base + j] = build(sp, pr) if sp is not None else None
        elif ty == 4:
            for j in range(1, n + 1): pr.upvals[base + j] = arr((L[2] or {}).get(j))
        elif ty == 5:
            for j in range(1, n + 1): pr.idx[base + j] = arr((L[2] or {}).get(j))
        elif ty == 2:
            pr.lineinfo = [arr(x) for x in arr(L[2])]
        elif ty == 3:
            pr.sec3 = [arr(x) for x in arr(L[2])]
        elif ty == 6:
            if modes[3] == 4: kind, val = L[1][1], L[2][1]
            else: kind, val = L[1], L[2]
            if kind == 0: pr.nparams = val
            elif kind == 2: pr.maxstack = val
            else: pr.extra = val
    return pr

def load_model(path):
    root = load(path)
    return build(root)

def all_protos(pr):
    yield pr
    for k in sorted(pr.protos):
        if pr.protos[k] is not None: yield from all_protos(pr.protos[k])

if __name__ == '__main__':
    m = load_model(sys.argv[1])
    ps = list(all_protos(m))
    print('protos', len(ps), 'instrs', sum(len(p.code) for p in ps), 'consts', sum(len(p.consts) for p in ps))
    enc = [(p.id, k, c) for p in ps for k, c in p.consts.items() if isinstance(c, Enc)]
    print('encrypted consts', len(enc))
