"""cfgcheck.py — symbolic equivalence check between the node graph and the
structured statement tree.

The differential test compares one execution, so it only covers the paths that
trace happens to take. This check covers the shape of the control flow on the
paths it can reach instead: it replaces every branch condition by an oracle,
walks the node graph and the structured tree under the same oracle answers, and
compares the sequence of statements they execute.

An oracle answer depends on the branch and on how many times it has been asked,
drawn from a fixed seed, so loops terminate and both walks stay in step. Once
the two disagree their evaluation counts diverge as well and the traces differ,
which is what we are looking for.

A loop that is already a statement *inside* a node (recognised by
emit.apply_multret before structuring) is opaque to the structurer, which copies
it verbatim. `mark` replaces each one by an OPAQUE statement so that both walks
treat it as one step rather than one walking into it and the other not.

Use right after structure.structure() and before the passes that rewrite
statements (inline, propagate, polish): there the tree holds only IF / WHILE /
BREAK / CONTINUE / RETURN / GOTO around plain statements.
"""
import random

LIMIT = 200000
INNER_LOOPS = ('WHILE', 'FOR', 'REPEAT', 'FORIN')


class Stop(Exception):
    """a terminator: the walk ended normally"""


class Overflow(Exception):
    """the step limit was reached"""


class Brk(Exception):
    pass


class Cont(Exception):
    pass


class Jump(Exception):
    def __init__(self, n):
        self.n = n


def mark(nodes):
    """oracle per branch, keyed by node and position; inner loops made opaque.

    Returns (marked nodes, list of complaints). A GOTO inside an inner loop
    would be invisible to the structurer, so it is reported rather than hidden.
    """
    out, bad = {}, []
    counter = [0]

    def has_goto(stmts):
        for s in stmts:
            if s[0] == 'GOTO':
                return True
            if s[0] == 'IF' and (has_goto(s[2]) or has_goto(s[3])):
                return True
            if s[0] in INNER_LOOPS:
                for y in s[1:]:
                    if isinstance(y, list) and has_goto(y):
                        return True
        return False

    def tree(stmts, n):
        res = []
        for s in stmts:
            if s[0] == 'IF':
                counter[0] += 1
                res.append(('IF', ('ORACLE', counter[0]),
                            tree(s[2], n), tree(s[3], n)))
            elif s[0] in INNER_LOOPS:
                for y in s[1:]:
                    if isinstance(y, list) and has_goto(y):
                        bad.append('node %s: GOTO inside a %s body' % (n, s[0]))
                counter[0] += 1
                res.append(('OPAQUE', counter[0], repr(s)))
            else:
                res.append(s)
        return res
    for n in sorted(nodes):
        # a marker at the head of every node: a plain statement, so the
        # structurer copies it verbatim and it shows in the tree exactly where
        # that node's code was emitted. It makes the comparison node-aware and
        # names the node when the two walks disagree.
        out[n] = [('NODEMARK', n)] + tree(nodes[n], n)
    return out, bad


class Oracle:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.seen = {}
        self.vals = {}

    def ask(self, k):
        i = self.seen.get(k, 0)
        self.seen[k] = i + 1
        key = (k, i)
        if key not in self.vals:
            self.vals[key] = self.rng.random() < 0.5
        return self.vals[key]


def execute(stmts, oracle, trace, steps, graph):
    """one block; `graph` selects GOTO handling (node graph vs structured tree)"""
    for s in stmts:
        steps[0] += 1
        if steps[0] > LIMIT:
            raise Overflow
        h = s[0]
        if h == 'IF':
            execute(s[2] if oracle.ask(s[1][1]) else s[3],
                    oracle, trace, steps, graph)
        elif h == 'WHILE':
            while True:
                try:
                    execute(s[2], oracle, trace, steps, graph)
                except Cont:
                    continue
                except Brk:
                    break
        elif h == 'BREAK':
            raise Brk
        elif h == 'CONTINUE':
            raise Cont
        elif h == 'GOTO':
            if graph:
                raise Jump(s[1])
            trace.append(('UNSTRUCTURED', s[1]))
            raise Stop
        elif h in ('RETURN', 'ERRPATH', 'CRASH'):
            trace.append(repr(s))
            raise Stop
        else:
            trace.append(repr(s))


def walk_graph(nodes, entry, oracle):
    trace, steps, n = [], [0], entry
    try:
        while True:
            if n not in nodes:
                trace.append(('MISSING', n))
                break
            try:
                execute(nodes[n], oracle, trace, steps, True)
            except Jump as j:
                n = j.n
                continue
            trace.append(('FALLOUT', n))
            break
    except Stop:
        pass
    except Overflow:
        trace.append(('LIMIT',))
    except (Brk, Cont):
        trace.append(('ESCAPE',))
    return trace


def walk_tree(out, oracle):
    trace, steps = [], [0]
    try:
        execute(out, oracle, trace, steps, False)
        trace.append(('FALLOFF',))
    except Stop:
        pass
    except Overflow:
        trace.append(('LIMIT',))
    except (Brk, Cont):
        trace.append(('ESCAPE',))
    return trace


def check(nodes, entry, structure_fn, trials=120, seed=0):
    """returns (ok, trials_run, detail); ok is None when gotos remain"""
    marked, bad = mark(nodes)
    if bad:
        return False, 0, '; '.join(bad[:3])
    out, S = structure_fn(marked, entry)
    if S.labels:
        return None, 0, 'unstructured: %d label(s)' % len(S.labels)
    for t in range(trials):
        a = walk_graph(marked, entry, Oracle(seed * 10000 + t))
        b = walk_tree(out, Oracle(seed * 10000 + t))
        if a != b:
            i = 0
            while i < min(len(a), len(b)) and a[i] == b[i]:
                i += 1
            return False, t, ('trial %d diverges at step %d of %d/%d:\n'
                              '  graph: %s\n  tree : %s' % (
                                  t, i, len(a), len(b),
                                  a[i] if i < len(a) else '<end>',
                                  b[i] if i < len(b) else '<end>'))
    return True, trials, 'ok'
