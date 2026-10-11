#!/usr/bin/env python3
"""opmap.py — extract the executor's handler for every opcode.

usage: opmap.py deob.lua deob.json t1post.txt out.txt [--json out.json]

Finds the instruction loop of the executor t[119] (`local v17 = v16[v14]`
followed by the opcode decision tree), substitutes the runtime constants
t[1][..] captured after VM init (t1post.txt, from the harness), and walks the
tree for each opcode value. Writes each distinct handler once, listing the
opcodes that reach it.
"""
import json, re, sys
from collections import defaultdict, OrderedDict
import flat
from flat import nt, blk, lkey, walk, Printer, UNK, truthy

def load_consts(path):
    C = {}
    for line in open(path, encoding='latin1'):
        m = re.match(r'T1 (t\[1\](?:\[\d+\])*) = (-?[\d.e+]+|true|false)\s*$', line.strip())
        if m:
            v = m.group(2)
            C[m.group(1)] = True if v == 'true' else False if v == 'false' else (int(v) if re.match(r'^-?\d+$', v) else float(v))
    return C

def path_of(x, tkey):
    """t[1][a][b] -> 't[1][a][b]' if rooted at the f1 local `t`"""
    parts = []
    while nt(x) == 'AstExprIndexExpr' and nt(x['index']) == 'AstExprConstantNumber':
        parts.append(int(x['index']['value'])); x = x['expr']
    if nt(x) == 'AstExprLocal' and lkey(x['local']) == tkey and parts:
        return 't' + ''.join('[%d]' % p for p in reversed(parts))
    return None

class Eval:
    def __init__(self, C, tkey, opkey):
        self.C, self.tkey, self.opkey = C, tkey, opkey
    def ev(self, x, N):
        t = nt(x)
        if t == 'AstExprConstantNumber': return x['value']
        if t == 'AstExprConstantBool': return x['value']
        if t == 'AstExprGroup': return self.ev(x['expr'], N)
        if t == 'AstExprLocal':
            return N if lkey(x['local']) == self.opkey else UNK
        if t == 'AstExprIndexExpr':
            p = path_of(x, self.tkey)
            if p and p in self.C: return self.C[p]
            return UNK
        if t == 'AstExprUnary' and x['op'] == 'Not':
            v = self.ev(x['expr'], N); return UNK if v is UNK else not truthy(v)
        if t == 'AstExprBinary':
            op = x['op']
            if op == 'And':
                a = self.ev(x['left'], N)
                if a is not UNK and not truthy(a): return a
                b = self.ev(x['right'], N)
                if a is UNK: return False if (b is not UNK and not truthy(b)) else UNK
                return b
            if op == 'Or':
                a = self.ev(x['left'], N)
                if a is not UNK and truthy(a): return a
                b = self.ev(x['right'], N)
                if a is UNK: return UNK
                return b
            a = self.ev(x['left'], N); b = self.ev(x['right'], N)
            if a is UNK or b is UNK: return UNK
            try:
                return {'CompareEq': lambda: a == b, 'CompareNe': lambda: a != b, 'CompareLt': lambda: a < b,
                        'CompareLe': lambda: a <= b, 'CompareGt': lambda: a > b, 'CompareGe': lambda: a >= b,
                        'Add': lambda: a + b, 'Sub': lambda: a - b}.get(op, lambda: UNK)()
            except TypeError:
                return UNK
        return UNK

def find_dispatch(root):
    """returns (loop_body_stmts, opkey, tkey, index_of_first_dispatch_if)"""
    res = []
    def f(x):
        if nt(x) == 'AstStatBlock':
            b = x['body']
            for i, st in enumerate(b):
                if nt(st) == 'AstStatLocal' and len(st['vars']) == 1 and st['vars'][0]['name'] == 'v17' and \
                        nt(st['values'][0]) == 'AstExprIndexExpr':
                    res.append((b, lkey(st['vars'][0]), i + 1))
    walk(root, f)
    return res

def main():
    src, astp, cpath, out = sys.argv[1:5]
    jout = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    d = flat.load_ast(src, astp)
    C = load_consts(cpath)
    # f1's local `t`
    f1 = d['root']['body'][0]['func'] if nt(d['root']['body'][0]) == 'AstStatLocalFunction' else None
    tkey = None
    for st in f1['body']['body']:
        if nt(st) == 'AstStatLocal' and st['vars'][0]['name'] == 't':
            tkey = lkey(st['vars'][0]); break
    D = find_dispatch(d['root'])
    assert len(D) == 1, len(D)
    body, opkey, start = D[0]
    E = Eval(C, tkey, opkey)
    flat.NOISE.update(flat.compute_state_temps(d['root']))
    pr = Printer()
    handlers = OrderedDict()      # id(leaf) -> (stmts, [ops])
    unresolved = []
    for N in range(0, 512):
        stmts = body[start:]
        path = []
        ok = True
        # descend: the first statement is the dispatch if; follow until a block
        # whose first statement is not a v17-dispatch if
        while True:
            if len(stmts) >= 1 and nt(stmts[0]) == 'AstStatIf':
                c = E.ev(stmts[0]['condition'], N)
                if c is UNK:
                    # is this a dispatch condition at all?
                    mentions = []
                    walk(stmts[0]['condition'], lambda y: mentions.append(1) if nt(y) == 'AstExprLocal' and lkey(y['local']) == opkey else None)
                    if mentions:
                        ok = False; break
                    break
                br = stmts[0]['thenbody'] if truthy(c) else stmts[0].get('elsebody')
                rest = stmts[1:]
                if rest:
                    # statements after the if belong to every branch: keep as suffix
                    path.append(rest)
                stmts = blk(br) if br is not None else []
                continue
            break
        if not ok:
            unresolved.append(N); continue
        key = id(stmts) if stmts else ('empty', tuple(id(r) for r in path))
        tail = [s for r in reversed(path) for s in r]
        if key not in handlers: handlers[key] = (stmts, tail, [])
        handlers[key][2].append(N)
    with open(out, 'w') as fo:
        J = []
        for key, (stmts, tail, ops) in handlers.items():
            text = ''.join(pr.s(s, '    ') for s in stmts)
            ttext = ''.join(pr.s(s, '    ') for s in tail)
            fo.write('-- ops %s\n%s' % (ops if len(ops) < 20 else '%d..%d (%d ops)' % (ops[0], ops[-1], len(ops)), text))
            if ttext.strip(): fo.write('    -- tail:\n' + ttext)
            fo.write('\n')
            J.append({'ops': ops, 'code': text, 'tail': ttext})
        if unresolved: fo.write('-- unresolved: %s\n' % unresolved)
    if jout: json.dump(J, open(jout, 'w'), indent=1)
    print('handlers', len(handlers), 'unresolved', len(unresolved))

if __name__ == '__main__':
    main()
