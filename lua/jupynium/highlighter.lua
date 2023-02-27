-- Code mostly based on koenverburg/peepsight.nvim
local utils = require "jupynium.utils"
local cells = require "jupynium.cells"
local M = {}

M.options = {
  enable = true, -- separate from shortsighted.enable. Only for highlighting.
  highlight_groups = {},

  shortsighted = {
    enable = true,
    highlight_groups = {
      dim = "Comment",
    },
  },
}

function M.is_enabled()
  return M.options.enable or M.options.shortsighted.enable
end

function M.set_autocmd()
  local augroup = vim.api.nvim_create_augroup("jupynium-highlighter", {})
  vim.api.nvim_create_autocmd({ "BufWinEnter", "BufWritePost", "CursorMoved", "CursorMovedI", "WinScrolled" }, {
    pattern = "*.ju.*",
    callback = M.run,
    group = augroup,
  })
end

local ns_highlight = vim.api.nvim_create_namespace "jupynium-highlighter"
local ns_shortsighted = vim.api.nvim_create_namespace "jupynium-shortsighted"

--- Set highlight group for a line
---@param buffer number
---@param line_number number 0-indexed
---@param hl_group string
function M.set_line_hlgroup(buffer, namespace, line_number, hl_group)
  pcall(vim.api.nvim_buf_set_extmark, buffer, namespace, line_number, 0, {
    end_line = line_number + 1,
    end_col = 0,
    hl_group = hl_group,
    hl_eol = true,
    priority = 10000,
  })
end

function M.clear_namespace(namespace)
  vim.api.nvim_buf_clear_namespace(0, namespace, 0, -1)
end

function M.enable()
  M.options.enable = true

  if string.find(vim.fn.expand "%", ".ju.") then
    M.update()
  end
  M.set_autocmd()
end

function M.disable()
  M.options.enable = false

  M.clear_namespace(ns_highlight)
end

function M.toggle()
  if M.options.enable then
    M.disable()
  else
    M.enable()
  end
end

function M.run()
  if M.is_enabled() then
    M.clear_namespace(ns_highlight)
    M.clear_namespace(ns_shortsighted)

    M.update()
  end
end

function M.shortsighted_enable()
  M.options.shortsighted.enable = true

  if string.find(vim.fn.expand "%", ".ju.") then
    M.update()
  end
  M.set_autocmd()
end

function M.shortsighted_disable()
  M.options.shortsighted.enable = false

  M.clear_namespace(ns_shortsighted)
end

function M.shortsighted_toggle()
  if M.options.shortsighted.enable then
    M.shortsighted_disable()
  else
    M.shortsighted_enable()
  end
end

function M.update()
  if not M.is_enabled() then
    return
  end

  local end_of_file = vim.fn.line "$"
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local line_types = {}
  for i, line in ipairs(lines) do
    line_types[i] = cells.line_type(line)
  end

  if M.options.enable then
    for i, line_type in ipairs(line_types) do
      if line_type == "cell separator: code" then
        M.set_line_hlgroup(0, ns_highlight, i - 1, M.options.highlight_groups.code_cell_separator)
      elseif utils.string_begins_with(line_type, "cell separator: markdown") then
        M.set_line_hlgroup(0, ns_highlight, i - 1, M.options.highlight_groups.markdown_cell_separator)
      elseif line_type == "magic command" then
        M.set_line_hlgroup(0, ns_highlight, i - 1, M.options.highlight_groups.magic_command)
      end
    end
  end

  if M.options.shortsighted.enable then
    local current_row = cells.current_cell_separator()
    local next_row = cells.next_cell_separator()

    if current_row == nil and next_row == nil then
      return
    end

    if current_row ~= nil then
      -- Dim above cell range
      -- Exclude current cell separator
      for i = 1, current_row - 1 do
        if line_types[i] ~= "empty" then
          M.set_line_hlgroup(0, ns_shortsighted, i - 1, M.options.shortsighted.highlight_groups.dim)
        end
      end
    end

    if next_row ~= nil then
      -- Dim below cell range
      for j = next_row, end_of_file do
        if not line_types[j] ~= "empty" then
          M.set_line_hlgroup(0, ns_shortsighted, j - 1, M.options.shortsighted.highlight_groups.dim)
        end
      end
    end
  end
end

function M.add_commands()
  vim.api.nvim_create_user_command(
    "JupyniumShortsightedToggle",
    "lua require('jupynium.highlighter').shortsighted_toggle()",
    {}
  )
  vim.api.nvim_create_user_command(
    "JupyniumShortsightedEnable",
    "lua require('jupynium.highlighter').shortsighted_enable()",
    {}
  )
  vim.api.nvim_create_user_command(
    "JupyniumShortsightedDisable",
    "lua require('jupynium.highlighter').shortsighted_disable()",
    {}
  )
end

return M
