local M = {}

function M.string_begins_with(str, start)
  return start == "" or str:sub(1, #start) == start
end

function M.string_ends_with(str, ending)
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

return M
