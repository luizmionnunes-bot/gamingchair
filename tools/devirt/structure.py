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
        self._refine_follow()

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


    def reach(self, n, avoid=None):
        R, st = set(), [n]
        while st:
            x = st.pop()
            if x in R or x == avoid or x not in self.nodes:
                continue
            R.add(x)
            st.extend(self.succ.get(x, []))
        return R

    def weak_join(self, n, targets):
        """the convergence point of a two-way branch whose post-dominator is the
        exit.

        `ipdom` treats a `return` as reaching the exit, so a branch with one
        returning arm post-dominates nothing and the structurer has to goto the
        node where the arms actually meet. That node is still a sound place to
        continue after the `if`, provided it can only be entered from inside the
        branch: `n` must dominate it, and every one of its predecessors must be
        reachable from `n`. Both arms are then truncated there and fall out of
        the `if` onto it.
        """
        if len(targets) != 2:
            return None
        ra, rb = self.reach(targets[0]), self.reach(targets[1])
        both = (ra & rb) - {n}
        if not both:
            return None
        idx = {x: i for i, x in enumerate(self.rpo)}
        reach_n = ra | rb
        for j in sorted(both, key=lambda x: idx.get(x, 10 ** 9)):
            if not self.dominates(n, j) or j == n:
                continue
            if all(q in reach_n or q == n for q in self.pred[j]):
                return j
        return None

    def _refine_follow(self):
        """prefer the header's immediate post-dominator as the loop follow.

        The RPO heuristic picks the exit closest in reverse post-order, which for
        a loop with several exit targets is usually one of the intermediate ones;
        every edge to any other exit then has nowhere structured to go and turns
        into a goto. The immediate post-dominator is where all the exits
        converge, so the other exit targets are emitted inside the loop body and
        reach it with a plain `break`.
        """
        for h, body in self.loop_body.items():
            j = self.ipdom.get(h)
            if j is None or j == self.EXIT or j in body or j not in self.nodes:
                continue
            exits = {s for x in body for s in self.succ[x] if s not in body}
            if j in exits or any(self.dominates(j, e) for e in exits):
                self.follow[h] = j


def sccs_of(succ, universe):
    """strongly connected components of the subgraph induced by `universe`,
    iterative Tarjan. Restricting the node set is what lets the caller look for
    an irreducible cycle *inside* a reducible loop, which a single pass over the
    whole graph hides inside the outer component."""
    def out(n):
        return [s for s in succ.get(n, []) if s in universe]
    index, low, on, stack, comps = {}, {}, set(), [], []
    counter = [0]
    for root in universe:
        if root in index:
            continue
        work = [(root, iter(out(root)))]
        index[root] = low[root] = counter[0]; counter[0] += 1
        stack.append(root); on.add(root)
        while work:
            n, it = work[-1]
            nxt = next(it, None)
            if nxt is None:
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[n])
                if low[n] == index[n]:
                    comp = set()
                    while True:
                        x = stack.pop(); on.discard(x); comp.add(x)
                        if x == n:
                            break
                    comps.append(comp)
                continue
            if nxt not in index:
                index[nxt] = low[nxt] = counter[0]; counter[0] += 1
                stack.append(nxt); on.add(nxt)
                work.append((nxt, iter(out(nxt))))
            elif nxt in on:
                low[n] = min(low[n], index[nxt])
    return comps


def retarget(stmts, remap):
    out = []
    for s in stmts:
        if s[0] == 'GOTO' and s[1] in remap:
            out.append(('GOTO', remap[s[1]]))
        elif s[0] == 'IF':
            out.append(('IF', s[1], retarget(s[2], remap), retarget(s[3], remap)))
        else:
            out.append(s)
    return out


def split_irreducible(nodes, entry, budget=400, rounds=12):
    """duplicate the secondary entries of irreducible loops.

    The VM's code sharing — one block jumped to from two distant places, each
    continuing at the same successor — puts two entries on a cycle, so no node
    dominates it and the dominator-based structurer has to fall back to gotos.
    Duplicating the nodes a secondary entry reaches before the chosen header
    leaves that cycle with a single entry, which structures normally. Both paths
    are mutually exclusive at run time and the copy references the same
    variables, so this is literal code duplication.

    `budget` caps the statements copied per split; a loop that would cost more
    keeps its gotos (and the caller its dispatcher).
    """
    for _ in range(rounds):
        G = Graph(nodes, entry)
        idx = {n: i for i, n in enumerate(G.rpo)}
        best = [None]

        def visit(universe, depth):
            for comp in sccs_of(G.succ, universe):
                if len(comp) == 1:
                    n = next(iter(comp))
                    if n not in G.succ.get(n, []):
                        continue
                ext = {}
                for x in comp:
                    for q in G.pred[x]:
                        if q not in comp and q in G.nodes:
                            ext.setdefault(x, []).append(q)
                if not ext:
                    continue
                hdr = min(ext, key=lambda e: idx.get(e, 10 ** 9))
                for e in ext:
                    if e == hdr:
                        continue
                    dup, stack = set(), [e]
                    while stack:
                        x = stack.pop()
                        if x in dup or x == hdr:
                            continue
                        dup.add(x)
                        stack.extend(t for t in G.succ.get(x, []) if t in comp)
                    cost = sum(len(nodes[x]) for x in dup)
                    if cost <= budget and (best[0] is None or cost < best[0][2]):
                        best[0] = (e, dup, cost, ext[e])
                if depth < 8:
                    visit(comp - {hdr}, depth + 1)

        visit(set(nodes), 0)
        best = best[0]
        if best is None:
            return nodes
        e, dup, _cost, preds = best
        base = max(nodes) + 1
        remap = {x: base + i for i, x in enumerate(sorted(dup))}
        new = dict(nodes)
        for x in dup:
            new[remap[x]] = retarget(nodes[x], remap)
        for q in preds:
            new[q] = retarget(nodes[q], {e: remap[e]})
        nodes = new
    return nodes


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
                # The body's stop set is the loop's own follow only: an outer
                # stop node must not be inherited here. Truncating a branch at a
                # stop node makes control fall out of the enclosing `if`, which
                # inside a loop body means going round the loop again, not
                # reaching that node. Dropping them turns such an edge into an
                # inline emission or a reported goto instead of wrong code.
                body_stop = frozenset({follow}) if follow is not None else frozenset()
                body_out = self.emit_node(n, body_stop, (n, follow), fresh=True)
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
            if j is None or j == self.G.EXIT or j not in self.nodes:
                j = self.G.weak_join(n, tg)
            # Truncating the arms at the join makes control fall out of the
            # `if` onto whatever the enclosing chain emits next. That is this
            # node's own continuation when the join is still unemitted, and the
            # enclosing construct's when the join is already one of its stop
            # nodes. In any other case nobody would emit it, so the fall-out
            # would land on the wrong statement: leave join unset and let the
            # arms keep their own transfers (break / continue, or a goto that
            # gets reported).
            if j is not None and (j not in self.emitted or j in stop):
                join = j
        inner_stop = stop | ({join} if join is not None else set())
        res = self.tree(st, inner_stop, loop)
        if join is not None and join not in stop:
            return res, join
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
