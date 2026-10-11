"""peval.py — partial evaluation of the VM executor w.r.t. one instruction.

The executor t[119] is an interpreter loop:
    while true do
        local v16 = v1[sum_2]; local v17 = v16[v14]
        <decision tree on v17 with handlers>
        sum_2 = sum_2 + 1
    end
Given a concrete instruction (static operands, constants, pc, stack depth) we
symbolically execute that loop body once. Everything that depends only on the
program is computed; everything that depends on runtime state (registers,
accumulator, argument stack, upvalues, globals, varargs) is emitted as
*residual IR*. The result is the instruction's meaning in a small IR:

expressions (tuples)
  ('K', v)              constant (int/float/bool/None/bytes)
  ('R', n) / ('RX', e)  register (static / dynamic index)
  ('ACC',)              accumulator
  ('S', k) / ('SX', e)  argument-stack slot (static / dynamic index)
  ('SP',)               argument-stack depth when not static
  ('TOP',)              multret top register
  ('U', i)              upvalue
  ('ENV',)              environment table
  ('VA', e) ('NVA',)    vararg i / vararg count
  ('RET', e)            multret buffer slot
  ('T', n)              temporary
  ('IDX', o, k)         index
  ('CALL', f, [args])   call (single result when used as expression)
  ('BIN', op, a, b) ('UN', op, a)
  ('NEWT', [items])     table constructor
  ('CLOSURE', proto, [captures])
  ('FN', name)          known library helper (unpack, pack, create, select, ...)
  ('PACKN', e)          `bhv(v112, e)`: store results of multi-value expression e
                        into the RET buffer, evaluates to their count
statements
  ('SET', lhs, rhs) ('LOCAL', T, rhs) ('EXPR', e)
  ('IF', cond, [then], [else]) ('FOR', T, a, b, step, [body])
  ('GOTO', pc) ('GOTOX', e) ('RETURN', [exprs]) ('RAW', text)
"""
import flat
from flat import nt, blk, lkey, walk

class Unsupported(Exception): pass

# ------------------------------------------------------------ static objects
class SObj:
    kind = 'obj'
    def index(self, pe, k): raise Unsupported('index %s' % self.kind)

class SList(SObj):
    """static Lua array (operand arrays, index tables, upvalue descriptors)"""
    kind = 'list'
    def __init__(self, items): self.items = list(items)
    def index(self, pe, k):
        if not isinstance(k, (int, float)): raise Unsupported('list index %r' % (k,))
        k = int(k)
        if 1 <= k <= len(self.items): return wrap(self.items[k - 1])
        return None
    def length(self): return len(self.items)

def wrap(v):
    if isinstance(v, list): return SList(v)
    if isinstance(v, dict):
        n = 0
        while (n + 1) in v: n += 1
        if n == len(v): return SList([v[i] for i in range(1, n + 1)])
        raise Unsupported('non-array static table')
    return v

class SInstr(SObj):
    kind = 'instr'
    def __init__(self, rec): self.rec = rec
    def index(self, pe, k):
        v = self.rec.get(int(k)) if isinstance(k, (int, float)) else None
        return wrap(v)

class SCode(SObj):
    kind = 'code'
    def __init__(self, proto): self.proto = proto
    def index(self, pe, k):
        r = self.proto.code.get(int(k))
        return SInstr(r) if r is not None else None

class SConsts(SObj):
    kind = 'consts'
    def __init__(self, proto): self.proto = proto
    def index(self, pe, k):
        return ('CONST', self.proto.consts.get(int(k)))

class SProtos(SObj):
    kind = 'protos'
    def __init__(self, proto): self.proto = proto
    def index(self, pe, k):
        p = self.proto.protos.get(int(k))
        if p is None: raise Unsupported('proto %r' % k)
        return SProto(p)

class SProto(SObj):
    kind = 'proto'
    def __init__(self, p): self.p = p
    def index(self, pe, k):
        if k == 2693:
            return SList([self.p.upvals[i] for i in sorted(self.p.upvals)])
        raise Unsupported('proto field %r' % k)

class SIdx(SObj):
    kind = 'idx'
    def __init__(self, proto): self.proto = proto
    def index(self, pe, k):
        v = self.proto.idx.get(int(k))
        return SList(v) if v is not None else None

class SFn(SObj):
    """known function value"""
    kind = 'fn'
    def __init__(self, name): self.name = name

class SDyn(SObj):
    """a runtime container (registers, stack, env, upvalues, retbuf, varargs)"""
    def __init__(self, kind): self.kind = kind

class STTable(SObj):
    """the f1-local `t` table: t[1] runtime constants, t[N] helpers"""
    kind = 't'
    def __init__(self, consts): self.C = consts
    def index(self, pe, k):
        return STPath(self, [int(k)]).maybe()

class STPath(SObj):
    kind = 'tpath'
    def __init__(self, root, path): self.root, self.path = root, path
    def index(self, pe, k):
        return STPath(self.root, self.path + [int(k)]).maybe()
    def maybe(self):
        key = 't' + ''.join('[%d]' % p for p in self.path)
        if key in self.root.C: return self.root.C[key]
        if len(self.path) == 1 and self.path[0] in (7, 14, 117, 118, 119, 6, 27, 29, 30, 19, 8, 9, 10): return self.resolve()
        if key in TFUNCS or (len(self.path) == 2 and self.path[0] == 15): return self.resolve()
        return self
    def resolve(self):
        key = 't' + ''.join('[%d]' % p for p in self.path)
        if key in self.root.C: return self.root.C[key]
        if key in TFUNCS: return SFn(TFUNCS[key])
        if len(self.path) == 2 and self.path[0] == 15: return SFn('native:%d' % self.path[1])
        if len(self.path) == 1:
            n = self.path[0]
            H = {7: 'unpack', 14: 'create', 117: 'pack', 118: 'shared118', 119: 'closure', 6: 'unpack',
                 27: 'bc_byte', 29: 'bc_varint', 30: 'bc_zigzag', 19: 'BYTECODE', 8: 'bxor', 9: 'lshift', 10: 'rshift'}
            if n in H: return SFn(H[n])
        raise Unsupported('t path %s' % key)

class SMarks(SObj):
    """v132: stack of saved argument-stack marks (static)"""
    kind = 'marks'
    def set(self, cur, k, v):
        cur = list(cur)
        while len(cur) < k: cur.append(None)
        cur[k - 1] = v
        return tuple(cur)

class SBuild(SObj):
    """table being filled by the handler (closure capture lists)"""
    kind = 'build'
    def __init__(self): self.items = {}
    def index(self, pe, k): return self.items.get(k)

class SBytecode(SObj):
    kind = 'bytecode'

# runtime function slots in t[1] (identified from their initialisation code)
TFUNCS = {'t[1][21][7]': 'band', 't[1][39][1]': 'bor', 't[1][15][4]': 'bnot', 't[1][15][5]': 'string.byte'}

class Box:
    """mutable static local cell"""
    def __init__(self, v): self.v = v

DYNAMIC = object()

def is_static(v):
    return not isinstance(v, tuple) or v[0] == 'CONST'

def sval(v):
    """static python value of v (for CONST markers returns the constant)"""
    if isinstance(v, tuple) and v[0] == 'CONST': return v[1]
    if isinstance(v, STPath): return v.resolve()
    return v

def to_ir(v):
    """turn a value into an IR expression"""
    if isinstance(v, STPath): v = v.resolve()
    if isinstance(v, tuple):
        if v[0] == 'CONST': return ('K', v[1])
        return v
    if v is None or isinstance(v, (bool, int, float, bytes)): return ('K', v)
    if isinstance(v, SFn): return ('FN', v.name)
    if isinstance(v, SDyn): return ('CONTAINER', v.kind)
    if isinstance(v, SConsts): return ('CONTAINER', 'consts')
    if isinstance(v, SCode): return ('CONTAINER', 'code')
    if isinstance(v, SList): return ('NEWT', [to_ir(x) for x in v.items])
    if isinstance(v, SBuild):
        n = max(v.items) if v.items else 0
        return ('CAPS', [to_ir(v.items.get(i)) for i in range(1, n + 1)])
    raise Unsupported('to_ir %r' % (v,))

BINOPS = {'Add': '+', 'Sub': '-', 'Mul': '*', 'Div': '/', 'FloorDiv': '//', 'Mod': '%', 'Pow': '^',
          'Concat': '..', 'CompareEq': '==', 'CompareNe': '~=', 'CompareLt': '<', 'CompareLe': '<=',
          'CompareGt': '>', 'CompareGe': '>=', 'And': 'and', 'Or': 'or'}

def fold(op, a, b):
    import math
    try:
        if op == '+': return a + b
        if op == '-': return a - b
        if op == '*': return a * b
        if op == '/': return a / b
        if op == '%': return a - math.floor(a / b) * b
        if op == '//': return math.floor(a / b)
        if op == '^': return a ** b
        if op == '==': return a == b
        if op == '~=': return a != b
        if op == '<': return a < b
        if op == '<=': return a <= b
        if op == '>': return a > b
        if op == '>=': return a >= b
        if op == '..': return a + b
    except Exception:
        pass
    raise Unsupported('fold %s %r %r' % (op, a, b))

def truthy(v): return not (v is None or v is False)

def mentions_mutable(e):
    """does the IR expression read mutable runtime state?"""
    if not isinstance(e, tuple): return False
    h = e[0]
    if h in ('K', 'T', 'FN', 'CONST'): return False
    if h in ('R', 'RX', 'ACC', 'S', 'SX', 'TOP', 'U', 'IDX', 'CALL', 'RET', 'VA', 'NVA', 'SP', 'PACKN'): return True
    return any(mentions_mutable(x) for x in e[1:] if isinstance(x, tuple)) or \
        any(mentions_mutable(y) for x in e[1:] if isinstance(x, list) for y in x)


class PE:
    """partial evaluator bound to the executor AST"""
    def __init__(self, root, consts):
        self.root = root
        self.TC = STTable(consts)
        self._locate()
        self.tmp = 0

    def _locate(self):
        res = []
        def f(x):
            if nt(x) == 'AstStatBlock':
                b = x['body']
                for i, st in enumerate(b):
                    if nt(st) == 'AstStatLocal' and len(st['vars']) == 1 and st['vars'][0]['name'] == 'v17' and st['values'] and nt(st['values'][0]) == 'AstExprIndexExpr' and nt(st['values'][0]['expr']) == 'AstExprLocal' and st['values'][0]['expr']['local']['name'] == 'v16':
                        res.append((x, i))
        walk(self.root, f)
        assert len(res) == 1
        self.body, i = res[0]
        self.stmts = self.body['body']
        self.start = i + 1
        self.k_v16 = lkey(self.stmts[i - 1]['vars'][0])
        self.k_v17 = lkey(self.stmts[i]['vars'][0])
        # find the enclosing executor function to map its locals by name
        names = {}
        def g(x):
            if nt(x) == 'AstLocal': names.setdefault(x['name'], set()).add(lkey(x))
        walk(self.root, g)
        self.names = names

    # ---------------------------------------------------------------
    def new_tmp(self):
        self.tmp += 1
        return ('T', self.tmp)

    def instr_env(self, proto, pc, sp, fieldmap, fkeys):
        """static environment for executing instruction at pc"""
        return {'pc': pc, 'sp': sp, 'proto': proto, 'fk': fkeys}

    def specialize(self, proto, pc, sp, bind):
        """bind: dict name -> (key) for executor locals. Returns (ir_stmts)"""
        env = {}
        ins = proto.code[pc]
        env[self.k_v16] = SInstr(ins)
        env[self.k_v17] = ins.get(bind['opkey'])
        for name, val in bind['static'].items():
            env[name] = val
        env[bind['pc']] = pc
        sp, mark, nmarks, marks, carry = sp
        for k, v in zip(bind['carry'], carry): env[k] = v
        env[bind['sp']] = sp
        env[bind['mark']] = mark
        env[bind['nmarks']] = nmarks
        env['__marks'] = marks
        self.bind = bind
        self.tsrc, self.ver = {}, {}
        self.cur_proto = proto
        self.cur_pc = pc
        return self.exec([('blk', self.stmts, self.start)], env, 0)

    # ------------------------------------------------------------ exec
    def exec(self, stack, env, depth):
        """continuation-passing symbolic execution.
        frames: ('blk', stmts, i) | ('for', stmts, i, st, a, b, c)   static unrolled
                ('rloop', stmts, i, inv)                              residual loop body"""
        if depth > 80: raise Unsupported('fork depth')
        out = []
        stack = list(stack); env = dict(env)
        while True:
            self._env = env
            if not stack:
                # end of interpreter loop body -> next instruction
                pcv = env[self.bind['pc']]
                nm = env.get(self.bind['nmarks']) or 0
                ms = (env[self.bind['sp']], env.get(self.bind['mark']), nm, tuple(env.get('__marks', ()))[:nm],
                      tuple(sval(env.get(k)) if not isinstance(env.get(k), tuple) or env.get(k)[0] == 'CONST' else env.get(k) for k in self.bind['carry']))
                if is_static(pcv) and not isinstance(pcv, tuple):
                    out.append(('NEXT', sval(pcv), ms))
                else:
                    out.append(('GOTOX', to_ir(pcv), ms))
                return out
            fr = stack[-1]
            kind, stmts, i = fr[0], fr[1], fr[2]
            if i >= len(stmts):
                stack.pop()
                if kind == 'for':
                    r = self.for_next(stack, fr, env)
                    if r is not None: stack = r
                elif kind == 'rloop':
                    self.check_inv(fr[3], env)
                    out.append(('LOOPEND',))
                    return out
                continue
            stack[-1] = (kind, stmts, i + 1) + fr[3:]
            st = stmts[i]
            t = nt(st)
            if t == 'AstStatLocal':
                vals = self.eval_list(st['values'], len(st['vars']), env, out)
                for var, v in zip(st['vars'], vals):
                    env[lkey(var)] = self.bindable(v, out)
                continue
            if t == 'AstStatAssign':
                self.assign(st, env, out)
                continue
            if t == 'AstStatCompoundAssign':
                raise Unsupported('compound assign')
            if t == 'AstStatExpr':
                v = self.ev(st['expr'], env, out)
                if isinstance(v, tuple) and v[0] in ('CALL', 'PACKN'):
                    out.append(('EXPR', v))
                continue
            if t == 'AstStatIf':
                c = self.ev(st['condition'], env, out)
                if not isinstance(c, tuple) or c[0] == 'CONST':
                    if isinstance(c, SObj) and not isinstance(c, STPath): c = True
                    br = st['thenbody'] if truthy(sval(c)) else st.get('elsebody')
                    if br is not None: stack.append(('blk', blk(br), 0))
                    continue
                els = st.get('elsebody')
                a = self.fork(stack + [('blk', blk(st['thenbody']), 0)], env, depth)
                b = self.fork(stack + ([('blk', blk(els), 0)] if els is not None else []), env, depth)
                if all(x and x[-1][0] == 'ERRPATH' for x in (a, b)): raise Unsupported('both branches fail: ' + a[-1][1])
                out.append(('IF', to_ir(c), a, b))
                return out
            if t == 'AstStatReturn':
                vals = [to_ir(v) for v in self.eval_list(st['list'], None, env, out)]
                out.append(('RETURN', vals))
                return out
            if t == 'AstStatFor':
                if nt(st['from']) == 'AstExprLocal' and self.bind['roles'].get(lkey(st['from']['local'])) == 'opencount':
                    out.append(('CLOSEUPV',))
                    continue
                a = self.ev(st['from'], env, out); b = self.ev(st['to'], env, out)
                c = self.ev(st['step'], env, out) if st.get('step') is not None else 1
                if all(not isinstance(x, (tuple, SObj)) for x in (a, b, c)):
                    if (c > 0 and a > b) or (c < 0 and a < b): continue
                    env[lkey(st['var'])] = a
                    stack.append(('for', blk(st['body']), 0, st, a, b, c))
                    continue
                T = self.new_tmp()
                self.materialize(st['body'], env, out)
                env2 = dict(env); env2[lkey(st['var'])] = T
                body = self.exec([('rloop', blk(st['body']), 0, self.inv(env))], env2, depth + 1)
                out.append(('FOR', T, to_ir(a), to_ir(b), to_ir(c), body))
                continue
            if t in ('AstStatWhile', 'AstStatRepeat'):
                self.materialize(st, env, out)
                scratch = []
                c = self.ev(st['condition'], env, scratch)
                body = self.exec([('rloop', blk(st['body']), 0, self.inv(env))], env, depth + 1)
                if t == 'AstStatWhile':
                    if not isinstance(c, tuple) and not truthy(c): continue
                    if scratch or isinstance(c, tuple):
                        out.append(('WHILE', ('K', True), scratch + [('IF', ('UN', 'not', to_ir(c)), [('BREAK',)], [])] + body))
                    else:
                        out.append(('WHILE', ('K', True), body))
                else:
                    out.append(('REPEAT', body, to_ir(c), scratch))
                continue
            if t == 'AstStatContinue':
                while stack and stack[-1][0] == 'blk': stack.pop()
                if not stack: raise Unsupported('continue outside loop')
                fr2 = stack.pop()
                if fr2[0] == 'rloop':
                    self.check_inv(fr2[3], env)
                    out.append(('CONTINUE',)); return out
                r = self.for_next(stack, fr2, env)
                if r is not None: stack = r
                continue
            if t == 'AstStatBreak':
                while stack and stack[-1][0] == 'blk': stack.pop()
                if not stack: raise Unsupported('break outside loop')
                fr2 = stack.pop()
                if fr2[0] == 'rloop':
                    self.check_inv(fr2[3], env)
                    out.append(('BREAK',)); return out
                continue      # leave static unrolled for
            if t == 'AstStatBlock':
                stack.append(('blk', st['body'], 0)); continue
            raise Unsupported('stmt %s' % t)

    def inv(self, env):
        b = self.bind
        return (env.get(b['pc']), env.get(b['sp']), env.get(b['mark']), env.get(b['nmarks']), env.get('__marks'), env.get('__bcpos')) + tuple(repr(env.get(k)) for k in b['carry'])

    def check_inv(self, inv, env):
        if self.inv(env) != inv:
            raise Unsupported('static VM state changes inside a residual loop')

    def materialize(self, node, env, out):
        """locals assigned inside a residual loop must live in temporaries"""
        ks = set()
        def f(x):
            if nt(x) == 'AstStatAssign':
                for v in x['vars']:
                    if nt(v) == 'AstExprLocal': ks.add(lkey(v['local']))
                    if nt(v) == 'AstExprGlobal': ks.add('G:' + v['global'])
        flat.walk_nofunc(node, f)
        for k in ks:
            if k in self.bind['roles']: continue
            if k not in env: continue
            cur = env[k]
            if isinstance(cur, tuple) and cur[0] == 'T': continue
            if isinstance(cur, SObj): continue
            T = self.new_tmp()
            out.append(('LOCAL', T, to_ir(cur)))
            env[k] = T

    def fork(self, stack, env, depth):
        try:
            return self.exec(stack, env, depth + 1)
        except Unsupported as ex:
            return [('ERRPATH', str(ex))]

    def for_next(self, stack, fr, env):
        _, body, _, st, a, b, c = fr
        k = lkey(st['var'])
        v = env[k] + c
        if (c > 0 and v > b) or (c < 0 and v < b): return None
        env[k] = v
        return stack + [('for', body, 0, st, a, b, c)]

    def bindable(self, v, out):
        """value to bind to a handler local: temporaries for runtime reads"""
        if isinstance(v, tuple) and v[0] not in ('CONST', 'K', 'T', 'FN') and mentions_mutable(v):
            T = self.new_tmp()
            out.append(('LOCAL', T, v))
            if v[0] in ('R', 'U', 'ACC'):
                self.tsrc[T] = (v, self.ver.get(v, 0))
            return T
        return v

    # ------------------------------------------------------------ assign
    def assign(self, st, env, out):
        # Luau order: every LHS (table, key) left to right, then every RHS value
        targets = []
        for var in st['vars']:
            t = nt(var)
            if t in ('AstExprLocal', 'AstExprGlobal'):
                targets.append(('local', var))
            elif t in ('AstExprIndexExpr', 'AstExprIndexName'):
                obj = self.ev(var['expr'], env, out)
                key = self.ev(var['index'], env, out) if t == 'AstExprIndexExpr' else var['index'].encode()
                if isinstance(obj, tuple) and mentions_mutable(obj) and len(st['vars']) > 1:
                    obj = self.bindable(obj, out)
                targets.append(('index', obj, key))
            else:
                raise Unsupported('assign target %s' % t)
        vals = self.eval_list(st['values'], len(st['vars']), env, out)
        if len(st['vars']) > 1:
            vals = [self.bindable(v, out) for v in vals]
        for tg, v in zip(targets, vals):
            if tg[0] == 'local':
                k = lkey(tg[1]['local']) if nt(tg[1]) == 'AstExprLocal' else 'G:' + tg[1]['global']
                role = self.bind['roles'].get(k)
                if role == 'acc':
                    out.append(('SET', ('ACC',), to_ir(v))); continue
                if role == 'top':
                    out.append(('SET', ('TOP',), to_ir(v))); continue
                if role in ('pc', 'sp', 'mark', 'nmarks', 'carry'):
                    env[k] = v if not (isinstance(v, tuple) and v[0] == 'CONST') else v[1]
                    continue
                if role == 'opencount':
                    continue
                if role == 'v8':
                    out.append(('SET', ('VMVAR', role), to_ir(v))); continue
                cur = env.get(k)
                if isinstance(cur, tuple) and cur[0] == 'T':
                    out.append(('SET', cur, to_ir(v))); continue
                env[k] = v
                continue
            obj, key = tg[1], tg[2]
            if isinstance(obj, STTable) and sval(key) == 20:
                env['__bcpos'] = sval(v); continue
            if isinstance(obj, SMarks):
                env['__marks'] = obj.set(env.get('__marks', ()), sval(key), sval(v)); continue
            if isinstance(obj, SBuild):
                obj.items[sval(key)] = v if not (isinstance(v, tuple) and v[0] == 'T') else v
                continue
            if isinstance(obj, SDyn) and obj.kind in ('openup', 'openlist'):
                continue        # open-upvalue bookkeeping: no observable effect (capture is by value)
            lhs = self.lvalue(obj, key)
            if lhs[0] in ("R", "U"): self.ver[lhs] = self.ver.get(lhs, 0) + 1
            out.append(('SET', lhs, to_ir(v)))

    def lvalue(self, obj, key):
        if isinstance(obj, SDyn):
            if obj.kind == 'regs':
                return ('R', int(key)) if is_static(key) and not isinstance(key, tuple) else ('RX', to_ir(key))
            if obj.kind == 'stack':
                return ('S', int(key)) if is_static(key) and not isinstance(key, tuple) else ('SX', to_ir(key))
            if obj.kind == 'env':
                return ('IDX', ('ENV',), to_ir(key))
            if obj.kind == 'upvals':
                return ('U', int(key)) if is_static(key) and not isinstance(key, tuple) else ('UX', to_ir(key))
            if obj.kind == 'retbuf':
                return ('RET', to_ir(key))
            return ('IDX', ('CONTAINER', obj.kind), to_ir(key))
        return ('IDX', to_ir(obj), to_ir(key))

    # ------------------------------------------------------------ expressions
    def eval_list(self, exprs, n, env, out):
        vals = []
        for i, x in enumerate(exprs):
            last = i == len(exprs) - 1
            v = self.ev(x, env, out, multi=last and (n is None or n > len(exprs)))
            vals.append(v)
        if n is not None:
            if len(vals) < n:
                last = vals[-1] if vals else None
                if isinstance(last, tuple) and last[0] == 'CALL' and len(exprs) > 0:
                    # multiple assignment from one call: spread via temporaries
                    Ts = [self.new_tmp() for _ in range(n - len(vals) + 1)]
                    out.append(('LOCALS', Ts, last))
                    vals = vals[:-1] + Ts
                else:
                    vals += [None] * (n - len(vals))
            vals = vals[:n]
        return vals

    def ev(self, x, env, out, multi=False):
        t = nt(x)
        if t == 'AstExprConstantNumber': return x['value'] if not float(x['value']).is_integer() else int(x['value'])
        if t == 'AstExprConstantBool': return x['value']
        if t == 'AstExprConstantNil': return None
        if t == 'AstExprConstantString': return x['value'].encode('latin1', errors='replace')
        if t == 'AstExprGroup': return self.ev(x['expr'], env, out)
        if t == 'AstExprLocal':
            k = lkey(x['local'])
            if k in env:
                v = env[k]
                if isinstance(v, str) and v == 'CONFLICT':
                    raise Unsupported('read of a carried VM register with conflicting values')
                return v
            role = self.bind['roles'].get(k)
            if role == 'acc': return ('ACC',)
            if role == 'top': return ('TOP',)
            if role == 'opencount': return 0
            if role in ('frames', 'v8'): return ('VMVAR', role)
            raise Unsupported('unknown local %s' % x['local']['name'])
        if t == 'AstExprGlobal':
            if ('G:' + x['global']) in env: return env['G:' + x['global']]
            return ('GLOBALFN', x['global'])
        if t == 'AstExprVarargs':
            raise Unsupported('varargs in handler')
        if t in ('AstExprIndexExpr', 'AstExprIndexName'):
            obj = self.ev(x['expr'], env, out)
            key = self.ev(x['index'], env, out) if t == 'AstExprIndexExpr' else x['index'].encode()
            return self.index(obj, key)
        if t == 'AstExprUnary':
            a = self.ev(x['expr'], env, out)
            op = x['op']
            if is_static(a) and not isinstance(a, SObj):
                av = sval(a)
                if op == 'Not': return not truthy(av)
                if op == 'Minus': return -av
                if op == 'Len':
                    if isinstance(av, bytes): return len(av)
            if op == 'Len' and isinstance(a, SList): return a.length()
            return ('UN', {'Not': 'not', 'Minus': '-', 'Len': '#'}[op], to_ir(a))
        if t == 'AstExprBinary':
            op = BINOPS[x['op']]
            if op in ('and', 'or'):
                a = self.ev(x['left'], env, out)
                if is_static(a) and not isinstance(a, SObj):
                    av = sval(a)
                    if op == 'and': return self.ev(x['right'], env, out) if truthy(av) else av
                    return av if truthy(av) else self.ev(x['right'], env, out)
                b = self.ev(x['right'], env, out)
                return ('BIN', op, to_ir(a), to_ir(b))
            a = self.ev(x['left'], env, out); b = self.ev(x['right'], env, out)
            if is_static(a) and is_static(b) and not isinstance(a, SObj) and not isinstance(b, SObj):
                av, bv = sval(a), sval(b)
                if isinstance(av, STPath) or isinstance(bv, STPath): raise Unsupported('tpath arith')
                if op in ('==', '~='): return fold(op, av, bv)
                if isinstance(av, (int, float)) and isinstance(bv, (int, float)) and not isinstance(av, bool) and not isinstance(bv, bool):
                    r = fold(op, av, bv)
                    return int(r) if isinstance(r, float) and r.is_integer() and op not in ('/', '^') else r
            A, B = to_ir(a), to_ir(b)
            if op in ('==', '~=') and (A == B and pure(A) or (A in self.tsrc and self.tsrc.get(A) == self.tsrc.get(B))):
                return op == '=='
            return simp(('BIN', op, A, B))
        if t == 'AstExprIfElse':
            c = self.ev(x['condition'], env, out)
            if is_static(c) and not isinstance(c, SObj):
                return self.ev(x['trueExpr'] if truthy(sval(c)) else x['falseExpr'], env, out)
            return ('IFE', to_ir(c), to_ir(self.ev(x['trueExpr'], env, out)), to_ir(self.ev(x['falseExpr'], env, out)))
        if t == 'AstExprCall':
            return self.call(x, env, out)
        if t == 'AstExprTable':
            items = []
            for it in x['items']:
                if it['kind'] in ('item', 'List'):
                    items.append(('ITEM', to_ir(self.ev(it['value'], env, out))))
                else:
                    items.append(('KV', to_ir(self.ev(it['key'], env, out)), to_ir(self.ev(it['value'], env, out))))
            return ('NEWT', items)
        if t == 'AstExprFunction':
            return self.handler_function(x, env, out)
        raise Unsupported('expr %s' % t)

    def index(self, obj, key):
        if obj is None:
            raise Unsupported('index nil (static)')
        if isinstance(obj, tuple) and obj[0] == 'CONST':
            raise Unsupported('index constant')
        if isinstance(obj, SMarks):
            m = self._env.get('__marks', ())
            k = int(sval(key))
            return m[k - 1] if 1 <= k <= len(m) else None
        if isinstance(obj, STTable) and sval(key) == 20:
            return self._env.get('__bcpos')
        if isinstance(obj, SObj) and not isinstance(obj, SDyn):
            k = sval(key)
            if isinstance(k, tuple): raise Unsupported('dynamic index into static %s' % obj.kind)
            if isinstance(obj, STPath):
                return obj.index(self, k)
            return obj.index(self, k)
        if isinstance(obj, SDyn):
            k = sval(key) if not isinstance(key, tuple) or key[0] == 'CONST' else key
            static_k = not isinstance(k, tuple)
            if obj.kind == 'regs': return ('R', int(k)) if static_k else ('RX', to_ir(k))
            if obj.kind == 'stack': return ('S', int(k)) if static_k else ('SX', to_ir(k))
            if obj.kind == 'env': return ('IDX', ('ENV',), to_ir(key))
            if obj.kind == 'upvals': return ('U', int(k)) if static_k else ('UX', to_ir(k))
            if obj.kind == 'retbuf': return ('RET', to_ir(key))
            if obj.kind == 'varargs': return ('VA', to_ir(key))
            if obj.kind == 'openup':
                # open-upvalue cache: holds exactly the captured register's value
                return ('R', int(k)) if static_k else ('RX', to_ir(k))
            return ('IDX', ('CONTAINER', obj.kind), to_ir(key))
        return ('IDX', to_ir(obj), to_ir(key))

    def call(self, x, env, out):
        f = self.ev(x['func'], env, out)
        args = [self.ev(a, env, out) for a in x['args']]
        if isinstance(f, STPath): f = f.resolve()
        if isinstance(f, SFn):
            n = f.name
            if n in ('bc_byte', 'bc_varint', 'bc_zigzag'):
                return self.bc_read(n)
            if n in ('bxor', 'band', 'bor', 'lshift', 'rshift') and all(not isinstance(a, (tuple, SObj)) for a in args):
                x, y = int(args[0]) % 2**32, int(args[1]) % 2**32
                return {'bxor': x ^ y, 'band': x & y, 'bor': x | y, 'lshift': (x << y) % 2**32, 'rshift': x >> y}[n]
            if n.startswith('native:'):
                return ('NATIVE', int(n.split(':')[1]), [to_ir(a) for a in args])
            if n == 'closure':
                proto = args[0]
                if not isinstance(proto, SProto): raise Unsupported('closure of dynamic proto')
                caps = args[1]
                return ('CLOSURE', proto.p, to_ir(caps) if caps is not None else ('CAPS', []))
            if n == 'create':
                return SBuild()
            if n == 'coroutine.wrap' and len(args) == 1 and isinstance(args[0], tuple) and args[0][0] == 'GENITER':
                return args[0]
            if n == 'unpack' and len(args) == 3 and isinstance(args[0], SDyn) and args[0].kind == 'stack':
                i, j = sval(args[1]), sval(args[2])
                if isinstance(i, int) and isinstance(j, int):
                    return ('MULTI', [('S', k) for k in range(i, j + 1)])
                return ('UNPACKSTACK', to_ir(args[1]), to_ir(args[2]))
            return ('CALL', ('FN', n), [to_ir(a) for a in args])
        if isinstance(f, tuple) and f[0] == 'GLOBALFN':
            return ('CALL', ('FN', f[1]), [to_ir(a) for a in args])
        if isinstance(f, tuple) and f[0] == 'BHV':
            # bhv(v112, expr...) -> PACKN
            return ('PACKN', [to_ir(a) for a in args[1:]])
        A = [to_ir(a) for a in args]
        if A and isinstance(A[-1], tuple) and A[-1][0] == 'MULTI':
            A = A[:-1] + A[-1][1]
        return ('CALL', to_ir(f), A)

    def bc_read(self, n):
        env = self._env
        pos = env.get('__bcpos')
        if not isinstance(pos, int): raise Unsupported('bytecode read at unknown position')
        bc = self.bytecode
        if n == 'bc_byte':
            env['__bcpos'] = pos + 1
            return bc[pos - 1]
        mult, u = 1, 0
        while True:
            b = bc[pos - 1]; pos += 1
            if b > 127: u += (b - 128) * mult
            else: u += b * mult; break
            mult *= 128
        env['__bcpos'] = pos
        if n == 'bc_varint': return u
        f = u // 2
        return f if u % 2 == 0 else -f - 1

    def handler_function(self, x, env, out):
        """the only function literals in handlers wrap a generic-for iterator:
           co_wrap(function() for a, b in f, s, c do co_yield(true, a, b) end end)"""
        body = blk(x['body'])
        if len(body) == 1 and nt(body[0]) == 'AstStatForIn':
            fi = body[0]
            vals = [to_ir(self.ev(v, env, out)) for v in fi['values']]
            return ('GENITER', vals, len(fi['vars']))
        raise Unsupported('function literal in handler')


def pure(e):
    return isinstance(e, tuple) and e[0] in ('R', 'U', 'K', 'T', 'ACC', 'S', 'TOP')

def simp(e):
    """light algebraic simplification of residual IR"""
    if e[0] == 'BIN':
        _, op, a, b = e
        if op == '+' and b == ('K', 0): return a
        if op == '+' and a == ('K', 0): return b
        if op == '-' and b == ('K', 0): return a
        if op in ('+', '-') and b[0] == 'K' and isinstance(b[1], (int, float)) and a[0] == 'BIN' and a[1] in ('+', '-') and a[3][0] == 'K':
            c1 = a[3][1] if a[1] == '+' else -a[3][1]
            c2 = b[1] if op == '+' else -b[1]
            c = c1 + c2
            if c == 0: return a[2]
            return ('BIN', '+' if c > 0 else '-', a[2], ('K', abs(c)))
    return e
