local M = {}

function M.string_begins_with(str, start)
  if str == nil then
    return false
  end
  return start == "" or str:sub(1, #start) == start
end

function M.string_ends_with(str, ending)
  if str == nil then
    return false
  end
  return ending == "" or str:sub(-#ending) == ending
end

function M.wildcard_to_regex(pattern)
  local reg = pattern:gsub("([^%w])", "%%%1"):gsub("%%%*", ".*")
  if not M.string_begins_with(reg, ".*") then
    reg = "^" .. reg
  end
  if not M.string_ends_with(reg, ".*") then
    reg = reg .. "$"
  end
  return reg
end

function M.string_wildcard_match(str, pattern)
  return str:match(M.wildcard_to_regex(pattern))
end

function M.list_wildcard_match(str, patterns)
  for _, pattern in ipairs(patterns) do
    if M.string_wildcard_match(str, pattern) ~= nil then
      return true
    end
  end
  return false
end

function M.remove_duplicates(list)
  local hash = {}
  local res = {}
  for _, v in ipairs(list) do
    if not hash[v] then
      res[#res + 1] = v
      hash[v] = true
    end
  end
  return res
end

function M.table_concat(t1, t2)
  for i = 1, #t2 do
    t1[#t1 + 1] = t2[i]
  end
  return t1
end

return M
