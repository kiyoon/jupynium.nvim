local utils = require "jupynium.utils"

local M = {}

--- Get the line type (cell separator, magic commands, empty, others)
---@param line string | number 1-indexed
---@return string "cell separator: markdown" | "cell separator: markdown (jupytext)" | "cell separator: code" | "magic commands" | "empty" | "others"
function M.line_type(line)
  if type(line) == "number" then
    line = vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1]
  end

  if
    utils.string_begins_with(line, "# %%%")
    or utils.string_begins_with(line, '"""%%')
    or utils.string_begins_with(line, "'''%%")
  then
    return "cell separator: markdown"
  elseif utils.string_begins_with(line, "# %% [md]") or utils.string_begins_with(line, "# %% [markdown]") then
    return "cell separator: markdown (jupytext)"
  elseif
    utils.string_begins_with(line, "# %%")
    or utils.string_begins_with(line, '%%"""')
    or utils.string_begins_with(line, "%%'''")
  then
    return "cell separator: code"
  elseif utils.string_begins_with(line, "# %") then
    return "magic command"
  elseif vim.fn.trim(line) == "" then
    return "empty"
  end

  return "others" -- code
end

--- Check if the line is a cell separator
---@param line string | number 1-indexed
---@return boolean
function M.is_line_separator(line)
  local line_type = M.line_type(line)
  if utils.string_begins_with(line_type, "cell separator:") then
    return true
  end

  return false
end

--- Get the current cell separator row
---@param row number | nil 1-indexed
---@return number | nil row 1-indexed
function M.current_cell_separator(row)
  row = row or vim.api.nvim_win_get_cursor(0)[1]
  if M.is_line_separator(row) then
    return row
  end

  row = row - 1

  while row > 0 do
    if M.is_line_separator(row) then
      return row
    end
    row = row - 1
  end

  return nil
end

--- Get the previous cell separator row
---@param row number | nil 1-indexed
---@return number | nil row 1-indexed
function M.previous_cell_separator(row)
  row = row or vim.api.nvim_win_get_cursor(0)[1]
  local found_separator
  if M.is_line_separator(row) then
    found_separator = row
  end

  row = row - 1

  while row > 0 do
    if M.is_line_separator(row) then
      if found_separator ~= nil then
        return row
      else
        found_separator = row
      end
    end
    row = row - 1
  end

  if found_separator ~= nil then
    return found_separator
  end
  return nil
end

--- Get the next cell separator row
---@param row number | nil 1-indexed
---@return number | nil row 1-indexed
function M.next_cell_separator(row)
  row = row or vim.api.nvim_win_get_cursor(0)[1]

  row = row + 1

  local num_lines = vim.api.nvim_buf_line_count(0)

  while row <= num_lines do
    if M.is_line_separator(row) then
      return row
    end
    row = row + 1
  end

  return nil
end

return M
