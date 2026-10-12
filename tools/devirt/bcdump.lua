-- Harness prelude part: dump the decoded VM bytecode string (t[19], produced
-- by t[19] = t[18](blob)) to stdout as hex, then stop. This is phase 1 of
-- DEVIRT_PLAN.md: from here on nothing depends on t[18] any more.
function HOOK_BC(s, t)
  realprint("BEGINBC " .. #s)
  local out = {}
  for i = 1, #s do
    out[#out + 1] = string.format("%02x", string.byte(s, i))
    if #out >= 4096 then realprint(table.concat(out)); out = {} end
  end
  realprint(table.concat(out))
  realprint("ENDBC")
  error("stop")
end
