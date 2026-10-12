"""unbox.py — undo the VM's upvalue boxes.

The obfuscator's VM gives every captured local its own one-element table so a
closure and its enclosing function share mutations through it:

    local b = { v }
    b[1] = 0
    local f = (function(u1) return function() u1[1] = u1[1] + 1 end end)(b)
    ... b[1] ...

A Lua upvalue already has that sharing, so the box is pure scaffolding. This
pass turns it back into an ordinary local captured by name:

    local b = 0
    local f = function() b = b + 1 end
    ... b ...

A box is undone only when every occurrence, on both sides of the capture, is a
box operation:

  producer  the single defining `SET b = NEWT{init}`, `b[1]` reads, `b[1] = x`
            writes, and CLOSURE capture arguments;
  consumer  in the capturing prototype, slot i occurs only as `U_i[1]` (read or
            write) or as a capture argument of a deeper closure, which then
            inherits the same decision.

Anything else — the box passed as a value, stored in a table, returned —
keeps its box. Because a rejected consumer invalidates its producer, and a
re-capture propagates the decision downwards, the two sides are resolved by a
fixed point that only ever shrinks the candidate set.

Correctness rests on the local keeping the box's *lifetime*. A box built inside
a loop is a fresh table per iteration, and a by-name capture matches that only
if the local is declared inside the loop body too. `place_decls` hoists forward
declarations out of every loop, so a variable that ends up forward-declared
with its definition inside a loop would be shared across iterations instead of
one-per-iteration: `unsafe_vars` finds those after scoping and they keep their
box as well.

Rendering is in final.py: an unboxed capture must be rendered by name, never
through the by-value IIFE, since the whole point of the box was shared mutation.
"""
from collections import Counter, defaultdict

BOXKEY = ('K', 1)


def is_var(x):
    return isinstance(x, tuple) and x and x[0] in ('R', 'T', 'S', 'ACC', 'W')


def walk_exprs(stmts, fe):
    """fe(expr, is_assignment_target) over every expression of a statement list"""
    for s in stmts:
        h = s[0]
        if h in ('SET', 'LOCALSET'):
            fe(s[1], True); fe(s[2], False)
        elif h in ('MSET', 'LOCALMSET'):
            for t in s[1]:
                fe(t, True)
            fe(s[2], False)
        elif h == 'IF':
            fe(s[1], False); walk_exprs(s[2], fe); walk_exprs(s[3], fe)
        elif h == 'WHILE':
            fe(s[1], False); walk_exprs(s[2], fe)
        elif h == 'FOR':
            for e in s[2:5]:
                fe(e, False)
            walk_exprs(s[5], fe)
        elif h == 'REPEAT':
            walk_exprs(s[3], fe); walk_exprs(s[1], fe); fe(s[2], False)
        elif h == 'FORIN':
            fe(s[2], False); walk_exprs(s[3], fe)
        elif h == 'DECL':
            pass
        else:
            for y in s[1:]:
                if isinstance(y, (tuple, list)):
                    fe(y, False)


def _each(e, f, tgt):
    """f over the sub-expressions of e, preserving the target flag for the
    assignable part only (table/field of an indexed assignment is a read)"""
    for y in e[1:]:
        if isinstance(y, (tuple, list)):
            f(y, False)


def scan(body):
    """occurrences per variable, box initialisers, and the closures of `body`"""
    occ = defaultdict(Counter)
    init = {}
    closures = []

    def fe(e, tgt):
        if isinstance(e, list):
            for y in e:
                fe(y, tgt)
            return
        if not (isinstance(e, tuple) and e and isinstance(e[0], str)):
            return
        h = e[0]
        if h == 'IDX' and is_var(e[1]) and e[2] == BOXKEY:
            occ[e[1]]['boxwrite' if tgt else 'boxread'] += 1
            return
        if is_var(e):
            occ[e]['plaindef' if tgt else 'value'] += 1
            return
        if h == 'CLOSURE':
            caps = e[2][1] if e[2][0] == 'CAPS' else []
            closures.append((e[1], caps))
            for c in caps:
                if is_var(c):
                    occ[c]['capture'] += 1
                else:
                    fe(c, False)
            return
        _each(e, fe, tgt)

    # a box definition is `SET v = NEWT{ one positional item }`
    def stmt(s):
        if s[0] in ('SET', 'LOCALSET') and is_var(s[1]):
            v, e = s[1], s[2]
            if (isinstance(e, tuple) and e[0] == 'NEWT' and len(e[1]) == 1
                    and isinstance(e[1][0], tuple) and e[1][0][0] == 'ITEM'):
                occ[v]['boxdef'] += 1
                init.setdefault(v, e[1][0][1])
                fe(e[1][0][1], False)
                return True
        return False

    def blk(stmts):
        for s in stmts:
            h = s[0]
            if stmt(s):
                pass
            elif h in ('SET', 'LOCALSET'):
                fe(s[1], True); fe(s[2], False)
            elif h in ('MSET', 'LOCALMSET'):
                for t in s[1]:
                    fe(t, True)
                fe(s[2], False)
            elif h == 'IF':
                fe(s[1], False); blk(s[2]); blk(s[3])
            elif h == 'WHILE':
                fe(s[1], False); blk(s[2])
            elif h == 'FOR':
                occ[s[1]]['plaindef'] += 1
                for e in s[2:5]:
                    fe(e, False)
                blk(s[5])
            elif h == 'REPEAT':
                blk(s[3]); blk(s[1]); fe(s[2], False)
            elif h == 'FORIN':
                for v in s[1]:
                    occ[v]['plaindef'] += 1
                fe(s[2], False); blk(s[3])
            elif h == 'DECL':
                pass
            else:
                for y in s[1:]:
                    if isinstance(y, (tuple, list)):
                        fe(y, False)
    blk(body)
    return occ, init, closures


def candidates(occ):
    """variables that are boxes as far as this prototype alone can tell"""
    ok = set()
    for v, c in occ.items():
        if c['boxdef'] != 1:
            continue
        if c['value'] or c['plaindef']:
            continue
        ok.add(v)
    return ok


def slot_uses(body, slot):
    """how the capturing prototype uses upvalue `slot`"""
    out = []

    def fe(e, tgt):
        if isinstance(e, list):
            for y in e:
                fe(y, tgt)
            return
        if not (isinstance(e, tuple) and e and isinstance(e[0], str)):
            return
        if e[0] == 'IDX' and e[1] == ('U', slot) and e[2] == BOXKEY:
            out.append(('write' if tgt else 'read', None))
            return
        if e[0] == 'U' and e[1] == slot:
            out.append(('value', None))
            return
        if e[0] == 'CLOSURE':
            caps = e[2][1] if e[2][0] == 'CAPS' else []
            for j, c in enumerate(caps, 1):
                if c == ('U', slot):
                    out.append(('recapture', j))
                else:
                    fe(c, False)
            return
        _each(e, fe, tgt)
    walk_exprs(body, fe)
    return out


def plan(protos, pre_of, blocked=()):
    """fixed point: which locals lose their box, and which upvalue slots arrive
    unboxed in each prototype.

    `blocked` holds (prototype id, variable) pairs refused by an earlier round
    — for instance by the loop-lifetime check in final.py — which stay boxed.
    """
    blocked = set(blocked)
    info = {p.id: scan(pre_of(p)) for p in protos}
    cand = {p.id: {v for v in candidates(info[p.id][0])
                   if (p.id, v) not in blocked} for p in protos}
    dead = set()            # (prototype id, slot) refused by the consumer

    while True:
        # A slot is unboxed when its capture is an unboxed local of the parent,
        # or a re-capture of a slot the parent already receives unboxed. Every
        # capture site of a prototype has to agree, so this is a fixed point;
        # `protos` is a pre-order walk, which usually settles it in one pass.
        slots = {}
        while True:
            want = defaultdict(list)
            for p in protos:
                here = slots.get(p.id, ())
                for sub, caps in info[p.id][2]:
                    for i, c in enumerate(caps, 1):
                        want[(sub.id, i)].append(
                            (is_var(c) and c in cand[p.id])
                            or (isinstance(c, tuple) and c[0] == 'U'
                                and c[1] in here))
            nxt = {}
            for (sid, i), ws in want.items():
                if all(ws) and (sid, i) not in dead:
                    nxt.setdefault(sid, set()).add(i)
            if nxt == slots:
                break
            slots = nxt

        # consumer check: a slot used as a value cannot lose its box
        bad = {(p.id, i) for p in protos for i in sorted(slots.get(p.id, ()))
               if any(k == 'value' for k, _ in slot_uses(pre_of(p), i))}
        if not bad:
            return cand, slots
        dead |= bad
        # a refused slot invalidates the local it was captured from
        for p in protos:
            for sub, caps in info[p.id][2]:
                for i, c in enumerate(caps, 1):
                    if (sub.id, i) in bad and is_var(c):
                        cand[p.id].discard(c)


def rewrite(body, vars_, slots):
    """drop the box: `v = NEWT{init}` -> `v = init`, `v[1]` -> `v`, and the
    same for the upvalue slots that arrive unboxed"""
    def re_e(e, tgt=False):
        if isinstance(e, list):
            return [re_e(y) for y in e]
        if not (isinstance(e, tuple) and e and isinstance(e[0], str)):
            return e
        if e[0] == 'IDX' and e[2] == BOXKEY:
            if is_var(e[1]) and e[1] in vars_:
                return e[1]
            if isinstance(e[1], tuple) and e[1][0] == 'U' and e[1][1] in slots:
                return e[1]
        if e[0] == 'CLOSURE':
            # captures are rewritten, the sub-prototype is not (it is rendered
            # from its own `body()`, with its own slot set)
            caps = e[2]
            if caps[0] == 'CAPS':
                caps = ('CAPS', [re_e(c) for c in caps[1]])
            return (e[0], e[1], caps) + e[3:]
        return tuple(re_e(y) if isinstance(y, (tuple, list)) else y for y in e)

    def re_s(s):
        h = s[0]
        if h in ('SET', 'LOCALSET'):
            v, e = s[1], s[2]
            if (is_var(v) and v in vars_ and isinstance(e, tuple)
                    and e[0] == 'NEWT' and len(e[1]) == 1
                    and isinstance(e[1][0], tuple) and e[1][0][0] == 'ITEM'):
                return (h, v, re_e(e[1][0][1]))
            return (h, re_e(v, True), re_e(e))
        if h in ('MSET', 'LOCALMSET'):
            return (h, [re_e(t, True) for t in s[1]], re_e(s[2]))
        if h == 'IF':
            return ('IF', re_e(s[1]), [re_s(x) for x in s[2]],
                    [re_s(x) for x in s[3]])
        if h == 'WHILE':
            return ('WHILE', re_e(s[1]), [re_s(x) for x in s[2]])
        if h == 'FOR':
            return ('FOR', s[1], re_e(s[2]), re_e(s[3]), re_e(s[4]),
                    [re_s(x) for x in s[5]])
        if h == 'REPEAT':
            return ('REPEAT', [re_s(x) for x in s[1]], re_e(s[2]),
                    [re_s(x) for x in s[3]])
        if h == 'FORIN':
            return ('FORIN', s[1], re_e(s[2]), [re_s(x) for x in s[3]])
        if h == 'DECL':
            return s
        return tuple(re_e(y) if isinstance(y, (tuple, list)) else y for y in s)

    return [re_s(s) for s in body]


def unsafe_vars(body, vars_):
    """unboxed variables that scoping turned into a forward declaration while
    their definition sits inside a loop: the local would then be shared by all
    iterations, where the box was one per iteration"""
    declared = set()
    in_loop = set()

    def blk(stmts, loop):
        for s in stmts:
            h = s[0]
            if h == 'DECL':
                declared.update(v for v in s[1] if v in vars_)
            elif h == 'SET' and is_var(s[1]) and s[1] in vars_ and loop:
                in_loop.add(s[1])
            if h == 'IF':
                blk(s[2], loop); blk(s[3], loop)
            elif h == 'WHILE':
                blk(s[2], True)
            elif h == 'FOR':
                blk(s[5], True)
            elif h == 'REPEAT':
                blk(s[1], True); blk(s[3], True)
            elif h == 'FORIN':
                blk(s[3], True)
    blk(body, False)
    return declared & in_loop


def per_iteration(body, vars_):
    """variables whose box was created at the shallowest loop nesting of all
    their occurrences, so a per-iteration local reproduces its identity.

    Runs on the body *before* `rewrite`, where a box definition is still
    recognisable as `SET v = NEWT{init}`; `rewrite` does not touch control flow,
    so the nesting it sees is the same. For such a variable a forward
    declaration may stay inside that loop body instead of being hoisted out of
    it: nothing can carry a value across iterations, because the box could not.
    A box created deeper than some of its uses outlived its own iteration and
    keeps its box.
    """
    defstack = {}
    stacks = defaultdict(set)

    def mark(e, stack):
        if isinstance(e, list):
            for y in e:
                mark(y, stack)
            return
        if not (isinstance(e, tuple) and e and isinstance(e[0], str)):
            return
        if is_var(e):
            if e in vars_:
                stacks[e].add(stack)
            return
        if e[0] == 'IDX' and is_var(e[1]) and e[2] == BOXKEY:
            if e[1] in vars_:
                stacks[e[1]].add(stack)
            return
        if e[0] == 'CLOSURE':
            caps = e[2][1] if e[2][0] == 'CAPS' else []
            for c in caps:
                mark(c, stack)
            return
        for y in e[1:]:
            if isinstance(y, (tuple, list)):
                mark(y, stack)

    def blk(stmts, stack):
        for s in stmts:
            h = s[0]
            boxdef = None
            if h in ('SET', 'LOCALSET') and is_var(s[1]) and s[1] in vars_:
                e = s[2]
                if (isinstance(e, tuple) and e[0] == 'NEWT' and len(e[1]) == 1
                        and isinstance(e[1][0], tuple) and e[1][0][0] == 'ITEM'):
                    boxdef = s[1]
                    defstack.setdefault(boxdef, stack)
            if h in ('SET', 'LOCALSET'):
                if boxdef is None:
                    mark(s[1], stack)
                else:
                    stacks[boxdef].add(stack)
                mark(s[2], stack)
            elif h in ('MSET', 'LOCALMSET'):
                for t in s[1]:
                    mark(t, stack)
                mark(s[2], stack)
            elif h == 'IF':
                mark(s[1], stack); blk(s[2], stack); blk(s[3], stack)
            elif h == 'WHILE':
                mark(s[1], stack); blk(s[2], stack + (id(s),))
            elif h == 'FOR':
                for e in s[2:5]:
                    mark(e, stack)
                blk(s[5], stack + (id(s),))
            elif h == 'REPEAT':
                inner = stack + (id(s),)
                blk(s[3], inner); blk(s[1], inner); mark(s[2], inner)
            elif h == 'FORIN':
                mark(s[2], stack); blk(s[3], stack + (id(s),))
            elif h == 'DECL':
                pass
            else:
                for y in s[1:]:
                    if isinstance(y, (tuple, list)):
                        mark(y, stack)
    blk(body, ())

    ok = set()
    for v in vars_:
        if v not in defstack:
            continue
        ss = stacks[v]
        common = min(ss, key=len)
        for st in ss:
            k = 0
            while k < len(common) and k < len(st) and common[k] == st[k]:
                k += 1
            common = common[:k]
        if defstack[v] == common:
            ok.add(v)
    return ok
