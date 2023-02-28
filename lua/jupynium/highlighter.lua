-- Code mostly based on koenverburg/peepsight.nvim
local utils = require "jupynium.utils"
local cells = require "jupynium.cells"
local M = {}

M.options = {
  enable = true, -- separate from shortsighted.enable. Only for highlighting.

  shortsighted = {
    enable = true,
    highlight_groups = {
      dim = "Comment",
    },
  },
}

function M.setup(opts)
  if opts.syntax_highlight.highlight_groups then
    -- deprecated, use vim.cmd [[hi! link Jupynium... ...]]
    vim.notify_once(
      "Jupynium: Setting highlight groups via opts is deprecated. Set directly using e.g. vim.cmd[[hi! link JupyniumCodeCellSeparator Folded]]",
      vim.log.levels.WARN
    )
    if opts.syntax_highlight.highlight_groups.code_cell_separator then
      vim.cmd("hi! link JupyniumCodeCellSeparator " .. opts.syntax_highlight.highlight_groups.code_cell_separator)
    end
    if opts.syntax_highlight.highlight_groups.markdown_cell_separator then
      vim.cmd(
        "hi! link JupyniumMarkdownCellSeparator " .. opts.syntax_highlight.highlight_groups.markdown_cell_separator
      )
    end
    if opts.syntax_highlight.highlight_groups.code_cell_content then
      vim.cmd("hi! link JupyniumCodeCellContent " .. opts.syntax_highlight.highlight_groups.code_cell_content)
    end
    if opts.syntax_highlight.highlight_groups.markdown_cell_content then
      vim.cmd("hi! link JupyniumMarkdownCellContent " .. opts.syntax_highlight.highlight_groups.markdown_cell_content)
    end
    if opts.syntax_highlight.highlight_groups.magic_command then
      vim.cmd("hi! link JupyniumMagicCommand " .. opts.syntax_highlight.highlight_groups.magic_command)
    end
  end

  -- If the colourscheme doesn't support Jupynium yet, link to some default highlight groups
  -- Here we can define some default settings per colourscheme.
  local colorscheme = vim.g.colors_name
  if utils.string_begins_with(colorscheme, "tokyonight") then
    colorscheme = "tokyonight"
  end
  local hlgroup
  if vim.fn.hlexists "JupyniumCodeCellSeparator" == 0 then
    vim.cmd [[hi! link JupyniumCodeCellSeparator Folded]]
  end
  if vim.fn.hlexists "JupyniumMarkdownCellSeparator" == 0 then
    vim.cmd [[hi! link JupyniumMarkdownCellSeparator Pmenu]]
  end
  --- In most cases you don't want to link Code cell content to anything.
  -- if vim.fn.hlexists "JupyniumCodeCellContent" == 0 then
  --   vim.cmd [[hi! link JupyniumCodeCellContent Normal]]
  -- end
  if vim.fn.hlexists "JupyniumMarkdownCellContent" == 0 then
    if colorscheme == "tokyonight" then
      hlgroup = "Pmenu"
    else
      hlgroup = "CursorLine"
    end
    vim.cmd([[hi! link JupyniumMarkdownCellContent ]] .. hlgroup)
  end
  if vim.fn.hlexists "JupyniumMagicCommand" == 0 then
    vim.cmd [[hi! link JupyniumMagicCommand Keyword]]
  end

  if opts.syntax_highlight.enable then
    M.enable()
  else
    M.disable()
  end

  if opts.shortsighted then
    M.shortsighted_enable()
  else
    M.shortsighted_disable()
  end
  M.add_commands()
end

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
function M.set_line_hlgroup(buffer, namespace, line_number, hl_group, priority)
  priority = priority or 99 -- Treesitter uses 100
  pcall(vim.api.nvim_buf_set_extmark, buffer, namespace, line_number, 0, {
    end_line = line_number + 1,
    end_col = 0,
    hl_group = hl_group,
    hl_eol = true,
    priority = priority,
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
  local line_types = cells.line_types_entire_buf()

  if M.options.enable then
    for i, line_type in ipairs(line_types) do
      -- priority 10000: above treesitter
      -- priority 99: below treesitter (default)
      if line_type == "cell separator: code" then
        M.set_line_hlgroup(0, ns_highlight, i - 1, "JupyniumCodeCellSeparator", 10000)
      elseif utils.string_begins_with(line_type, "cell separator: markdown") then
        M.set_line_hlgroup(0, ns_highlight, i - 1, "JupyniumMarkdownCellSeparator", 10000)
      elseif utils.string_begins_with(line_type, "cell content: code") then
        M.set_line_hlgroup(0, ns_highlight, i - 1, "JupyniumCodeCellContent")
      elseif utils.string_begins_with(line_type, "cell content: markdown") then
        M.set_line_hlgroup(0, ns_highlight, i - 1, "JupyniumMarkdownCellContent")
      elseif line_type == "magic command" then
        M.set_line_hlgroup(0, ns_highlight, i - 1, "JupyniumMagicCommand", 10000)
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
          M.set_line_hlgroup(0, ns_shortsighted, i - 1, M.options.shortsighted.highlight_groups.dim, 10000)
        end
      end
    end

    if next_row ~= nil then
      -- Dim below cell range
      for j = next_row, end_of_file do
        if not line_types[j] ~= "empty" then
          M.set_line_hlgroup(0, ns_shortsighted, j - 1, M.options.shortsighted.highlight_groups.dim, 10000)
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
