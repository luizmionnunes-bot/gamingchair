function DUMPT1(t)
  local function ser(v, path, depth)
    local ty = type(v)
    if ty == "number" or ty == "boolean" then realprint("T1 " .. path .. " = " .. tostring(v))
    elseif ty == "string" then realprint("T1 " .. path .. " = " .. string.format("%q", v))
    elseif ty == "table" and depth < 3 then
      for k, x in pairs(v) do
        if type(k) == "number" or type(k) == "string" then ser(x, path .. "[" .. (type(k)=="string" and string.format("%q",k) or tostring(k)) .. "]", depth + 1) end
      end
    else realprint("T1 " .. path .. " : " .. ty) end
  end
  ser(t[1], "t[1]", 0)
  for i = 1, 130 do local v = t[i]; if type(v) == "number" or type(v) == "boolean" then realprint("TN t[" .. i .. "] = " .. tostring(v)) elseif v ~= nil then realprint("TN t["..i.."] : "..type(v)) end end
end
