-- Logging environment shared by both sides of the differential test.
local __out = realprint or print
local __BASE = getfenv and getfenv(1) or _G
local __n = 0
local function __d(v)
    local ty = type(v)
    if ty == "string" then return "s:" .. (#v > 60 and v:sub(1, 60) or v):gsub("%c", "?") end
    if ty == "number" or ty == "boolean" or ty == "nil" then return tostring(v) end
    return ty
end
PROXYENV = setmetatable({}, {
    __index = function(_, k) __n = __n + 1; local v = __BASE[k]; __out("G", __n, "get", tostring(k), __d(v)); return v end,
    __newindex = function(_, k, v) __n = __n + 1; __out("G", __n, "set", tostring(k), __d(v)); __BASE[k] = v end,
})
-- normalize "chunk:line:" in caught error messages so both sides see the same text
local function __norm(e)
    if type(e) == "string" then return (e:gsub("^[^%s:]*:%d+:", "internal:3:")) end
    return e
end
local __pcall, __xpcall, __select, __unpack = pcall, xpcall, select, table.unpack
local __npcall = function(f, ...)
    local r = table.pack(__pcall(f, ...))
    if not r[1] then r[2] = __norm(r[2]); __out("PERR", tostring(r[2])) end
    return __unpack(r, 1, r.n)
end
local __nxpcall = function(f, h, ...)
    return __xpcall(f, function(e) __out("XERR", tostring(__norm(e))) return h(__norm(e)) end, ...)
end
local __mt = getmetatable(PROXYENV)
local __idx = __mt.__index
__mt.__index = function(s, k)
    local v = __idx(s, k)
    if k == "pcall" then return __npcall elseif k == "xpcall" then return __nxpcall end
    return v
end
-- normalize debug.info results (line numbers / sources differ between the two runs)
local __dbg = debug
local __ndebug = setmetatable({}, {__index = __dbg})
__ndebug.info = function(a, b, ...)
    local opts = b
    if type(a) == "number" then a = a + 1 end
    if type(a) == "thread" then opts = ... end
    local r = table.pack(__dbg.info(a, b, ...))
    if type(opts) == "string" then
        local i = 1
        for c in opts:gmatch(".") do
            if c == "l" and type(r[i]) == "number" and r[i] > 0 then r[i] = 3 end
            if c == "s" and type(r[i]) == "string" and r[i] ~= "[C]" then r[i] = "internal" end
            if c == "f" and r[i] ~= nil and false then end
            i = i + 1
        end
    end
    return table.unpack(r, 1, r.n)
end
local __idx2 = __mt.__index
__mt.__index = function(s, k)
    local v = __idx2(s, k)
    if k == "debug" then return __ndebug end
    return v
end
-- getfenv seen by the script: inside the VM every function's environment is the
-- loader's global table (not the proxy passed as p3); make both sides agree.
local __getfenv = getfenv
local __ngetfenv = function(a)
    local r
    if a == nil then r = __getfenv(2) elseif type(a) == "number" then r = __getfenv(a == 0 and 0 or a + 1) else r = __getfenv(a) end
    if r == PROXYENV then return __BASE end
    return r
end
local __idx3 = __mt.__index
__mt.__index = function(s, k)
    local v = __idx3(s, k)
    if k == "getfenv" then return __ngetfenv end
    return v
end
