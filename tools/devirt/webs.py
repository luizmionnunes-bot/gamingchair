"""webs.py — split VM registers/temporaries into independent variables.

The VM reuses a register for unrelated values. We build a statement-level CFG
over the node graph, compute reaching definitions, and union every definition
that reaches a common use into one *web*. Each web becomes its own variable
('W', id), so later passes (inlining, scoping, naming) see real variables.

Occurrences are enumerated in a deterministic traversal; the same traversal is
used to rewrite, so occurrence k of the analysis is occurrence k of the rewrite.
"""
from collections import defaultdict

VARS = ('R', 'T', 'S', 'ACC')
def is_var(x): return isinstance(x, tuple) and x and x[0] in VARS

def expr_uses(e, out):
    if isinstance(e, tuple) and e and isinstance(e[0], str):
        if is_var(e): out.append(e); return
        for y in e[1:]:
            if isinstance(y, (tuple, list)): expr_uses(y, out)
    elif isinstance(e, list):
        for y in e: expr_uses(y, out)

def lhs_parts(l, uses):
    """uses inside an assignment target (index object/key); returns written var or None"""
    if is_var(l): return l
    expr_uses(l, uses)
    return None

class Builder:
    """statement-level CFG. vertex = list of ('use'|'def', var, occ_id)"""
    def __init__(self):
        self.V = []            # vertex events
        self.succ = []
        self.occ = 0
        self.node_entry = {}
        self.pending_goto = []  # (vertex, node)

    def vertex(self, events):
        self.V.append(events); self.succ.append([])
        return len(self.V) - 1

    def ev(self, kind, var):
        o = self.occ; self.occ += 1
        return (kind, var, o)

    def atomic(self, st):
        """events for a non-compound statement, in evaluation order"""
        h = st[0]
        evs = []
        if h in ('SET', 'LOCAL'):
            uses = []
            w = lhs_parts(st[1], uses) if h == 'SET' else st[1]
            expr_uses(st[2], uses)
            evs = [self.ev('use', u) for u in uses]
            if w is not None and is_var(w): evs.append(self.ev('def', w))
        elif h in ('MSET', 'LOCALS'):
            uses = []
            expr_uses(st[2], uses)
            evs = [self.ev('use', u) for u in uses] + [self.ev('def', t) for t in st[1] if is_var(t)]
        else:
            uses = []
            for y in st[1:]:
                if isinstance(y, (tuple, list)): expr_uses(y, uses)
            evs = [self.ev('use', u) for u in uses]
        return evs

    def seq(self, stmts, nxt, loop):
        """build vertices for stmts flowing into vertex `nxt`; returns entry vertex.
        loop = (continue_target, break_target)"""
        # process forward to keep occurrence order = traversal order, link afterwards
        entries = []
        exits = []      # list of (vertex, kind) to link to the following statement
        first = None
        prev_exits = None
        for st in stmts:
            ent, ex = self.stmt(st, loop)
            if prev_exits is not None:
                for v in prev_exits: self.succ[v].append(ent)
            if first is None: first = ent
            prev_exits = ex
        if first is None:
            return None, []
        return first, prev_exits

    def stmt(self, st, loop):
        """returns (entry vertex, list of fall-through exit vertices)"""
        h = st[0]
        if h == 'IF':
            c = self.vertex(self.atomic(('EXPR', st[1])))
            a, ax = self.seq(st[2], None, loop)
            b, bx = self.seq(st[3], None, loop)
            ex = []
            if a is None: ex.append(c)
            else: self.succ[c].append(a); ex += ax
            if b is None: ex.append(c)
            else: self.succ[c].append(b); ex += bx
            return c, ex
        if h == 'WHILE':
            c = self.vertex(self.atomic(('EXPR', st[1])))
            brk = []
            body, bx = self.seq(st[2], None, (c, brk))
            if body is not None:
                self.succ[c].append(body)
                for v in bx: self.succ[v].append(c)
            return c, [c] + brk     # (while true with break: c's exit edge is harmless/conservative)
        if h == 'FOR':
            init = self.vertex([self.ev('use', u) for u in uses_of([st[2], st[3], st[4]])] + [self.ev('def', st[1])])
            head = self.vertex([self.ev('def', st[1])])
            self.succ[init].append(head)
            brk = []
            body, bx = self.seq(st[5], None, (head, brk))
            if body is not None:
                self.succ[head].append(body)
                for v in bx: self.succ[v].append(head)
            return init, [head] + brk
        if h == 'REPEAT':
            # body (scratch + body) then condition
            brk = []
            cond = None
            body, bx = self.seq(st[3] + st[1], None, (None, brk))
            cond = self.vertex(self.atomic(('EXPR', st[2])))
            for v in bx: self.succ[v].append(cond)
            if body is not None: self.succ[cond].append(body)
            # continue targets in a repeat go to the condition
            for v in self.pending_cont: self.succ[v].append(cond)
            self.pending_cont = []
            return (body if body is not None else cond), [cond] + brk
        if h == 'BREAK':
            v = self.vertex([])
            if loop: loop[1].append(v)
            return v, []
        if h == 'CONTINUE':
            v = self.vertex([])
            if loop and loop[0] is not None: self.succ[v].append(loop[0])
            else: self.pending_cont.append(v)
            return v, []
        if h == 'GOTO':
            v = self.vertex([])
            self.pending_goto.append((v, st[1]))
            return v, []
        if h in ('RETURN', 'CRASH', 'ERRPATH', 'GOTOX'):
            v = self.vertex(self.atomic(st))
            return v, []
        v = self.vertex(self.atomic(st))
        return v, [v]

    pending_cont = []

def uses_of(exprs):
    u = []
    for e in exprs: expr_uses(e, u)
    return u

def analyze(nodes, entry, params):
    B = Builder()
    B.pending_cont = []
    order = sorted(nodes, key=lambda n: (n != entry, n))
    start = B.vertex([B.ev('def', p) for p in params])      # parameter definitions
    for n in order:
        ent, ex = B.seq(nodes[n], None, None)
        if ent is None:
            ent = B.vertex([]); ex = [ent]
        B.node_entry[n] = ent
    for v, n in B.pending_goto:
        if n in B.node_entry: B.succ[v].append(B.node_entry[n])
    B.succ[start].append(B.node_entry[entry])
    # reaching definitions: per vertex, var -> frozenset(def occ)
    nV = len(B.V)
    pred = defaultdict(list)
    for v in range(nV):
        for s in B.succ[v]: pred[s].append(v)
    UNINIT = -1
    IN = [None] * nV
    OUT = [dict() for _ in range(nV)]
    def transfer(v, inn):
        cur = dict(inn)
        for kind, var, o in B.V[v]:
            if kind == 'def': cur[var] = frozenset([o])
        return cur
    work = list(range(nV))
    inset = set(work)
    while work:
        v = work.pop()
        inset.discard(v)
        inn = {}
        for p in pred[v]:
            for var, ds in OUT[p].items():
                inn[var] = inn.get(var, frozenset()) | ds
        IN[v] = inn
        out = transfer(v, inn)
        if out != OUT[v]:
            OUT[v] = out
            for s in B.succ[v]:
                if s not in inset: inset.add(s); work.append(s)
    # union-find over def occurrences, joined at uses
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent.setdefault(parent[x], parent[x]); x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    use_web = {}
    for v in range(nV):
        cur = dict(IN[v] or {})
        for kind, var, o in B.V[v]:
            if kind == 'use':
                ds = cur.get(var, frozenset([('U', var)]))     # uninitialised read
                ds = list(ds)
                for d in ds[1:]: union(ds[0], d)
                use_web[o] = ds[0]
            else:
                find(o)
                cur[var] = frozenset([o])
    rename = {}
    for v in range(nV):
        for kind, var, o in B.V[v]:
            root = find(o) if kind == 'def' else find(use_web[o])
            rename[o] = root
    return rename, B.occ

def apply(nodes, entry, params):
    """returns (new nodes, mapping web-var -> original var) — params keep their var"""
    rename, nocc = analyze(nodes, entry, params)
    webs = {}
    pvars = {}
    # parameter webs keep the parameter variable
    counter = [0]
    order = sorted(nodes, key=lambda n: (n != entry, n))
    # replay the same traversal, replacing occurrence k by its web variable
    B = Builder(); B.pending_cont = []
    B.vertex([B.ev('def', p) for p in params])
    param_occ = {o: p for o, p in zip(range(len(params)), params)}
    for o, p in param_occ.items(): pvars[rename[o]] = p
    def wvar(o, orig):
        r = rename[o]
        if r in pvars: return pvars[r]
        if r not in webs:
            counter[0] += 1
            webs[r] = ('W', counter[0], orig[0])
        return webs[r]
    out = {}
    for n in order:
        out[n] = rewrite_seq(B, nodes[n], wvar)
    return out

# the rewrite replays Builder's traversal order exactly
def rewrite_seq(B, stmts, wvar):
    return [rewrite_stmt(B, st, wvar) for st in stmts]

def rewrite_stmt(B, st, wvar):
    h = st[0]
    if h == 'IF':
        c = rewrite_atomic(B, ('EXPR', st[1]), wvar)[1]
        a = rewrite_seq(B, st[2], wvar)
        b = rewrite_seq(B, st[3], wvar)
        return ('IF', c, a, b)
    if h == 'WHILE':
        c = rewrite_atomic(B, ('EXPR', st[1]), wvar)[1]
        body = rewrite_seq(B, st[2], wvar)
        return ('WHILE', c, body)
    if h == 'FOR':
        # init: uses of bounds then def of loop var; head: def of loop var
        exprs = [st[2], st[3], st[4]]
        new = [sub_uses(B, e, wvar) for e in exprs]
        v1 = wvar(B.ev('def', st[1])[2], st[1])
        v2 = wvar(B.ev('def', st[1])[2], st[1])
        body = rewrite_seq(B, st[5], wvar)
        return ('FOR', v1, new[0], new[1], new[2], body)
    if h == 'REPEAT':
        allb = rewrite_seq(B, st[3] + st[1], wvar)
        cond = rewrite_atomic(B, ('EXPR', st[2]), wvar)[1]
        return ('REPEAT', allb, cond, [])
    if h in ('BREAK', 'CONTINUE', 'GOTO'):
        return st
    return rewrite_atomic(B, st, wvar)

def sub_uses(B, e, wvar):
    if isinstance(e, tuple) and e and isinstance(e[0], str):
        if is_var(e): return wvar(B.ev('use', e)[2], e)
        return tuple(sub_uses(B, y, wvar) if isinstance(y, (tuple, list)) else y for y in e)
    if isinstance(e, list): return [sub_uses(B, y, wvar) for y in e]
    return e

def sub_lhs(B, l, wvar):
    if is_var(l): return None
    return sub_uses(B, l, wvar)

def rewrite_atomic(B, st, wvar):
    h = st[0]
    if h in ('SET', 'LOCAL'):
        l = st[1]
        if h == 'SET' and not is_var(l):
            nl = sub_uses(B, l, wvar)
            ne = sub_uses(B, st[2], wvar)
            return ('SET', nl, ne)
        ne = sub_uses(B, st[2], wvar)
        nv = wvar(B.ev('def', l)[2], l)
        return (h, nv, ne)
    if h in ('MSET', 'LOCALS'):
        ne = sub_uses(B, st[2], wvar)
        nv = [wvar(B.ev('def', t)[2], t) if is_var(t) else t for t in st[1]]
        return (h, nv, ne)
    return tuple(sub_uses(B, y, wvar) if isinstance(y, (tuple, list)) else y for y in st)
