"""Python port of the VM's constant-decryption PRNG (t[1][38] seed, t[1][3]
xorshift32 step, t[99] XOR stream). Arithmetic mirrors Lua doubles."""
M = 4294967296.0

def lmod(a, b):
    import math
    return a - math.floor(a / b) * b

def seed(p1, p2, p3):
    v = int(lmod(p1, M)) ^ int(lmod(lmod(p2, M) * 1103515245.0, M))
    v = v ^ int(lmod(lmod(p3 + 1, M) * 12345.0, M))
    return 1 if v == 0 else v

def step(x):
    x = (x ^ ((x << 13) & 0xffffffff)) % 4294967296
    x = (x ^ (x >> 17)) % 4294967296
    x = (x ^ ((x << 5) & 0xffffffff)) % 4294967296
    return 1 if x == 0 else x

def decrypt(data, key, p2, kind):
    """t[99](bytes, key, p2, kind)"""
    if key == 0: return bytes(data)
    s = seed(key, p2, kind)
    out = []
    for b in data:
        s = step(s)
        out.append(b ^ (s & 255))
    return bytes(out)
