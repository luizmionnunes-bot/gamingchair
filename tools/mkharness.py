import sys, re
src_path, out_path = sys.argv[1], sys.argv[2]
s = open(src_path, encoding='utf-8', errors='surrogateescape').read()
# route the decoder stdlib funcs through local hooks
s,n1 = re.subn(r'\blocal gsub = string\.gsub\b',   'local gsub = HGSUB', s, count=1)
s,n2 = re.subn(r'\blocal char = string\.char\b',   'local char = HCHAR', s, count=1)
s,n3 = re.subn(r'\blocal concat = table\.concat\b','local concat = HCONCAT', s, count=1)
s,n4 = re.subn(r'\blocal sub = string\.sub\b',     'local sub = HSUB', s, count=1)
s,n5 = re.subn(r'\breturn f1\(', 'MODV = f1(', s, count=1)
assert (n1,n2,n3,n4,n5)==(1,1,1,1,1), (n1,n2,n3,n4,n5)
preamble = r'''
local realprint=print

local _gsub,_char,_concat,_sub,_byte=string.gsub,string.char,table.concat,string.sub,string.byte
local function emit(tag,x)
  if type(x)~="string" then return end
  if #x<4 or #x>600 then return end
  local pr=0 for i=1,#x do local b=_byte(x,i); if b>=32 and b<127 then pr=pr+1 end end
  if pr>=#x-1 then print("[["..tag.."]]"..x) end
end
local function HGSUB(a,b,c,...) local o,m=_gsub(a,b,c,...) emit("G",o) return o,m end
local function HCHAR(...) local o=_char(...) emit("C",o) return o end
local function HCONCAT(a,b,...) local o=_concat(a,b,...) emit("T",o) return o end
local function HSUB(a,b,c,...) local o=_sub(a,b,c,...) emit("S",o) return o end
local MODV=nil
'''
epilogue = r'''
realprint("=== module type:", type(MODV))
if type(MODV)=="table" then
  local ks={} for k,v in pairs(MODV) do ks[#ks+1]=tostring(k)..":"..type(v) end
  table.sort(ks); realprint("#keys:",#ks); realprint("keys:",table.concat(ks,", "))
  realprint("mt:",tostring(getmetatable(MODV)))
end
'''
open(out_path,'w',encoding='utf-8',errors='surrogateescape').write(preamble+s+epilogue)
