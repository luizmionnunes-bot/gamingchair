"""Load the proto-tree dump produced by the harness (JSON of Lua tables)."""
import json

class LT(dict):
    """Lua table: dict with int/str keys; .id for identity."""
    __slots__ = ('id',)
    def __hash__(self): return id(self)
    def __eq__(self, o): return self is o
    def arr(self):
        n = 0
        while (n + 1) in self: n += 1
        return [self[i] for i in range(1, n + 1)]

class Fn:
    def __init__(self, t): self.t = t
    def __repr__(self): return '<%s>' % self.t

def load(path):
    raw = json.load(open(path))
    byid = {}
    pend = []
    def conv(x):
        if isinstance(x, dict):
            if 'kv' in x:
                t = LT(); t.id = x['id']; byid[x['id']] = t
                for k, v in x['kv']:
                    kk = conv(k)
                    if kk == b'fnres': kk = 'fnres'
                    t[kk] = conv(v)
                return t
            if 'ref' in x:
                r = Ref(x['ref']); pend.append(r); return r
            if 's' in x: return bytes.fromhex(x['s'])
            if 't' in x: return Fn(x['t'])
            if 'nan' in x: return float('nan')
            if 'inf' in x: return float('inf') * x['inf']
        if isinstance(x, float) and x.is_integer(): return int(x)
        return x
    class Ref:
        def __init__(self, i): self.i = i
    root = conv(raw)
    def fix(t, seen):
        if id(t) in seen: return
        seen.add(id(t))
        for k in list(t.keys()):
            v = t[k]
            if isinstance(v, Ref): t[k] = byid[v.i]
            elif isinstance(v, LT): fix(v, seen)
    fix(root, set())
    return root
