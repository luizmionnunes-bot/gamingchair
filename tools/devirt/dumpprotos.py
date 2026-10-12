#!/usr/bin/env python3
"""dumpprotos.py — listing of the VM's own bytecode: every prototype, its
constants, its upvalue/index tables and its instructions.

usage: dumpprotos.py <workdir> <out.txt>

The prototype tree comes from the harness dump (`proto.json`, decoded by
model.py) and the opcode semantics from the executor's handler table
(`ops.json`, extracted by opmap.py). Handler bodies are printed in the
executor's own terms with the operand fields resolved:

    v16[v13] -> A    v16[v12] -> B    v16[v10] -> C    v16[v11] -> D
    v72 -> R (registers)      v102 -> STK (operand stack)
    v4  -> K (constants)      v9/v3 -> P (child prototypes)
    v5  -> IDX (index lists)  p2 -> UP (upvalues), p3 -> ENV
    v17 -> op (the opcode)    sum_2 -> pc, sum -> sp, sum_3 -> acc

so `R[A] = K[B]` is a load-constant and `pc = D` a jump. The ISA section
prints each distinct handler once; the per-prototype listing then repeats it
per instruction with A/B/C/D substituted by that instruction's operands.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.setrecursionlimit(1000000)
import model, opmap

FIELD = {'v13': 'A', 'v12': 'B', 'v10': 'C', 'v11': 'D'}
LOCALS = [('v17', 'op'), ('p2', 'UP'), ('p3', 'ENV'),
          ('v72', 'R'), ('v102', 'STK'), ('v112', 'RETBUF'), ('v132', 'MARKS'),
          ('v142', 'OPENLIST'), ('v152', 'VARARG'), ('v122', 'mark'), ('v42', 'VARARG'),
          ('v4', 'K'), ('v5', 'IDX'), ('v9', 'P'), ('v3', 'P'), ('v1', 'CODE'),
          ('v2', 'nparams'), ('v7', 'maxstack'), ('t2', 'OPENUP'),
          ('sum_2', 'pc'), ('sum_3', 'acc'), ('sum', 'sp'),
          ('count_2', 'opencount'), ('count', 'nmarks'), ('bhv', 'BHV')]


def symbolize(src, vmconsts=()):
    """executor source -> the same code in VM terms (fields, registers, pools)

    An instruction's A/B/C/D fields are *columns*: `v16[v13]` is the A column,
    and the superinstruction handlers index it per sub-step (`A[2]` is the A of
    the second step they run). Handlers that alias the record into a local of
    their own, or re-read it from the code section, are folded back onto it
    first so every field read prints as A/B/C/D.
    """
    rec = r'(?:v16|v1\[sum_2\])'
    for alias in set(re.findall(r'(?:local )?(v\d+) = %s[ \t]*$' % rec, src, re.M)):
        src = re.sub(r'\b%s\[' % alias, 'v16[', src)
        if not re.search(r'\b%s\b(?! = )' % alias, src):
            src = re.sub(r'^[ \t]*(?:local )?%s = %s[ \t]*$\n?' % (alias, rec), '',
                         src, flags=re.M)
    for v, name in FIELD.items():
        src = src.replace('v16[%s]' % v, name).replace('v1[sum_2][%s]' % v, name)
    # t[119] is the executor itself: calling it on a child prototype is how the
    # VM builds a closure
    src = src.replace('t[119](', 'closure(')
    # the remaining t[1][..] reads are VM constants fixed at init
    for path in sorted(vmconsts, key=len, reverse=True):
        src = src.replace(path, repr(vmconsts[path]))
    for v, name in sorted(LOCALS, key=lambda x: -len(x[0])):
        src = re.sub(r'\b%s\b' % v, name, src)
    for v, name in FIELD.items():
        src = src.replace('CODE[pc][%s]' % v, name)
    # the fused handlers read the *following* instructions out of the code
    # section, each into a local of its own; print their fields as
    # CODE[pc + 1].A and so on
    for alias in re.findall(r'(?:local )?(v\d+) = pc[ \t]*$', src, re.M):
        src = fold(src, alias, 'pc', lambda n: n)
    for alias, idx in re.findall(r'(?:local )?(v\d+) = (CODE\[[^]\n]*\])[ \t]*$',
                                 src, re.M):
        src = fold(src, alias, idx, lambda n, i=idx: '%s.%s' % (i, n))
    return src


def fold(src, alias, val, field):
    """rewrite `alias[<field key>]` as field(A/B/C/D), the rest of `alias` as
    `val`, and drop the then redundant `local alias = val` line"""
    for v, name in FIELD.items():
        src = src.replace('%s[%s]' % (alias, v), field(name))
    src = re.sub(r'\b%s\b' % alias, lambda _m: val, src)
    return re.sub(r'^[ \t]*(?:local )?%s = %s[ \t]*$\n?'
                  % (re.escape(val), re.escape(val)), '', src, flags=re.M)


def oneline(src, width=150):
    s = '; '.join(l.strip() for l in src.splitlines() if l.strip()
                  and not l.strip().startswith('--'))
    return s if len(s) <= width else s[:width - 3] + '...'


def subst(src, rec, consts):
    """substitute this instruction's operands for the A/B/C/D field names, then
    resolve the constant pool reads they turn into"""
    def one(m):
        v = rec.get(model.FK[m.group(0)])
        if v is None or v is False or isinstance(v, dict):
            return m.group(0)       # absent, or a column of a superinstruction
        return repr(v) if not isinstance(v, int) else str(v)
    src = re.sub(r'\b(?:A|B|C|D)\b', one, src)

    def k(m):
        i = int(m.group(1))
        return const(consts[i]) if i in consts else m.group(0)
    return re.sub(r'K\[(\d+)\]', k, src)


def const(v):
    if isinstance(v, bytes):
        try:
            s = v.decode('utf-8')
        except UnicodeDecodeError:
            return '<%d bytes> %s' % (len(v), v[:40].hex())
        if all(32 <= ord(c) < 127 or c in '\t\n' for c in s):
            return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"') \
                             .replace('\n', '\\n').replace('\t', '\\t')
        return '<%d bytes> %s' % (len(v), v[:40].hex())
    if v is None:
        return 'nil'
    if v is True or v is False:
        return 'true' if v else 'false'
    return repr(v)


def main():
    W, out = sys.argv[1], sys.argv[2]
    root = model.load_model(os.path.join(W, 'proto.json'))
    protos = list(model.all_protos(root))
    handlers = json.load(open(os.path.join(W, 'ops.json')))
    vmconsts = opmap.load_consts(os.path.join(W, 't1post.txt'))
    by_op = {}
    for h in handlers:
        body = symbolize(h['code'], vmconsts)
        tail = symbolize(h['tail'], vmconsts)
        for o in h['ops']:
            by_op[o] = (body, tail)

    used = {}
    for p in protos:
        for pc, rec in p.code.items():
            if rec is not None:
                used.setdefault(rec.get(model.FK['op']), 0)
                used[rec.get(model.FK['op'])] += 1

    ninstr = sum(len(p.code) for p in protos)
    nconst = sum(len(p.consts) for p in protos)
    f = open(out, 'w', encoding='utf-8')
    w = f.write
    w('-- gamingchairac: dump of the virtual machine\'s own bytecode\n')
    w('-- generated by tools/devirt/dumpprotos.py (see tools/devirt/run.sh)\n--\n')
    w('-- %d prototypes, %d instructions, %d constants\n'
      % (len(protos), ninstr, nconst))
    w('-- %d of the executor\'s %d opcodes are reached by this bytecode\n'
      % (len(used), len(by_op)))
    w('-- instruction fields: op A B C D F1 F2 F3 (header field map t[48..55])\n')
    w('-- R registers, K constants, STK operand stack, P child prototypes,\n')
    w('-- IDX index lists, pc program counter, sp stack pointer, acc accumulator\n')
    w('--\n-- The executor increments pc after running a handler, so a handler that\n')
    w('-- sets `pc = n` continues at n+1. That increment is the common case and is\n')
    w('-- left out of the per-instruction listing; a handler whose tail differs\n')
    w('-- shows it after `;;`. A handler too long for one line is cut with\n')
    w('-- `...`; its full body is in the instruction-set section.\n')
    w('--\n-- The devirtualized, readable program these prototypes encode is\n')
    w('-- gamingchairac.src.lua.\n')

    w('\n\n-- ' + '=' * 70 + '\n'
      + '-- instruction set: the %d opcodes this bytecode uses, %d distinct handlers\n'
      % (len(used), len({by_op[o] for o in used if o in by_op}))
      + '-- ' + '=' * 70 + '\n')
    seen = {}
    for o in sorted(used):
        h = by_op.get(o)
        if h is None:
            w('\nop %-4d (%d uses)  -- no handler found\n' % (o, used[o]))
            continue
        key = (h[0], h[1])
        if key in seen:
            w('\nop %-4d (%d uses)  -- same handler as op %d\n' % (o, used[o], seen[key]))
            continue
        seen[key] = o
        w('\nop %-4d (%d uses)\n' % (o, used[o]))
        for line in (h[0] + h[1]).splitlines():
            if line.strip():
                w('    %s\n' % line.rstrip())
        if not (h[0] + h[1]).strip():
            w('    -- no effect\n')

    w('\n\n-- ' + '=' * 70 + '\n-- prototype tree\n-- ' + '=' * 70 + '\n')
    def tree(p, ind=''):
        kids = [p.protos[k] for k in sorted(p.protos) if p.protos[k] is not None]
        w('-- %sproto %-4d params=%-3d maxstack=%-4d instrs=%-5d consts=%-4d '
          'upvals=%-3d children=%d\n'
          % (ind, p.id, p.nparams, p.maxstack, len(p.code), len(p.consts),
             len(p.upvals), len(kids)))
        for k in kids:
            tree(k, ind + '  ')
    tree(root)

    w('\n\n-- ' + '=' * 70 + '\n-- prototypes\n-- ' + '=' * 70 + '\n')
    for p in protos:
        kids = [p.protos[k].id for k in sorted(p.protos) if p.protos[k] is not None]
        w('\n\n-- ' + '-' * 70 + '\n')
        w('-- proto %d%s: params=%d maxstack=%d instrs=%d\n'
          % (p.id, ' (main)' if p.parent is None else ' (child of %d)' % p.parent.id,
             p.nparams, p.maxstack, len(p.code)))
        if kids:
            w('--   child prototypes: %s\n' % ', '.join(map(str, kids)))
        if p.consts:
            w('--   constants\n')
            for k in sorted(p.consts):
                w('--     K[%-5d] = %s\n' % (k, const(p.consts[k])))
        if p.upvals:
            w('--   upvalues\n')
            for k in sorted(p.upvals):
                w('--     UP[%-4d] = %s\n' % (k, p.upvals[k]))
        if p.idx:
            w('--   index lists\n')
            for k in sorted(p.idx):
                w('--     IDX[%-4d] = %s\n' % (k, p.idx[k]))
        w('--   code\n')
        for pc in sorted(p.code):
            rec = p.code[pc]
            if rec is None:
                w('%8d:  <missing>\n' % pc)
                continue
            op = rec.get(model.FK['op'])
            cols = []
            parts = []
            for n in ('A', 'B', 'C', 'D', 'F1', 'F2', 'F3'):
                v = rec.get(model.FK[n])
                if v is None or v is False:
                    continue
                if isinstance(v, dict):       # superinstruction: a column
                    col = [v[i] for i in sorted(k for k in v if isinstance(k, int))]
                    parts.append('%s[1..%d]' % (n, len(col)))
                    cols.append((n, col))
                else:
                    parts.append('%s=%s' % (n, v))
            ops = ' '.join(parts)
            h = by_op.get(op)
            if h is None:
                eff = '?'
            else:
                eff = oneline(subst(h[0], rec, p.consts))
                tail = oneline(subst(h[1], rec, p.consts))
                if tail != 'pc = pc + 1':
                    eff = (eff + ' ;; ' + tail) if eff else ';; ' + tail
                eff = eff or '-- no effect'
            w('%8d:  op %-4d %-28s -- %s\n' % (pc, op, ops, eff))
            for n, col in cols:
                line = '%s = ' % n
                for i, v in enumerate(col, 1):
                    piece = ('%s' % v) + (', ' if i < len(col) else '')
                    if len(line) + len(piece) > 96:
                        w('%12s%s\n' % ('', line)); line = '%s   ' % (' ' * len(n))
                    line += piece
                w('%12s%s\n' % ('', line))
    f.close()
    print('%s: %d protos, %d instructions, %d constants'
          % (out, len(protos), ninstr, nconst))


if __name__ == '__main__':
    main()
