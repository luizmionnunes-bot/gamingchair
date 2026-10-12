-- Reconstructed bodies for the lua.expert decompiler holes on the VM's
-- critical path. Loaded as a harness prelude (see tools/devirt/hook.py):
-- HOOK_STUB[n] replaces "structuring failed for function n".
-- Each stub receives `up` (accessors for the original upvalues) followed by
-- the original parameters. Evidence for every reconstruction: RECONSTRUCTED.md.

HOOK_STUB = HOOK_STUB or {}
local _floor, _byte, _char, _unpack = math.floor, string.byte, string.char, string.unpack

-- fn 268 = t[30]: zigzag varint from the bytecode stream (t[19], cursor t[20]).
-- Same LEB128 as t[29], then zigzag like the third reader of t[79].
HOOK_STUB[268] = function(up, s)
    local t = up.t()
    local mult, u = 1, 0
    while true do
        local b = _byte(s, t[20]); t[20] = t[20] + 1
        if b > 127 then u = u + (b - 128) * mult else u = u + b * mult; break end
        mult = mult * 128
    end
    local f = _floor(u / 2)
    if u % 2 == 0 then return f else return -f - 1 end
end

-- fn 128 = t2[69] (inside t[114]): layout builder for constant sections,
-- sibling of t2[70]/t2[71] selected by layout mode t2[23]. p1 = section base,
-- p2 = raw entries (may contain holes, hence the explicit count p3).
-- Produces exactly the shapes the layout accessor t[100] reads.
HOOK_STUB[128] = function(up, p1, p2, p3)
    local t2, t = up.t2(), up.t()
    local mode = t2[23]
    if mode == 1 then
        local w = {}
        for i = 1, p3 do if p2[i] ~= nil then w[i] = { p2[i] } end end
        return { p1, w, 0 }
    elseif mode == t[1][30][7] then            -- 2: chunked
        local size = p3 > 1 and _floor((p3 + 1) / t[1][30][7]) or 1
        local groups, g = {}, 1
        for s = 1, p3, size do
            local chunk, k = {}, 1
            for i = s, math.min(s + size - 1, p3) do chunk[k] = p2[i]; k = k + 1 end
            groups[g] = chunk; g = g + 1
        end
        return { p1, groups, size, p3 }
    elseif mode == t[1][28] then               -- 3: closure
        return { p1, function() return p2 end, p3 }
    end
    return { p1, p2, 0 }                       -- 0 / 4: raw
end

-- fn 228 = t[75]: kind-3/4 constant with 8 payload bytes -> IEEE-754 double
-- (little-endian, same byte order as the int64 readers t[66]/t[69]).
HOOK_STUB[228] = function(up, p1)
    local b = {}
    for i = 1, 8 do b[i] = p1[i] or 0 end
    return (_unpack("<d", _char(table.unpack(b))))
end

-- fn 234 = t[116]: wraps a deserialized prototype (output of t[114]) into the
-- object the executor t[119] expects:
--   obj[path1...](obj, obj[path2...]) -> instrs, nparams, protos, consts,
--                                        idxtabs, fieldmap, maxstack, extra
--   obj[2693] -> upvalue descriptors {kind, index, flag}
-- path1/path2 come from the proto header (t2[41]).
HOOK_STUB[234] = function(up, p1, p2)
    local t = up.t()
    local P = p1[123][31]
    local H, keys, S, fmap = P[1], P[2], P[3], P[4]
    local secinfo, modes, paths = H[keys[6]], H[keys[3]], H[keys[4]]
    local ckey = H[keys[7]][21] or 0
    local instrs, consts, protos, upv, idx, scal = {}, {}, {}, {}, {}, {}
    local posfix = {}
    for i = 1, #secinfo do
        local si = secinfo[i]
        local ty, base, n = si[1], si[2], si[3]
        local L = S[i]
        if ty == 0 then
            for j = 1, n do
                local raw = t[100](L, modes[1], base + j, false)
                -- payload is XOR-decrypted with the proto key (header t2[42]) and the
                -- constant's global index; raw[4] is not part of the decryption
                consts[base + j] = t[101](raw, base + j, ckey)
            end
        elseif ty == 1 then
            for j = 1, n do instrs[base + j] = t[100](L, modes[2], base + j, true) end
        elseif ty == 7 then
            for j = 1, n do protos[base + j] = HOOK_STUB[234](up, t[100](L, modes[3], base + j, false)) end
        elseif ty == 2 then
            -- inline-operand positions: {pc, position in the bytecode stream}
            for j = 1, n do posfix[#posfix + 1] = L[2][j] end
        elseif ty == 4 then
            for j = 1, n do upv[base + j] = L[2][j] end
        elseif ty == 5 then
            for j = 1, n do idx[base + j] = L[2][j] end
        elseif ty == 6 then
            local kind, val
            if modes[4] == t[1][7] then kind, val = L[1][1], L[2][1] else kind, val = L[1], L[2] end
            scal[kind] = val
        end
    end
    for _, e in ipairs(posfix) do
        local ins = instrs[e[1]]
        if ins then ins[t[52]] = e[2] end      -- operand D = stream position
    end
    local token = {}
    local obj = {}
    local function put(path, v)
        local o = obj
        for i = 1, #path - 1 do o[path[i]] = o[path[i]] or {}; o = o[path[i]] end
        o[path[#path]] = v
    end
    put(paths[2], token)
    put(paths[1], function(self, tok)
        return instrs, scal[0] or 0, protos, consts, idx, fmap, scal[2] or 0, scal[1]
    end)
    obj[2693] = upv
    if HOOK_NEWPROTO then HOOK_NEWPROTO(obj, instrs, p1) end
    obj.__proto = p1   -- kept for the dumper (not read by the VM)
    return obj
end
