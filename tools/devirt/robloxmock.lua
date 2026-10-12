-- Deterministic universal mock of the Roblox API (identical for both sides of
-- the differential test). Every access/call is logged with its path.
local __out = realprint or print
local __B = getfenv and getfenv(1) or _G
local __cache = {}
local __mocks = setmetatable({}, {__mode = "k"})
local __steps = 0
local function __step(what)
    __steps = __steps + 1
    if __steps > 200000 then error("mock: step limit (" .. what .. ")") end
end
local function __arg(v)
    if __mocks[v] then return "<" .. __mocks[v] .. ">" end
    local ty = type(v)
    if ty == "string" then return "s:" .. (#v > 40 and v:sub(1, 40) or v):gsub("%c", "?") end
    if ty == "number" or ty == "boolean" or ty == "nil" then return tostring(v) end
    return ty
end
local M
local mt = {}
local __callbacks, __threads = {}, {}
mt.__index = function(self, k)
    local name = __mocks[self] .. "." .. tostring(k)
    __step(name)
    __out("M", "get", name)
    local c = rawget(__cache, name)
    if c == nil then c = M(name); __cache[name] = c end
    return c
end
mt.__newindex = function(self, k, v) __out("M", "set", __mocks[self] .. "." .. tostring(k), __arg(v)) end
mt.__call = function(self, ...)
    local name = __mocks[self]
    __step(name)
    local args = table.pack(...)
    local a = {}
    for i = 1, args.n do
        a[i] = __arg(args[i])
        if type(args[i]) == "function" then __callbacks[#__callbacks + 1] = {name, args[i]} end
    end
    __out("M", "call", name, table.concat(a, ","))
    -- event connection: run nothing, return a connection mock
    return M(name .. "()")
end
mt.__tostring = function(self) return __mocks[self] end
mt.__len = function() return 0 end
for _, op in ipairs({"__add", "__sub", "__mul", "__div", "__mod", "__pow", "__unm", "__idiv"}) do
    mt[op] = function() return 0 end
end
mt.__eq = function(a, b) return rawequal(a, b) end
mt.__lt = function() return false end
mt.__le = function() return true end
mt.__concat = function(a, b) return tostring(a) .. tostring(b) end
M = function(name)
    local o = setmetatable({}, mt)
    __mocks[o] = name
    return o
end
for _, n in ipairs({"game", "workspace", "script", "Instance", "Enum", "Vector3", "Vector2", "CFrame",
                    "Color3", "UDim2", "UDim", "TweenInfo", "Ray", "RaycastParams", "OverlapParams",
                    "NumberRange", "BrickColor", "shared", "plugin", "settings", "UserSettings", "DateTime"}) do
    __B[n] = M(n)
end
__B.typeof = function(v) if __mocks[v] then return "Instance" end return type(v) end
__B.tick = function() __step("tick") return 1000 + __steps * 0.001 end
__B.time = __B.tick
__B.elapsedTime = __B.tick
__B.wait = function(n) __step("wait") if coroutine.isyieldable() then coroutine.yield() end return n or 0.03, 1000 end
local function __resume(co, ...)
    local ok, e = coroutine.resume(co, ...)
    if not ok then __out("M", "threaderr", (tostring(e):gsub("^[^%s:]*:%d+:", "internal:3:"))) end
    if coroutine.status(co) == "suspended" then __threads[#__threads + 1] = co end
end
__B.spawn = function(f, ...) __resume(coroutine.create(f), ...) end
__B.delay = function(t, f, ...) __B.spawn(f, ...) end
__B.task = {
    wait = __B.wait,
    spawn = function(f, ...) if type(f) == "thread" then return f end __B.spawn(f, ...) return M("thread") end,
    defer = function(f, ...) __B.spawn(f, ...) end,
    delay = function(t, f, ...) __B.spawn(f, ...) end,
    cancel = function() end,
}

-- after the main chunk: fire every captured callback and resume threads, a few rounds
function RUNMOCK()
    for round = 1, 3 do
        local cbs, ths = __callbacks, __threads
        __callbacks, __threads = {}, {}
        for i, cb in ipairs(cbs) do
            __out("M", "fire", round, i, cb[1])
            __resume(coroutine.create(cb[2]), M("arg1"), M("arg2"))
        end
        for i, co in ipairs(ths) do
            __out("M", "resume", round, i)
            __resume(co)
        end
        for _, cb in ipairs(cbs) do __callbacks[#__callbacks + 1] = cb end
    end
end
