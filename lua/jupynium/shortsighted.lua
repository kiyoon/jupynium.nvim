-- Code mostly based on koenverburg/peepsight.nvim
local M = {}
local utils = {}

M.options = { enable = true }

function utils.is_empty_line(buf, line)
  local lines = vim.api.nvim_buf_get_lines(buf, line, line + 1, false)

  if vim.fn.trim(lines[1]) == "" then
    return true
  end

  return false
end

function utils.set_autocmd()
  vim.api.nvim_create_autocmd({ "BufWinEnter", "BufWritePost", "CursorMoved", "CursorMovedI", "WinScrolled" }, {
    pattern = "*.ju.*",
    callback = require("jupynium.shortsighted").run,
  })
end

function utils.contains(table, element)
  for _, value in pairs(table) do
    if value == element then
      return true
    end
  end
  return false
end

function utils.dim(namespace, buffer, line_number)
  pcall(vim.api.nvim_buf_set_extmark, buffer, namespace, line_number, 0, {
    end_line = line_number + 1,
    end_col = 0,
    hl_group = "Comment", -- mvp
    hl_eol = true,
    priority = 10000,
  })
end

function utils.clear(namespace)
  vim.api.nvim_buf_clear_namespace(0, namespace, 0, -1)
end

local cells = require "jupynium.cells"
local ns = vim.api.nvim_create_namespace "jupynium-shortsighted"

-- local defaults = {
--   enable = true,
-- }

local function string_ends_with(str, ending)
  return ending == "" or str:sub(-#ending) == ending
end

function M.enable()
  M.options.enable = true

  if string.find(vim.fn.expand "%", ".ju.") then
    M.focus(ns)
  end
  utils.set_autocmd()
end

function M.disable()
  M.options.enable = false

  utils.clear(ns)
end

function M.run()
  if M.options.enable then
    utils.clear(ns)

    M.focus(ns)
  end
end

function M.toggle()
  if M.options.enable then
    M.disable()
  else
    M.enable()
  end
end

function M.focus(namespace)
  local end_of_file = vim.fn.line "$"

  local current_row = cells.current_cell_separator()
  local next_row = cells.next_cell_separator()

  if current_row == nil and next_row == nil then
    return
  end

  if current_row ~= nil then
    -- Dim above cell range
    -- Exclude current cell separator
    for i = 0, current_row - 1 do
      if not utils.is_empty_line(0, i) then
        utils.dim(namespace, 0, i)
      end
    end
  end

  if next_row ~= nil then
    -- Dim below cell range
    for j = next_row - 1, end_of_file do
      if not utils.is_empty_line(0, j) then
        utils.dim(namespace, 0, j)
      end
    end
  end
end

function M.add_commands()
  vim.api.nvim_create_user_command("JupyniumShortsightedToggle", "lua require('jupynium.shortsighted').toggle()", {})
  vim.api.nvim_create_user_command("JupyniumShortsightedEnable", "lua require('jupynium.shortsighted').enable()", {})
  vim.api.nvim_create_user_command("JupyniumShortsightedDisable", "lua require('jupynium.shortsighted').disable()", {})
end

return M
