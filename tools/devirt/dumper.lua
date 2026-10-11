-- Harness prelude part: serialize the deserialized proto tree (t[120]) as JSON.
local seen = {}
local nid = 0
local out = {}
local function emit(s) out[#out+1] = s; if #out > 2000 then realprint(table.concat(out)); out = {} end end
local function ser(v)
  local ty = type(v)
  if ty == "nil" then emit("null")
  elseif ty == "boolean" then emit(v and "true" or "false")
  elseif ty == "number" then
    if v ~= v then emit('{"nan":1}') elseif v == math.huge then emit('{"inf":1}') elseif v == -math.huge then emit('{"inf":-1}')
    else emit(string.format("%.17g", v)) end
  elseif ty == "string" then
    local h = {} for i = 1, #v do h[i] = string.format("%02x", string.byte(v, i)) end
    emit('{"s":"' .. table.concat(h) .. '"}')
  elseif ty == "table" then
    if seen[v] then emit('{"ref":' .. seen[v] .. '}') return end
    nid = nid + 1; seen[v] = nid
    emit('{"id":' .. nid .. ',"kv":[')
    local first = true
    if type(rawget(v, 2)) == "function" and type(rawget(v, 1)) == "number" then
      local ok, res = pcall(rawget(v, 2), rawget(v, 3) or 0)
      if ok then emit('[{"s":"' .. "666e726573" .. '"},') ser(res) emit("]") first = false end
    end
    for k, x in pairs(v) do
      if not first then emit(",") end first = false
      emit("[") ser(k) emit(",") ser(x) emit("]")
    end
    emit("]}")
  else emit('{"t":"' .. ty .. '"}') end
end
function HOOK_PROTO(p, t)
  realprint("BEGINDUMP")
  ser(p) realprint(table.concat(out)) out = {}
  realprint("\nENDDUMP")
  local fk = {} for i = 48, 56 do fk[#fk+1] = tostring(t[i]) end
  realprint("FIELDKEYS " .. table.concat(fk, " "))
end
