local utils = require "jupynium.utils"

local M = {}

--- Get the line type (cell separator, magic commands, empty, others)
---@param line string | number 1-indexed
---@return string "cell separator: markdown" | "cell separator: markdown (jupytext)" | "cell separator: code" | "magic commands" | "empty" | "others"
function M.line_type(line)
  if type(line) == "number" then
    line = vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1]
  end

  if utils.string_begins_with(line, "# %%%") then
    return "cell separator: markdown"
  elseif utils.string_begins_with(line, '"""%%') or utils.string_begins_with(line, "'''%%") then
    return "cell separator: markdown (string)"
  elseif utils.string_begins_with(line, "# %% [md]") or utils.string_begins_with(line, "# %% [markdown]") then
    return "cell separator: markdown (jupytext)"
  elseif vim.fn.trim(line) == "# %%" then
    return "cell separator: code"
  elseif utils.string_begins_with(line, '%%"""') or utils.string_begins_with(line, "%%'''") then
    return "cell separator: code (string)"
  elseif utils.string_begins_with(line, "# ---") then
    return "metadata"
  elseif utils.string_begins_with(line, "# %") then
    return "magic command"
  elseif vim.fn.trim(line) == "" then
    return "empty"
  end

  return "others" -- code
end

local line_types_changedtick_per_buf = {}
local line_types_per_buf = {}

--- Get the line types of the entire buffer
--- Similar to `line_type` but returns a table of line types, and it returns more types
--- It also caches the results so repeated calls are fast
--- i.e. cell content: code, cell content: markdown, cell content: header
--- Useful for highlighting
---@return table
function M.line_types_entire_buf(bufnr)
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  local changedtick = vim.api.nvim_buf_get_changedtick(bufnr)
  if line_types_changedtick_per_buf[bufnr] == changedtick then
    return line_types_per_buf[bufnr]
  end

  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)

  local current_cell_type = "header"

  local line_types = {}

  for i, line in ipairs(lines) do
    local line_type = M.line_type(line)
    if line_type == "others" or line_type == "empty" then
      line_types[i] = "cell content: " .. current_cell_type
    elseif line_type == "cell separator: markdown (jupytext)" then
      current_cell_type = "markdown (jupytext)"
      line_types[i] = line_type
    elseif utils.string_begins_with(line_type, "cell separator: markdown") then
      current_cell_type = "markdown"
      line_types[i] = line_type
    elseif utils.string_begins_with(line_type, "cell separator: code") then
      current_cell_type = "code"
      line_types[i] = line_type
    else
      line_types[i] = line_type
    end
  end

  line_types_changedtick_per_buf[bufnr] = changedtick
  line_types_per_buf[bufnr] = line_types
  return line_types
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
