#!/usr/bin/env python3
"""flat.py — linearize control-flow-flattened Luau into labelled basic blocks.

usage: flat.py <file.lua> [--ast file.json] [--fn LINE] [--out out.lua]

Parses <file.lua> with `luau-ast` (env LUAU_AST, default `luau-ast`) and
pretty-prints it. Every dispatch loop (`while/repeat` driven by a local
"state" variable compared against numeric constants) is symbolically executed:
for each reachable state we follow the decision tree with the state value
known, emit only the real statements, and end the block with `goto S<next>`.
Data-dependent branches that change the state are forked (`if c then ... goto
A else ... goto B end`). States with a single predecessor are inlined.

The output is *pseudo-Lua* (uses goto/labels) meant for reading/analysis.
--fn LINE  restricts output to the function whose header is on source LINE
(1-based) — handy for 5k-line handlers.
"""
import json, os, subprocess, sys, re
from collections import defaultdict

sys.setrecursionlimit(100000)

# ---------------------------------------------------------------- AST utils
def nt(n): return n.get('type') if isinstance(n, dict) else None
def blk(b):
    if b is None: return []
    return b['body'] if nt(b) == 'AstStatBlock' else [b]
def lkey(loc_node):  # identity of a local = decl location
    return loc_node['location']
def line_of(n): return int(n['location'].split(',')[0]) + 1

def walk(n, fn):
    if isinstance(n, dict):
        if fn(n) is False: return
        for v in n.values(): walk(v, fn)
    elif isinstance(n, list):
        for v in n: walk(v, fn)

def walk_nofunc(n, fn):
    """walk without descending into nested function expressions"""
    def g(x):
        if nt(x) == 'AstExprFunction': return False
        return fn(x)
    if nt(n) == 'AstExprFunction':
        walk(n['body'], g)
    else:
        walk(n, g)

# ---------------------------------------------------------------- printer
PREC = {'Or': 1, 'And': 2, 'CompareLt': 3, 'CompareGt': 3, 'CompareLe': 3, 'CompareGe': 3,
        'CompareNe': 3, 'CompareEq': 3, 'Concat': 4, 'Add': 5, 'Sub': 5, 'Mul': 6, 'Div': 6,
        'FloorDiv': 6, 'Mod': 6, 'Pow': 8}
OPS = {'Or': 'or', 'And': 'and', 'CompareLt': '<', 'CompareGt': '>', 'CompareLe': '<=',
       'CompareGe': '>=', 'CompareNe': '~=', 'CompareEq': '==', 'Concat': '..', 'Add': '+',
       'Sub': '-', 'Mul': '*', 'Div': '/', 'FloorDiv': '//', 'Mod': '%', 'Pow': '^'}
UOPS = {'Not': 'not ', 'Minus': '-', 'Len': '#'}
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
KEYWORDS = set('and break do else elseif end false for function if in local nil not or repeat return then true until while continue'.split())

def lstr(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '\\': out.append('\\\\')
        elif ch == '"': out.append('\\"')
        elif ch == '\n': out.append('\\n')
        elif 32 <= o < 127: out.append(ch)
        elif o < 256: out.append('\\%d' % o if True else '')
        else: out.append(ch)
    # avoid \ddd followed by digit ambiguity
    r = ''.join(out)
    return '"' + re.sub(r'\\(\d{1,2})(?=\d)', lambda m: '\\%03d' % int(m.group(1)), r) + '"'

def lnum(v):
    if isinstance(v, float) and v.is_integer() and abs(v) < 2**63: return str(int(v))
    if v == float('inf'): return 'math.huge'
    return repr(v)


class Printer:
    def __init__(self, names=None):
        self.names = names or {}   # local key -> display name override

    def lname(self, L):
        return self.names.get(lkey(L), L['name'])

    # expressions -----------------------------------------------------
    def e(self, n, prec=0):
        t = nt(n)
        if t == 'AstExprGroup': return '(' + self.e(n['expr']) + ')'
        if t == 'AstExprConstantNil': return 'nil'
        if t == 'AstExprConstantBool': return 'true' if n['value'] else 'false'
        if t == 'AstExprConstantNumber': return lnum(n['value'])
        if t == 'AstExprConstantString': return lstr(n['value'])
        if t == 'AstExprLocal': return self.lname(n['local'])
        if t == 'AstExprGlobal': return n['global']
        if t == 'AstExprVarargs': return '...'
        if t == 'AstExprCall':
            f = n['func']
            if nt(f) == 'AstExprFunction' or (nt(f) == 'AstExprGroup' and nt(f['expr']) == 'AstExprFunction'):
                r = const_iife(n)
                if r is not None: return lnum(r) + ' --[[iife]]' if False else lnum(r)
            fs = self.e(f, 10)
            if nt(f) not in ('AstExprLocal', 'AstExprGlobal', 'AstExprIndexName', 'AstExprIndexExpr', 'AstExprCall', 'AstExprGroup'):
                fs = '(' + self.e(f) + ')'
            if n.get('self'):
                return self.e(f['expr'], 10) + ':' + f['index'] + '(' + ', '.join(self.e(a) for a in n['args']) + ')'
            return fs + '(' + ', '.join(self.e(a) for a in n['args']) + ')'
        if t == 'AstExprIndexName':
            return self._prefix(n['expr']) + '.' + n['index']
        if t == 'AstExprIndexExpr':
            return self._prefix(n['expr']) + '[' + self.e(n['index']) + ']'
        if t == 'AstExprFunction':
            return self.func(n)
        if t == 'AstExprTable':
            items = []
            for it in n['items']:
                k = it['kind']
                if k == 'item' or k == 'List': items.append(self.e(it['value']))
                elif k == 'record' or k == 'Record': items.append(it['key']['value'] + ' = ' + self.e(it['value']) if IDENT.match(it['key']['value']) and it['key']['value'] not in KEYWORDS else '[' + self.e(it['key']) + '] = ' + self.e(it['value']))
                else: items.append('[' + self.e(it['key']) + '] = ' + self.e(it['value']))
            if not items: return '{}'
            s = '{ ' + ', '.join(items) + ' }'
            return s
        if t == 'AstExprUnary':
            s = UOPS[n['op']] + self.e(n['expr'], 7)
            return '(' + s + ')' if prec > 7 else s
        if t == 'AstExprBinary':
            op = n['op']; p = PREC[op]
            right_assoc = op in ('Concat', 'Pow')
            l = self.e(n['left'], p + (1 if right_assoc else 0))
            r = self.e(n['right'], p + (0 if right_assoc else 1))
            s = l + ' ' + OPS[op] + ' ' + r
            return '(' + s + ')' if p < prec else s
        if t == 'AstExprIfElse':
            s = 'if ' + self.e(n['condition']) + ' then ' + self.e(n['trueExpr']) + ' else ' + self.e(n['falseExpr'])
            return '(' + s + ')' if prec > 0 else s
        if t == 'AstExprTypeAssertion':
            return self.e(n['expr'], prec)
        if t == 'AstExprInterpString':
            return '`<interp>`'
        raise Exception('expr ' + str(t))

    def _prefix(self, x):
        if nt(x) in ('AstExprLocal', 'AstExprGlobal', 'AstExprIndexName', 'AstExprIndexExpr', 'AstExprCall', 'AstExprGroup'):
            return self.e(x, 10)
        return '(' + self.e(x) + ')'

    def func(self, n, name=None, ind=''):
        args = [self.lname(a) for a in n['args']]
        if n.get('vararg'): args.append('...')
        head = 'function' + ((' ' + name) if name else '') + '(' + ', '.join(args) + ')'
        body = FuncLinearizer(self, n).render(ind + '    ')
        return head + '\n' + body + ind + 'end'

    # statements ------------------------------------------------------
    def s(self, n, ind):
        t = nt(n)
        P = lambda x: ind + x + '\n'
        if t == 'AstStatBlock':
            return P('do') + ''.join(self.s(x, ind + '    ') for x in n['body']) + P('end')
        if t == 'AstStatLocal':
            vs = ', '.join(self.lname(v) for v in n['vars'])
            if n['values']:
                return P('local ' + vs + ' = ' + ', '.join(self.e(x) for x in n['values']).replace('\n', '\n'))
            return P('local ' + vs)
        if t == 'AstStatAssign':
            return P(', '.join(self.e(x) for x in n['vars']) + ' = ' + ', '.join(self.e_ind(x, ind) for x in n['values']))
        if t == 'AstStatCompoundAssign':
            return P(self.e(n['var']) + ' ' + OPS[n['op']] + '= ' + self.e(n['value']))
        if t == 'AstStatExpr':
            return P(self.e_ind(n['expr'], ind))
        if t == 'AstStatReturn':
            return P(('return ' + ', '.join(self.e_ind(x, ind) for x in n['list'])).rstrip())
        if t == 'AstStatBreak': return P('break')
        if t == 'AstStatContinue': return P('continue')
        if t == 'AstStatLocalFunction':
            return ind + 'local ' + self.func(n['func'], self.lname(n['name']), ind) + '\n'
        if t == 'AstStatFunction':
            return ind + self.func(n['func'], self.e(n['name']), ind) + '\n'
        if t == 'AstStatIf':
            out = P('if ' + self.e(n['condition']) + ' then')
            out += ''.join(self.s(x, ind + '    ') for x in blk(n['thenbody']))
            eb = n.get('elsebody')
            while eb is not None and nt(eb) == 'AstStatIf':
                out += P('elseif ' + self.e(eb['condition']) + ' then')
                out += ''.join(self.s(x, ind + '    ') for x in blk(eb['thenbody']))
                eb = eb.get('elsebody')
            if eb is not None:
                out += P('else') + ''.join(self.s(x, ind + '    ') for x in blk(eb))
            return out + P('end')
        if t == 'AstStatWhile':
            lin = LoopLinearizer.try_make(self, n)
            if lin: return lin.render(ind)
            return P('while ' + self.e(n['condition']) + ' do') + ''.join(self.s(x, ind + '    ') for x in blk(n['body'])) + P('end')
        if t == 'AstStatRepeat':
            lin = LoopLinearizer.try_make(self, n)
            if lin: return lin.render(ind)
            return P('repeat') + ''.join(self.s(x, ind + '    ') for x in blk(n['body'])) + P('until ' + self.e(n['condition']))
        if t == 'AstStatFor':
            h = 'for ' + self.lname(n['var']) + ' = ' + self.e(n['from']) + ', ' + self.e(n['to'])
            if n.get('step') is not None: h += ', ' + self.e(n['step'])
            return P(h + ' do') + ''.join(self.s(x, ind + '    ') for x in blk(n['body'])) + P('end')
        if t == 'AstStatForIn':
            h = 'for ' + ', '.join(self.lname(v) for v in n['vars']) + ' in ' + ', '.join(self.e(x) for x in n['values'])
            return P(h + ' do') + ''.join(self.s(x, ind + '    ') for x in blk(n['body'])) + P('end')
        if t == 'AstStatTypeAlias': return ''
        raise Exception('stat ' + str(t))

    def e_ind(self, x, ind):
        # nested functions need the current indentation
        if nt(x) == 'AstExprFunction': return self.func(x, None, ind)
        return self.e(x)


# ------------------------------------------------- function-level wrapper
class FuncLinearizer:
    def __init__(self, pr, fn):
        self.pr, self.fn = pr, fn
    def render(self, ind):
        return ''.join(self.pr.s(x, ind) for x in blk(self.fn['body']))


# ------------------------------------------- concrete evaluation of IIFEs
class _Ret(Exception):
    def __init__(self, v): self.v = v
class _Brk(Exception): pass
class _Cont(Exception): pass
class _NoEval(Exception): pass

def const_iife(call):
    f = call['func']
    if nt(f) == 'AstExprGroup': f = f['expr']
    args = []
    for a in call['args']:
        if nt(a) == 'AstExprConstantNumber': args.append(a['value'])
        elif nt(a) == 'AstExprUnary' and a['op'] == 'Minus' and nt(a['expr']) == 'AstExprConstantNumber': args.append(-a['expr']['value'])
        else: return None
    env = {}
    for i, p in enumerate(f['args']): env[lkey(p)] = args[i] if i < len(args) else None
    steps = [0]
    def ev(x):
        t = nt(x)
        if t == 'AstExprConstantNumber': return x['value']
        if t == 'AstExprConstantBool': return x['value']
        if t == 'AstExprConstantNil': return None
        if t == 'AstExprGroup': return ev(x['expr'])
        if t == 'AstExprLocal':
            k = lkey(x['local'])
            if k not in env: raise _NoEval()
            return env[k]
        if t == 'AstExprUnary':
            v = ev(x['expr'])
            if x['op'] == 'Minus': return -v
            if x['op'] == 'Not': return not truthy(v)
            raise _NoEval()
        if t == 'AstExprBinary':
            op = x['op']
            if op == 'And':
                a = ev(x['left']); return ev(x['right']) if truthy(a) else a
            if op == 'Or':
                a = ev(x['left']); return a if truthy(a) else ev(x['right'])
            a = ev(x['left']); b = ev(x['right'])
            if not all(isinstance(z, (int, float)) and not isinstance(z, bool) for z in (a, b)):
                if op == 'CompareEq': return a == b
                if op == 'CompareNe': return a != b
                raise _NoEval()
            import math
            return {'Add': lambda: a + b, 'Sub': lambda: a - b, 'Mul': lambda: a * b,
                    'Div': lambda: a / b, 'FloorDiv': lambda: math.floor(a / b),
                    'Mod': lambda: a - math.floor(a / b) * b, 'Pow': lambda: a ** b,
                    'CompareEq': lambda: a == b, 'CompareNe': lambda: a != b,
                    'CompareLt': lambda: a < b, 'CompareLe': lambda: a <= b,
                    'CompareGt': lambda: a > b, 'CompareGe': lambda: a >= b}.get(op, lambda: (_ for _ in ()).throw(_NoEval()))()
        if t == 'AstExprIfElse':
            return ev(x['trueExpr']) if truthy(ev(x['condition'])) else ev(x['falseExpr'])
        raise _NoEval()
    def run(stmts):
        for st in stmts:
            steps[0] += 1
            if steps[0] > 200000: raise _NoEval()
            t = nt(st)
            if t == 'AstStatLocal':
                vals = [ev(v) for v in st['values']]
                for i, v in enumerate(st['vars']): env[lkey(v)] = vals[i] if i < len(vals) else None
            elif t == 'AstStatAssign':
                vals = [ev(v) for v in st['values']]
                for i, v in enumerate(st['vars']):
                    if nt(v) != 'AstExprLocal': raise _NoEval()
                    env[lkey(v['local'])] = vals[i] if i < len(vals) else None
            elif t == 'AstStatCompoundAssign':
                raise _NoEval()
            elif t == 'AstStatIf':
                if truthy(ev(st['condition'])): run(blk(st['thenbody']))
                elif st.get('elsebody') is not None: run(blk(st['elsebody']))
            elif t == 'AstStatRepeat':
                while True:
                    try: run(blk(st['body']))
                    except _Cont: pass
                    except _Brk: break
                    if truthy(ev(st['condition'])): break
            elif t == 'AstStatWhile':
                while truthy(ev(st['condition'])):
                    try: run(blk(st['body']))
                    except _Cont: pass
                    except _Brk: break
            elif t == 'AstStatContinue': raise _Cont()
            elif t == 'AstStatBreak': raise _Brk()
            elif t == 'AstStatReturn':
                if len(st['list']) != 1: raise _NoEval()
                raise _Ret(ev(st['list'][0]))
            elif t == 'AstStatBlock': run(st['body'])
            else: raise _NoEval()
    try:
        run(blk(f['body']))
    except _Ret as r:
        return r.v if isinstance(r.v, (int, float)) and not isinstance(r.v, bool) else None
    except (_NoEval, _Brk, _Cont, RecursionError, ZeroDivisionError, OverflowError):
        return None
    return None


# ---------------------------------------------------- state-machine core
class Unknown: pass
UNK = Unknown()

class Fallback(Exception): pass

def assigns_var(node, key):
    found = [False]
    def f(x):
        if nt(x) == 'AstStatAssign':
            for v in x['vars']:
                if nt(v) == 'AstExprLocal' and lkey(v['local']) == key: found[0] = True
        if nt(x) == 'AstStatCompoundAssign':
            v = x['var']
            if nt(v) == 'AstExprLocal' and lkey(v['local']) == key: found[0] = True
    walk_nofunc(node, f)
    return found[0]

def assigned_locals(node):
    ks = set()
    def f(x):
        if nt(x) == 'AstStatAssign':
            for v in x['vars']:
                if nt(v) == 'AstExprLocal': ks.add(lkey(v['local']))
        if nt(x) == 'AstStatCompoundAssign' and nt(x['var']) == 'AstExprLocal': ks.add(lkey(x['var']['local']))
    walk_nofunc(node, f)
    return ks

def has_loop_ctrl(stmts):
    """does the statement list contain continue/break bound to the *enclosing* loop?"""
    found = [False]
    def f(x):
        t = nt(x)
        if t in ('AstStatWhile', 'AstStatRepeat', 'AstStatFor', 'AstStatForIn', 'AstExprFunction'): return False
        if t in ('AstStatContinue', 'AstStatBreak'): found[0] = True
    for s in stmts: walk(s, f)
    return found[0]


class LoopLinearizer:
    MAXSTATES = 20000

    @staticmethod
    def try_make(pr, loop):
        key = LoopLinearizer.find_loopvar(loop)
        if key is None: return None
        lin = LoopLinearizer(pr, loop, key)
        try:
            lin.run()
        except Fallback as ex:
            sys.stderr.write('fallback at line %d: %s\n' % (line_of(loop), ex))
            return None
        return lin

    @staticmethod
    def find_loopvar(loop):
        # loopvar: local compared with numeric constants in an if-condition at the
        # top of the loop body, and assigned numeric constants inside the loop.
        body = blk(loop['body'])
        cnt = defaultdict(int); decl = {}
        def f(x):
            if nt(x) == 'AstExprBinary' and x['op'].startswith('Compare'):
                a, b = x['left'], x['right']
                if nt(a) == 'AstExprLocal' and nt(b) == 'AstExprConstantNumber':
                    cnt[lkey(a['local'])] += 1; decl[lkey(a['local'])] = a['local']
        for s in body[:3]:
            if nt(s) == 'AstStatIf': walk_nofunc(s['condition'], f)
        c = loop.get('condition')
        if c is not None: walk_nofunc(c, f)
        if not cnt: return None
        key = max(cnt, key=lambda k: cnt[k])
        # need many comparisons overall to be a dispatcher
        total = [0]
        def g(x):
            if nt(x) == 'AstExprBinary' and x['op'].startswith('Compare'):
                a, b = x['left'], x['right']
                if nt(a) == 'AstExprLocal' and lkey(a['local']) == key and nt(b) == 'AstExprConstantNumber':
                    total[0] += 1
        walk_nofunc(loop['body'], g)
        if total[0] < 2 or not assigns_var(loop['body'], key): return None
        return key

    def __init__(self, pr, loop, key):
        self.pr, self.loop, self.key = pr, loop, key
        self.blocks = {}       # state -> tree
        self.entry = None
        self.exit_used = False
        self.dynamic = False

    # 3-valued evaluation -----------------------------------------
    def ev(self, x, env):
        t = nt(x)
        if t == 'AstExprConstantNumber': return x['value']
        if t == 'AstExprConstantBool': return x['value']
        if t == 'AstExprConstantNil': return None
        if t == 'AstExprGroup': return self.ev(x['expr'], env)
        if t == 'AstExprLocal':
            return env.get(lkey(x['local']), UNK)
        if t == 'AstExprUnary' and x['op'] == 'Not':
            v = self.ev(x['expr'], env)
            return UNK if v is UNK else (not truthy(v))
        if t == 'AstExprUnary' and x['op'] == 'Minus':
            v = self.ev(x['expr'], env)
            return UNK if v is UNK or not isinstance(v, (int, float)) else -v
        if t == 'AstExprBinary':
            op = x['op']
            if op == 'And':
                a = self.ev(x['left'], env)
                if a is not UNK and not truthy(a): return a
                b = self.ev(x['right'], env)
                if a is UNK:
                    return False if (b is not UNK and not truthy(b)) else UNK
                return b
            if op == 'Or':
                a = self.ev(x['left'], env)
                if a is not UNK and truthy(a): return a
                b = self.ev(x['right'], env)
                if a is UNK:
                    return True if (b is not UNK and truthy(b) and b is True) else UNK
                return b
            a = self.ev(x['left'], env); b = self.ev(x['right'], env)
            if a is UNK or b is UNK: return UNK
            try:
                if op == 'CompareEq': return a == b
                if op == 'CompareNe': return a != b
                if op == 'CompareLt': return a < b
                if op == 'CompareLe': return a <= b
                if op == 'CompareGt': return a > b
                if op == 'CompareGe': return a >= b
                if op == 'Add': return a + b
                if op == 'Sub': return a - b
            except TypeError:
                return UNK
            return UNK
        if t == 'AstExprIfElse':
            c = self.ev(x['condition'], env)
            if c is UNK: return UNK
            return self.ev(x['trueExpr'] if truthy(c) else x['falseExpr'], env)
        return UNK

    def mentions_loopvar(self, x):
        found = [False]
        def f(y):
            if nt(y) == 'AstExprLocal' and lkey(y['local']) == self.key: found[0] = True
        walk_nofunc(x, f)
        return found[0]

    # symbolic execution -------------------------------------------
    # continuation stack frames: ('blk', stmts, i, 'main'|'sub') | ('iloop', stmts, i, loopnode, iters)
    def run(self):
        # the loop is entered with whatever value the loopvar has: we compute it from
        # the statements preceding the loop (done by caller via env), but simpler:
        # find entry by scanning the parent — not available here, so we derive entry
        # states as: all constants assigned to loopvar that are never targets? Instead,
        # caller passes env via self.pre_env (set by BlockScanner). Fallback: dynamic.
        pass

    def body_locals(self, loop):
        ks = []
        def f(x):
            if nt(x) == 'AstStatLocal':
                for v in x['vars']: ks.append(lkey(v))
        walk_nofunc(loop['body'], f)
        return ks

    def fresh_env(self, v, loop):
        env = {k: None for k in self.body_locals(loop)}
        env[self.key] = v
        return env

    def linearize(self, entry_env):
        self.entry_env = entry_env
        v0 = entry_env.get(self.key, UNK)
        if v0 is UNK: raise Fallback('unknown entry state')
        self.entry = v0
        self.pending = {}   # composite key -> stack
        work = [v0]; seen = set()
        while work:
            s = work.pop()
            if s in seen: continue
            seen.add(s)
            if len(seen) > self.MAXSTATES: raise Fallback('too many states')
            if isinstance(s, tuple):
                stack, ctl = self.pending[s]
                env = self.fresh_env(s[2], stack[-1][3]); env.update(ctl)
                tree = self.exec(stack, env, 0)
            else:
                tree = self.start_iteration(self.fresh_env(s, self.loop))
            self.blocks[s] = tree
            for g in tree_gotos(tree): work.append(g)

    def start_iteration(self, env):
        # main loop condition check at iteration start (while)
        if nt(self.loop) == 'AstStatWhile':
            c = self.ev(self.loop['condition'], env)
            if c is UNK: raise Fallback('data-dependent main while condition')
            if not truthy(c):
                self.exit_used = True
                return [('exit',)]
        return self.exec([('blk', blk(self.loop['body']), 0, 'main')], env, 0)

    def end_iteration(self, env):
        v = env.get(self.key, UNK)
        if nt(self.loop) == 'AstStatRepeat':
            c = self.ev(self.loop['condition'], env)
            if c is UNK: raise Fallback('data-dependent repeat condition')
            if truthy(c):
                self.exit_used = True
                return [('exit',)]
        else:
            c = self.ev(self.loop['condition'], env)
            if c is UNK: raise Fallback('data-dependent while condition')
            if not truthy(c):
                self.exit_used = True
                return [('exit',)]
        if v is UNK: raise Fallback('unknown next state')
        return [('goto', v)]

    def exec(self, stack, env, depth):
        if depth > 400: raise Fallback('path too deep')
        out = []
        stack = list(stack)
        env = dict(env)
        while True:
            if not stack:
                raise Fallback('fell off stack')
            fr = stack[-1]
            kind = fr[0]
            stmts, i = fr[1], fr[2]
            if i >= len(stmts):
                stack.pop()
                if kind == 'blk' and fr[3] == 'main':
                    return out + self.end_iteration(env)
                if kind == 'blk':
                    continue
                if kind == 'iloop':
                    r = self.iloop_next(stack, fr, env)
                    if r is not None: return out + r
                    continue
            st = stmts[i]
            stack[-1] = fr[:2] + (i + 1,) + fr[3:]
            t = nt(st)
            if t == 'AstStatIf':
                c = self.ev(st['condition'], env)
                if c is not UNK:
                    br = st['thenbody'] if truthy(c) else st.get('elsebody')
                    if br is not None:
                        stack.append(('blk', blk(br), 0, 'sub'))
                    continue
                touches = assigns_var(st, self.key) or has_loop_ctrl(blk(st['thenbody']) + blk(st.get('elsebody')))
                if not touches:
                    out.append(('stmt', st)); continue
                # fork
                thenst = list(stack) + [('blk', blk(st['thenbody']), 0, 'sub')]
                elsest = list(stack) + ([('blk', blk(st.get('elsebody')), 0, 'sub')] if st.get('elsebody') is not None else [])
                a = self.exec(thenst, env, depth + 1)
                b = self.exec(elsest, env, depth + 1)
                return out + [('if', st['condition'], a, b)]
            if t == 'AstStatAssign' and len(st['vars']) == 1 and nt(st['vars'][0]) == 'AstExprLocal' and lkey(st['vars'][0]['local']) == self.key:
                val = st['values'][0]
                v = self.ev(val, env)
                if v is not UNK:
                    env[self.key] = v; continue
                if nt(val) == 'AstExprIfElse':
                    e1 = dict(env); e1[self.key] = self.ev(val['trueExpr'], env)
                    e2 = dict(env); e2[self.key] = self.ev(val['falseExpr'], env)
                    if e1[self.key] is UNK or e2[self.key] is UNK: raise Fallback('ifelse state')
                    a = self.exec(stack, e1, depth + 1)
                    b = self.exec(stack, e2, depth + 1)
                    return out + [('if', val['condition'], a, b)]
                raise Fallback('dynamic state assignment line %d' % line_of(st))
            if t == 'AstStatLocal':
                for k, var in enumerate(st['vars']):
                    vals = st['values']
                    v = self.ev(vals[k], env) if k < len(vals) else None
                    env[lkey(var)] = v
                out.append(('stmt', st)); continue
            if t == 'AstStatAssign':
                vals = st['values']
                same = len(vals) == len(st['vars'])
                newv = [self.ev(vals[k], env) if same else UNK for k in range(len(st['vars']))]
                keep_vars, keep_vals = [], []
                for k, var in enumerate(st['vars']):
                    if nt(var) == 'AstExprLocal':
                        if lkey(var['local']) == self.key:
                            if newv[k] is UNK: raise Fallback('dynamic multi state assignment line %d' % line_of(st))
                            continue
                    keep_vars.append(var)
                    if same: keep_vals.append(vals[k])
                for k, var in enumerate(st['vars']):
                    if nt(var) == 'AstExprLocal':
                        env[lkey(var['local'])] = newv[k]
                if len(keep_vars) != len(st['vars']):
                    if keep_vars:
                        out.append(('stmt', dict(st, vars=keep_vars, values=keep_vals)))
                    continue
                out.append(('stmt', st)); continue
            if t == 'AstStatContinue':
                # pop to innermost loop frame
                while stack and stack[-1][0] == 'blk' and stack[-1][3] != 'main':
                    stack.pop()
                top = stack[-1]
                if top[0] == 'blk':  # main
                    return out + self.end_iteration(env)
                fr2 = stack.pop()
                r = self.iloop_next(stack, fr2, env)
                if r is not None: return out + r
                continue
            if t == 'AstStatBreak':
                while stack and stack[-1][0] == 'blk' and stack[-1][3] != 'main':
                    stack.pop()
                top = stack[-1]
                if top[0] == 'blk':
                    self.exit_used = True
                    return out + [('exit',)]
                stack.pop()  # leave inner loop
                continue
            if t == 'AstStatReturn':
                return out + [('stmt', st), ('term',)]
            if t in ('AstStatWhile', 'AstStatRepeat') and (assigns_var(st, self.key) or self.control_loop(st)):
                stack.append(('iloop', blk(st['body']), 0, st, 0))
                if t == 'AstStatWhile':
                    c = self.ev(st['condition'], env)
                    if c is UNK: raise Fallback('inner while cond')
                    if not truthy(c): stack.pop()
                continue
            if t == 'AstStatBlock':
                stack.append(('blk', st['body'], 0, 'sub')); continue
            if t in ('AstStatFor', 'AstStatForIn', 'AstStatWhile', 'AstStatRepeat'):
                if assigns_var(st, self.key): raise Fallback('loop with state')
            # verbatim statement: forget what we knew about locals it may assign
            for k in assigned_locals(st): env[k] = UNK
            out.append(('stmt', st))

    def control_loop(self, loop):
        """a loop whose condition only reads locals that the body assigns numeric
        constants to (flattening artefact like `repeat ... v28 = 3175 until v28 ~= 3097`)"""
        cl = set()
        ok = [True]
        def f(y):
            if nt(y) == 'AstExprLocal': cl.add(lkey(y['local']))
            if nt(y) in ('AstExprCall', 'AstExprIndexExpr', 'AstExprIndexName', 'AstExprGlobal', 'AstExprVarargs'): ok[0] = False
        walk_nofunc(loop['condition'], f)
        if not ok[0] or not cl: return False
        for k in cl:
            rhs = []
            def g(x):
                if nt(x) == 'AstStatAssign':
                    for i, var in enumerate(x['vars']):
                        if nt(var) == 'AstExprLocal' and lkey(var['local']) == k:
                            rhs.append(x['values'][i] if i < len(x['values']) and len(x['values']) == len(x['vars']) else None)
            walk_nofunc(loop['body'], g)
            if not rhs: return False
            for r in rhs:
                if r is None: return False
                if nt(r) == 'AstExprConstantNumber': continue
                if nt(r) == 'AstExprIfElse' and nt(r['trueExpr']) == 'AstExprConstantNumber' and nt(r['falseExpr']) == 'AstExprConstantNumber': continue
                return False
        return True

    def iloop_next(self, stack, fr, env):
        """end of an inner symbolic loop iteration. Returns None if the loop exits
        (frame already popped by caller), else a tree [('goto', composite)]."""
        loop = fr[3]
        c = self.ev(loop['condition'], env)
        if c is UNK: raise Fallback('inner loop cond line %d' % line_of(loop))
        exits = truthy(c) if nt(loop) == 'AstStatRepeat' else not truthy(c)
        if exits: return None
        ctl = {}
        def f(y):
            if nt(y) == 'AstExprLocal': ctl[lkey(y['local'])] = env.get(lkey(y['local']), UNK)
        walk_nofunc(loop['condition'], f)
        ctl[self.key] = env.get(self.key, UNK)
        if any(v is UNK for v in ctl.values()): raise Fallback('unknown control value in inner loop')
        v = ctl[self.key]
        st = list(stack) + [('iloop', blk(loop['body']), 0, loop, 0)]
        sig = tuple((f[0], id(f[1]), f[2]) for f in st) + tuple(sorted(ctl.items(), key=lambda kv: kv[0]))
        key = ('I', sig, v, line_of(loop))
        self.pending[key] = (st, ctl)
        return [('goto', key)]

    # rendering ------------------------------------------------------
    def render(self, ind):
        preds = defaultdict(int)
        preds[self.entry] += 1
        for s, tr in self.blocks.items():
            for g in tree_gotos(tr): preds[g] += 1
        inline = {s for s in self.blocks if preds[s] == 1 and s != self.entry}
        # avoid inlining into itself cycles: a state inlined only if not reachable
        # from itself through inlined-only chain
        self.inline = inline
        out = ''
        emitted = set()
        # valueless `local a, b` at the top level of the loop body: hoist once
        self.hoisted = set(); names = []
        for st in blk(self.loop['body']):
            if nt(st) == 'AstStatLocal' and not st['values']:
                for v in st['vars']:
                    if lkey(v) not in self.hoisted: self.hoisted.add(lkey(v)); names.append(self.pr.lname(v))
        if names: out += ind + 'local ' + ', '.join(names) + '\n'
        order = [self.entry] + sorted((s for s in self.blocks if s not in inline and s != self.entry), key=label)
        lab = label
        for s in order:
            out += ind + '::' + lab(s) + '::\n'
            out += self.render_tree(self.blocks[s], ind + '    ', {s})
        if self.exit_used:
            out += ind + '::EXIT_%d::\n' % line_of(self.loop)
        return out

    def render_tree(self, tree, ind, stack):
        out = ''
        for it in tree:
            k = it[0]
            if k == 'stmt':
                st = it[1]
                if nt(st) == 'AstStatLocal' and not st['values'] and all(lkey(v) in self.hoisted for v in st['vars']):
                    continue
                if not is_noise(st): out += self.pr.s(st, ind)
            elif k == 'goto':
                g = it[1]
                if g in self.inline and g not in stack:
                    out += self.render_tree(self.blocks[g], ind, stack | {g})
                else:
                    out += ind + 'goto ' + label(g) + '\n'
            elif k == 'exit':
                out += ind + 'goto EXIT_%d\n' % line_of(self.loop)
            elif k == 'term':
                pass
            elif k == 'if':
                out += ind + 'if ' + self.pr.e(it[1]) + ' then\n'
                out += self.render_tree(it[2], ind + '    ', stack)
                out += ind + 'else\n'
                out += self.render_tree(it[3], ind + '    ', stack)
                out += ind + 'end\n'
        return out


NOISE = set()     # local keys whose decls are state-machine noise
LOOPVARS = set()  # detected dispatch variables

def is_noise(st):
    t = nt(st)
    if t == 'AstStatLocal':
        return all(lkey(v) in NOISE or lkey(v) in LOOPVARS for v in st['vars']) and \
            all(nt(x) in ('AstExprConstantNumber', 'AstExprLocal') for x in st['values'])
    if t == 'AstStatAssign' and len(st['vars']) == 1 and nt(st['vars'][0]) == 'AstExprLocal':
        k = lkey(st['vars'][0]['local'])
        return k in LOOPVARS
    return False

_LABELS = {}
def label(s):
    if not isinstance(s, tuple): return 'S%s' % lnum(s)
    if s not in _LABELS:
        base = 'L%d_%s' % (s[3], lnum(s[2])); name = base; n = 1
        used = set(_LABELS.values())
        while name in used: n += 1; name = '%s_%d' % (base, n)
        _LABELS[s] = name
    return _LABELS[s]

def truthy(v): return not (v is None or v is False)

def tree_gotos(tree):
    r = []
    for it in tree:
        if it[0] == 'goto': r.append(it[1])
        elif it[0] == 'if': r += tree_gotos(it[2]) + tree_gotos(it[3])
    return r


# Block-level driver: we need the entry state of each dispatch loop, which comes
# from statements preceding it in the same block. Patch Printer.s for blocks.
_orig_s = Printer.s
def _s(self, n, ind):
    return _orig_s(self, n, ind)

def render_block(pr, stmts, ind):
    env = {}
    out = ''
    for st in stmts:
        t = nt(st)
        if t in ('AstStatWhile', 'AstStatRepeat'):
            key = LoopLinearizer.find_loopvar(st)
            if key is not None:
                lin = LoopLinearizer(pr, st, key)
                try:
                    lin.linearize(env)
                    LOOPVARS.add(key)
                    out += lin.render(ind)
                    env = {}
                    continue
                except Fallback as ex:
                    sys.stderr.write('fallback at line %d: %s\n' % (line_of(st), ex))
            out += _orig_s(pr, st, ind) if t != 'AstStatWhile' and t != 'AstStatRepeat' else plain_loop(pr, st, ind)
            env = {}
            continue
        # track constants assigned to locals
        if t == 'AstStatLocal':
            for k, var in enumerate(st['vars']):
                vals = st['values']
                env[lkey(var)] = const_of(vals[k], env) if k < len(vals) else None
        elif t == 'AstStatAssign':
            for k, var in enumerate(st['vars']):
                if nt(var) == 'AstExprLocal':
                    env[lkey(var['local'])] = const_of(st['values'][k], env) if k < len(st['values']) else UNK
        if not is_noise(st): out += _orig_s(pr, st, ind)
    return out

def const_of(x, env):
    t = nt(x)
    if t == 'AstExprConstantNumber': return x['value']
    if t == 'AstExprLocal': return env.get(lkey(x['local']), UNK)
    return UNK

def plain_loop(pr, n, ind):
    P = lambda x: ind + x + '\n'
    if nt(n) == 'AstStatWhile':
        return P('while ' + pr.e(n['condition']) + ' do') + render_block(pr, blk(n['body']), ind + '    ') + P('end')
    return P('repeat') + render_block(pr, blk(n['body']), ind + '    ') + P('until ' + pr.e(n['condition']))

# route every statement list through render_block
def _patched_s(self, n, ind):
    t = nt(n)
    P = lambda x: ind + x + '\n'
    if t == 'AstStatBlock':
        return P('do') + render_block(self, n['body'], ind + '    ') + P('end')
    if t == 'AstStatIf':
        out = P('if ' + self.e(n['condition']) + ' then')
        out += render_block(self, blk(n['thenbody']), ind + '    ')
        eb = n.get('elsebody')
        while eb is not None and nt(eb) == 'AstStatIf':
            out += P('elseif ' + self.e(eb['condition']) + ' then')
            out += render_block(self, blk(eb['thenbody']), ind + '    ')
            eb = eb.get('elsebody')
        if eb is not None:
            out += P('else') + render_block(self, blk(eb), ind + '    ')
        return out + P('end')
    if t in ('AstStatWhile', 'AstStatRepeat'):
        return plain_loop(self, n, ind)
    if t == 'AstStatFor':
        h = 'for ' + self.lname(n['var']) + ' = ' + self.e(n['from']) + ', ' + self.e(n['to'])
        if n.get('step') is not None: h += ', ' + self.e(n['step'])
        return P(h + ' do') + render_block(self, blk(n['body']), ind + '    ') + P('end')
    if t == 'AstStatForIn':
        h = 'for ' + ', '.join(self.lname(v) for v in n['vars']) + ' in ' + ', '.join(self.e(x) for x in n['values'])
        return P(h + ' do') + render_block(self, blk(n['body']), ind + '    ') + P('end')
    return _orig_s(self, n, ind)
Printer.s = _patched_s
FuncLinearizer.render = lambda self, ind: render_block(self.pr, blk(self.fn['body']), ind)


def load_ast(path, ast_path=None):
    if ast_path and os.path.exists(ast_path):
        return json.load(open(ast_path))
    exe = os.environ.get('LUAU_AST', 'luau-ast')
    r = subprocess.run([exe, path], capture_output=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr.decode(errors='replace')); sys.exit(1)
    d = json.loads(r.stdout.decode('utf-8', errors='surrogateescape'))
    if ast_path: json.dump(d, open(ast_path, 'w'))
    return d


def compute_state_temps(root):
    """locals whose every use is `<local> = <it>` (state temporaries) plus
    detected loop variables: their declarations/assignments are noise."""
    uses = defaultdict(list)
    def f(x):
        if nt(x) in ('AstStatAssign',) and len(x['vars']) == 1 and len(x['values']) == 1 \
                and nt(x['vars'][0]) == 'AstExprLocal' and nt(x['values'][0]) == 'AstExprLocal':
            uses[lkey(x['values'][0]['local'])].append('st')
            uses[lkey(x['vars'][0]['local'])].append('lhs')
            return False
        if nt(x) == 'AstExprLocal':
            uses[lkey(x['local'])].append('use')
    walk(root, f)
    return {k for k, u in uses.items() if u and all(z == 'st' for z in u)}

def main():
    a = sys.argv[1:]
    src = a[0]; ast = None; fnline = None; out = None
    i = 1
    while i < len(a):
        if a[i] == '--ast': ast = a[i+1]; i += 2
        elif a[i] == '--fn': fnline = int(a[i+1]); i += 2
        elif a[i] == '--out': out = a[i+1]; i += 2
        else: raise SystemExit('bad arg ' + a[i])
    d = load_ast(src, ast)
    pr = Printer()
    NOISE.update(compute_state_temps(d['root']))
    if fnline:
        target = []
        def f(x):
            if nt(x) == 'AstExprFunction' and line_of(x) == fnline and not target: target.append(x)
        walk(d['root'], f)
        if not target: raise SystemExit('no function at line %d' % fnline)
        text = pr.func(target[0])
    else:
        text = render_block(pr, d['root']['body'], '')
    if out: open(out, 'w', encoding='utf-8', errors='surrogateescape').write(text)
    else: sys.stdout.write(text)

if __name__ == '__main__':
    main()
