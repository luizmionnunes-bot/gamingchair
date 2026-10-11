"""structure.py — turn a per-instruction IR graph into structured statements.

Input: nodes {id: [stmts]} where every path of a node's statement tree ends in
('GOTO', id) or ('RETURN', ...) (IF trees allowed), and an entry id.
Output: a statement list using IF / WHILE / BREAK / CONTINUE / RETURN.

Method: dominators -> natural loops (back edges to a dominating header);
post-dominators give the join point of two-way branches. Edges to the
current loop header become `continue`, edges to the loop's follow become
`break`. Anything that does not fit (irreducible flow, a second visit of a
node) falls back to `goto`/label, which is reported.
"""
from collections import defaultdict

def term_targets(stmts):
    r = []
    for s in stmts:
        if s[0] == 'GOTO': r.append(s[1])
        elif s[0] == 'IF': r += term_targets(s[2]) + term_targets(s[3])
        elif s[0] in ('WHILE', 'FOR', 'REPEAT', 'FORIN'):
            pass
    return r

def ends(stmts):
    """does every path of stmts end in a terminator?"""
    if not stmts: return False
    s = stmts[-1]
    if s[0] in ('GOTO', 'RETURN', 'BREAK', 'CONTINUE', 'ERRPATH', 'CRASH'): return True
    if s[0] == 'IF': return ends(s[2]) and ends(s[3])
    return False

class Graph:
    def __init__(self, nodes, entry):
        self.nodes, self.entry = nodes, entry
        self.succ = {n: list(dict.fromkeys(term_targets(st))) for n, st in nodes.items()}
        self.pred = defaultdict(list)
        for n, ss in self.succ.items():
            for s in ss: self.pred[s].append(n)
        self.rpo = self._rpo()
        self.idom = self._dominators(self.entry, self.succ, self.pred, self.rpo)
        self._loops()
        self._postdom()

    def _rpo(self):
        seen, order = set(), []
        stack = [(self.entry, iter(self.succ.get(self.entry, [])))]
        seen.add(self.entry)
        while stack:
            n, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                order.append(n); stack.pop(); continue
            if nxt not in seen and nxt in self.nodes:
                seen.add(nxt); stack.append((nxt, iter(self.succ.get(nxt, []))))
        return order[::-1]

    @staticmethod
    def _dominators(entry, succ, pred, rpo):
        idx = {n: i for i, n in enumerate(rpo)}
        idom = {entry: entry}
        changed = True
        while changed:
            changed = False
            for n in rpo:
                if n == entry: continue
                ps = [p for p in pred[n] if p in idom and p in idx]
                if not ps: continue
                new = ps[0]
                for p in ps[1:]:
                    a, b = p, new
                    while a != b:
                        while idx[a] > idx[b]: a = idom[a]
                        while idx[b] > idx[a]: b = idom[b]
                    new = a
                if idom.get(n) != new:
                    idom[n] = new; changed = True
        return idom

    def dominates(self, a, b):
        while True:
            if a == b: return True
            if b == self.entry or b not in self.idom: return False
            b = self.idom[b]

    def _loops(self):
        self.loop_body = {}     # header -> set of nodes
        self.irreducible = []
        for n in self.rpo:
            for s in self.succ[n]:
                if s in self.idom and self.dominates(s, n):
                    body = self.loop_body.setdefault(s, {s})
                    stack = [n]
                    while stack:
                        x = stack.pop()
                        if x in body: continue
                        body.add(x)
                        stack.extend(p for p in self.pred[x] if p in self.idom)
        # innermost loop of each node
        self.loop_of = {}
        for h in sorted(self.loop_body, key=lambda h: len(self.loop_body[h]), reverse=True):
            for x in self.loop_body[h]: self.loop_of[x] = h
        # loop follow: the exit target outside the body (prefer the one closest in RPO)
        idx = {n: i for i, n in enumerate(self.rpo)}
        self.follow = {}
        for h, body in self.loop_body.items():
            exits = [s for x in body for s in self.succ[x] if s not in body]
            if exits:
                self.follow[h] = min(set(exits), key=lambda e: idx.get(e, 10 ** 9))

    def _postdom(self):
        EXIT = '__exit'
        rsucc = defaultdict(list); rpred = defaultdict(list)
        for n in self.rpo:
            ss = self.succ[n]
            if not ss: rsucc[EXIT].append(n); rpred[n].append(EXIT)
            for s in ss:
                rsucc[s].append(n); rpred[n].append(s)
        # nodes in infinite loops: connect their header to exit so every node post-dominates somewhere
        for h in self.loop_body:
            if h not in self.follow:
                rsucc[EXIT].append(h); rpred[h].append(EXIT)
        seen, order = set([EXIT]), []
        stack = [(EXIT, iter(rsucc[EXIT]))]
        while stack:
            n, it = stack[-1]
            nxt = next(it, None)
            if nxt is None: order.append(n); stack.pop(); continue
            if nxt not in seen: seen.add(nxt); stack.append((nxt, iter(rsucc[nxt])))
        rpo = order[::-1]
        self.ipdom = self._dominators(EXIT, rsucc, rpred, rpo)
        self.EXIT = EXIT


class Structurer:
    def __init__(self, nodes, entry):
        self.G = Graph(nodes, entry)
        self.nodes = nodes
        self.emitted = set()
        self.gotos = 0
        self.labels = set()

    def run(self):
        out = self.emit(self.G.entry, frozenset(), None)
        return out

    def emit(self, n, stop, loop):
        """emit node n and what follows, until reaching a node in `stop`.
        loop = (header, follow) of the innermost enclosing loop being emitted."""
        out = []
        while n is not None:
            if loop and n == loop[1]: out.append(('BREAK',)); return out
            if loop and n == loop[0] and n in self.emitted: out.append(('CONTINUE',)); return out
            if n in stop: return out
            if n in self.emitted and n in self.nodes and not self.G.succ.get(n) and len(self.nodes[n]) <= 12:
                out += self.tree(self.nodes[n], stop, loop)     # duplicate a small terminal block
                return out
            if n in self.emitted or n not in self.nodes:
                self.gotos += 1; self.labels.add(n)
                out.append(('GOTO', n)); return out
            G = self.G
            if n in G.loop_body and (loop is None or loop[0] != n):
                # emit the loop headed at n
                follow = G.follow.get(n)
                body_out = self.emit_node(n, stop | ({follow} if follow is not None else set()), (n, follow), fresh=True)
                out.append(('WHILE', ('K', True), body_out))
                n = follow
                if n is not None and n in self.emitted: n = None
                continue
            body, nxt = self.node_body(n, stop, loop)
            out += body
            n = nxt
        return out

    def emit_node(self, n, stop, loop, fresh=False):
        body, nxt = self.node_body(n, stop, loop)
        if nxt is not None:
            body += self.emit(nxt, stop, loop)
        return body

    def node_body(self, n, stop, loop):
        """emit statements of node n; returns (stmts, single fall-through successor or None)"""
        self.emitted.add(n)
        if n in self.labels: pass
        st = self.nodes[n]
        tg = list(dict.fromkeys(term_targets(st)))
        join = None
        if len(tg) > 1:
            j = self.G.ipdom.get(n)
            if j is not None and j != self.G.EXIT and j in self.nodes:
                join = j
        inner_stop = stop | ({join} if join is not None else set())
        res = self.tree(st, inner_stop, loop)
        if join is not None:
            if join in stop: return res, None
            return res, join if join not in self.emitted else None
        return res, None

    def tree(self, stmts, stop, loop):
        out = []
        for s in stmts:
            if s[0] == 'GOTO':
                out += self.emit(s[1], stop, loop)
            elif s[0] == 'IF':
                a = self.tree(s[2], stop, loop)
                b = self.tree(s[3], stop, loop)
                out.append(('IF', s[1], a, b))
            else:
                out.append(s)
        return out


def structure(nodes, entry):
    S = Structurer(nodes, entry)
    out = S.run()
    if S.labels:
        out = add_labels(out, S)
    return out, S

def add_labels(out, S):
    """fallback: emit unstructured targets as labelled blocks after the body"""
    extra = []
    done = set()
    pending = list(S.labels)
    while pending:
        n = pending.pop()
        if n in done: continue
        done.add(n)
        if n not in S.nodes: continue
        S.emitted.discard(n)
        before = set(S.labels)
        body = S.emit(n, frozenset(), None)
        extra.append(('LABEL', n))
        extra += body
        pending += [l for l in S.labels if l not in done]
    return out + extra
