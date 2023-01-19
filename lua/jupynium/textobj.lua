local M = {}
local cells = require "jupynium.cells"

local enter_visual_mode = function()
  -- enter visual mode if normal or operator-pending (no) mode
  -- Why? According to https://learnvimscriptthehardway.stevelosh.com/chapters/15.html
  --   If your operator-pending mapping ends with some text visually selected, Vim will operate on that text.
  --   Otherwise, Vim will operate on the text between the original cursor position and the new position.
  local mode = vim.api.nvim_get_mode()
  if mode.mode == "no" or mode.mode == "n" or mode.mode == "v" or mode.mode == "<C-v>" then
    -- Use visual line because jupynium will get cleaner on_lines event
    vim.cmd "normal! V"
  end
end

-- Assume it is already visual mode
local function select_current_cell(row, include_current_separator, include_next_separator)
  row = row or vim.api.nvim_win_get_cursor(0)[1]
  if include_current_separator == nil then
    include_current_separator = true
  end
  if include_next_separator == nil then
    include_next_separator = false
  end

  local current_separator_row = cells.current_cell_separator(row)
  if current_separator_row == nil then
    return
  end

  local start_row = current_separator_row
  if not include_current_separator then
    start_row = start_row + 1
  end

  local next_row = cells.next_cell_separator(row)
  local end_row = nil
  if next_row == nil then
    end_row = vim.api.nvim_buf_line_count(0)
  else
    if include_next_separator then
      end_row = next_row
    else
      end_row = next_row - 1
    end
  end

  vim.api.nvim_win_set_cursor(0, { start_row, 0 })
  vim.cmd "normal! o"
  vim.api.nvim_win_set_cursor(0, { end_row, 0 })
  vim.cmd "normal! $"
end

M.goto_previous_cell_separator = function()
  local row = cells.previous_cell_separator()
  if row == nil then
    return
  end

  for _ = 1, vim.v.count1 - 1 do
    local next_row = cells.previous_cell_separator(row)
    if next_row == nil then
      break
    else
      row = next_row
    end
  end
  vim.api.nvim_win_set_cursor(0, { row, 0 })
end

M.goto_next_cell_separator = function()
  local row = cells.next_cell_separator()
  if row == nil then
    return
  end

  for _ = 1, vim.v.count1 - 1 do
    local next_row = cells.next_cell_separator(row)
    if next_row == nil then
      break
    else
      row = next_row
    end
  end
  vim.api.nvim_win_set_cursor(0, { row, 0 })
end

local status, repeat_move = pcall(require, "nvim-treesitter.textobjects.repeatable_move")
if status then
  M.goto_next_cell_separator, M.goto_previous_cell_separator =
    repeat_move.make_repeatable_move_pair(M.goto_next_cell_separator, M.goto_previous_cell_separator)
end

M.goto_current_cell_separator = function()
  local row = cells.current_cell_separator()
  if row == nil then
    return
  end
  vim.api.nvim_win_set_cursor(0, { row, 0 })
end

M.select_cell = function(include_current_separator, include_next_separator)
  if include_current_separator == nil then
    include_current_separator = true
  end
  if include_next_separator == nil then
    include_next_separator = false
  end
  enter_visual_mode()
  select_current_cell(nil, include_current_separator, include_next_separator)
end

M.default_keybindings = function(augroup)
  -- Text objects
  vim.api.nvim_create_autocmd({ "BufWinEnter" }, {
    pattern = "*.ju.*",
    callback = function()
      local buf_id = vim.api.nvim_get_current_buf()
      vim.keymap.set(
        { "n", "x", "o" },
        "[j",
        "<cmd>lua require'jupynium.textobj'.goto_previous_cell_separator()<cr>",
        { buffer = buf_id }
      )
      vim.keymap.set(
        { "n", "x", "o" },
        "]j",
        "<cmd>lua require'jupynium.textobj'.goto_next_cell_separator()<cr>",
        { buffer = buf_id }
      )
      vim.keymap.set(
        { "n", "x", "o" },
        "<space>j",
        "<cmd>lua require'jupynium.textobj'.goto_current_cell_separator()<cr>",
        { buffer = buf_id }
      )
      vim.keymap.set(
        { "x", "o" },
        "aj",
        "<cmd>lua require'jupynium.textobj'.select_cell(true, false)<cr>",
        { buffer = buf_id }
      )
      vim.keymap.set(
        { "x", "o" },
        "ij",
        "<cmd>lua require'jupynium.textobj'.select_cell(false, false)<cr>",
        { buffer = buf_id }
      )
      vim.keymap.set(
        { "x", "o" },
        "aJ",
        "<cmd>lua require'jupynium.textobj'.select_cell(true, true)<cr>",
        { buffer = buf_id }
      )
      vim.keymap.set(
        { "x", "o" },
        "iJ",
        "<cmd>lua require'jupynium.textobj'.select_cell(false, true)<cr>",
        { buffer = buf_id }
      )
    end,
    group = augroup,
  })
end

return M
