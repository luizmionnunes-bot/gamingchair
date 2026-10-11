#!/usr/bin/env python3
"""lift.py — devirtualize: specialize the VM executor for every instruction of
every prototype (peval.py), recover the control-flow graph, and emit Lua.

usage: lift.py deob.lua deob.json t1post.txt proto.json out_dir
"""
import json, os, sys
from collections import defaultdict, Counter
import flat
from flat import nt, blk, lkey, walk
import model, peval
from peval import PE, SCode, SConsts, SProtos, SIdx, SDyn, Unsupported
import opmap

def executor_bind(root):
    """find t[119] and its returned interpreter closure; map their locals"""
    target = []
    def f(x):
        if nt(x) == 'AstExprFunction':
            # interpreter closure: body contains `local v17 = v16[...]`
            found = []
            def g(y):
                if nt(y) == 'AstStatLocal' and y['vars'][0]['name'] == 'v17' and y['values'] and nt(y['values'][0]) == 'AstExprIndexExpr' and nt(y['values'][0]['expr']) == 'AstExprLocal' and y['values'][0]['expr']['local']['name'] == 'v16': found.append(1)
            flat.walk_nofunc(x, g)
            if found: target.append(x)
    walk(root, f)
    assert len(target) == 1
    inner = target[0]
    outer = []
    def h(x):
        if nt(x) == 'AstExprFunction':
            for st in blk(x['body']):
                if nt(st) == 'AstStatReturn' and st['list'] and st['list'][0] is inner: outer.append(x)
    walk(root, h)
    assert len(outer) == 1
    outer = outer[0]
    def scope_locals(fn):
        L = {}
        for a in fn['args']: L[a['name']] = lkey(a)
        def g(y):
            if nt(y) == 'AstStatLocal':
                for v in y['vars']: L[v['name']] = lkey(v)
            if nt(y) == 'AstStatLocalFunction': L[y['name']['name']] = lkey(y['name'])
        for st in blk(fn['body']):
            if nt(st) in ('AstStatLocal', 'AstStatLocalFunction'): g(st)
        return L
    return scope_locals(outer), scope_locals(inner)

STDNAMES = {'error_': 'error', 'next_': 'next', 'str_match': 'string.match', 'tonumber_': 'tonumber',
    'str_gsub': 'string.gsub', 'str_sub': 'string.sub', 'tbl_insert': 'table.insert', 'str_char': 'string.char',
    'str_byte': 'string.byte', 'co_yield': 'coroutine.yield', 'co_wrap': 'coroutine.wrap', 'str_rep': 'string.rep',
    'tbl_concat': 'table.concat', 'math_floor': 'math.floor', 'select_': 'select', 'getfenv_': 'getfenv',
    'setmetatable_': 'setmetatable', 'next_b': 'next', 'tbl_unpack': 'table.unpack', 'math_min': 'math.min',
    'str_len': 'string.len', 'tbl_remove': 'table.remove', 'tbl_sort': 'table.sort', 'str_unpack': 'string.unpack',
    'str_gmatch': 'string.gmatch', 'str_find': 'string.find', 'str_reverse': 'string.reverse',
    'tostring_': 'tostring', 'math_abs': 'math.abs', 'rawget_': 'rawget', 'str_format': 'string.format'}

class Lifter:
    def __init__(self, deob, astp, t1, protojson):
        self.ast = flat.load_ast(deob, astp)
        self.C = opmap.load_consts(t1)
        self.pe = PE(self.ast['root'], self.C)
        self.pe.bytecode = open(os.path.join(os.path.dirname(protojson), 'bytecode.bin'), 'rb').read()
        self.O, self.I = executor_bind(self.ast['root'])
        self.root = model.load_model(protojson)
        # t (f1 local)
        f1 = self.ast['root']['body'][0]['func']
        self.tkey = [lkey(st['vars'][0]) for st in f1['body']['body'] if nt(st) == 'AstStatLocal' and st['vars'][0]['name'] == 't'][0]
        self.stdlib = {lkey(a): peval.SFn(STDNAMES.get(a['name'], a['name'])) for a in f1['args']}

    def bind(self, proto):
        O, I = self.O, self.I
        fm = proto.fmap
        static = {
            O['v1']: SCode(proto), O['v2']: proto.nparams, O['v4']: SConsts(proto), O['v5']: SIdx(proto),
            O['v7']: proto.maxstack, O['v9']: SProtos(proto), O['v3']: SProtos(proto),
            O['v10']: fm[10], O['v11']: fm[5], O['v12']: fm[7], O['v13']: fm[4], O['v14']: fm[14],
            O['p2']: SDyn('upvals'), O['p3']: SDyn('env'),
            I['t2']: SDyn('openup'), I['v42']: SDyn('varargs'), I['v152']: SDyn('varargs'),
            I['v52']: ('NVA',), I['v6']: ('NVA',), I['v72']: SDyn('regs'), I['bhv']: ('BHV',),
            I['v92']: proto.nparams + 1, I['v102']: SDyn('stack'), I['v112']: SDyn('retbuf'),
            I['v132']: peval.SMarks(), I['v142']: SDyn('openlist'),
            self.tkey: self.pe.TC,
        }
        static.update(self.stdlib)
        roles = {I['sum_3']: 'acc', I['v3']: 'top', I['sum_2']: 'pc', I['sum']: 'sp',
                 I['count']: 'nmarks', I['v122']: 'mark', I['count_2']: 'opencount', I['v8']: 'v8',
                 I['v15']: 'carry', I['v22']: 'carry'}
        return {'static': static, 'roles': roles, 'pc': I['sum_2'], 'sp': I['sum'], 'opkey': fm[14],
                'mark': I['v122'], 'nmarks': I['count'], 'carry': [I['v15'], I['v22']]}

    def lift_proto(self, proto):
        b = self.bind(proto)
        ir = {}
        errors = []
        sp_at = {1: (0, 0, 0, (), (None, None))}
        work = [1]
        while work:
            pc = work.pop()
            if pc in ir: continue
            if pc not in proto.code:
                errors.append((pc, None, 'pc out of range')); continue
            sp = sp_at[pc]
            try:
                stmts = self.pe.specialize(proto, pc, sp, b)
            except Unsupported as ex:
                errors.append((pc, proto.code[pc].get(5), str(ex)))
                ir[pc] = None
                continue
            ir[pc] = stmts
            for nxt, nsp in successors(stmts):
                if nxt is None: continue
                if nxt in sp_at and sp_at[nxt] != nsp:
                    errors.append((nxt, None, 'sp mismatch %r vs %r' % (sp_at[nxt], nsp)))
                sp_at.setdefault(nxt, nsp)
                work.append(nxt)
        return ir, errors

def successors(stmts):
    r = []
    for s in stmts:
        if s[0] == 'NEXT': r.append((s[1] + 0, s[2]))
        elif s[0] == 'IF':
            r += successors(s[2]) + successors(s[3])
    return r

def main():
    deob, astp, t1, pj, outd = sys.argv[1:6]
    L = Lifter(deob, astp, t1, pj)
    os.makedirs(outd, exist_ok=True)
    errs = Counter(); total = 0; bad = 0
    examples = {}
    import time
    for p in model.all_protos(L.root):
        t0 = time.time()
        ir, errors = L.lift_proto(p)
        dt = time.time() - t0
        if dt > 5: print('slow proto', p.id, len(p.code), '%.1fs' % dt, flush=True)
        total += len(ir)
        for pc, op, msg in errors:
            bad += 1
            errs[(op, msg)] += 1
            examples.setdefault((op, msg), (p.id, pc))
    print('instructions lifted', total, 'errors', bad)
    for (op, msg), n in errs.most_common(40):
        print('%5d op=%s %s  e.g. %s' % (n, op, msg, examples[(op, msg)]))

if __name__ == '__main__':
    main()
