local _fmt,_byte,_floor=string.format,string.byte,math.floor
HOOK_STUB = {}
local function leb(t, s)
  local mult, sum = 1, 0
  while true do
    local b = _byte(s, t[20]); t[20] = t[20] + 1
    if b > 127 then sum = sum + (b-128)*mult else sum = sum + b*mult; return sum end
    mult = mult * 128
  end
end
function HOOK_BC(s, t) realprint("BCLEN", #s) end
function HOOK_PROTO(p, t) realprint("PROTO", type(p), "pos", t[20], "len", #t[19]) end
function HOOK_POST(p, t) realprint("POST", type(p)) end
