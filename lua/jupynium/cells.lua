local M = {}

local string_starts_with = function(str, start)
  if str == nil or start == nil then
    return false
  end
  return str:sub(1, #start) == start
end

local is_line_separator = function(row)
  local line = vim.api.nvim_buf_get_lines(0, row - 1, row, false)[1]
  if
    string_starts_with(line, "# %%")
    or string_starts_with(line, "# %%%")
    or string_starts_with(line, "# %% [md]")
    or string_starts_with(line, "# %% [markdown]")
    or string_starts_with(line, '"""%%')
    or string_starts_with(line, "'''%%")
    or string_starts_with(line, '%%"""')
    or string_starts_with(line, "%%'''")
  then
    return true
  end
  return false
end

function M.current_cell_separator(row)
  row = row or vim.api.nvim_win_get_cursor(0)[1]
  local found_separator = 0
  if is_line_separator(row) then
    return row
  end

  row = row - 1

  while row > 0 do
    if is_line_separator(row) then
      return row
    end
    row = row - 1
  end

  return nil
end

function M.previous_cell_separator(row)
  row = row or vim.api.nvim_win_get_cursor(0)[1]
  local found_separator = 0
  if is_line_separator(row) then
    found_separator = row
  end

  row = row - 1

  while row > 0 do
    if is_line_separator(row) then
      if found_separator > 0 then
        return row
      else
        found_separator = row
      end
    end
    row = row - 1
  end

  if found_separator > 0 then
    return found_separator
  end
  return nil
end

function M.next_cell_separator(row)
  row = row or vim.api.nvim_win_get_cursor(0)[1]
  row = row + 1

  local num_lines = vim.api.nvim_buf_line_count(0)

  while row <= num_lines do
    if is_line_separator(row) then
      return row
    end
    row = row + 1
  end

  return nil
end

return M
