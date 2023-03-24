local M = {}

local textobj = require "jupynium.textobj"
local highlighter = require "jupynium.highlighter"
local server = require "jupynium.server"
local options = require "jupynium.options"
local utils = require "jupynium.utils"

function M.set_default_keymaps(buf_id)
  vim.keymap.set(
    { "n", "x" },
    "<space>x",
    "<cmd>JupyniumExecuteSelectedCells<CR>",
    { buffer = buf_id, desc = "Jupynium execute selected cells" }
  )
  vim.keymap.set(
    { "n", "x" },
    "<space>c",
    "<cmd>JupyniumClearSelectedCellsOutputs<CR>",
    { buffer = buf_id, desc = "Jupynium clear selected cells" }
  )
  vim.keymap.set(
    { "n" },
    "<space>K",
    "<cmd>JupyniumKernelHover<cr>",
    { buffer = buf_id, desc = "Jupynium hover (inspect a variable)" }
  )
  vim.keymap.set(
    { "n", "x" },
    "<space>js",
    "<cmd>JupyniumScrollToCell<cr>",
    { buffer = buf_id, desc = "Jupynium scroll to cell" }
  )
  vim.keymap.set(
    { "n", "x" },
    "<space>jo",
    "<cmd>JupyniumToggleSelectedCellsOutputsScroll<cr>",
    { buffer = buf_id, desc = "Jupynium toggle selected cell output scroll" }
  )
  vim.keymap.set("", "<PageUp>", "<cmd>JupyniumScrollUp<cr>", { buffer = buf_id, desc = "Jupynium scroll up" })
  vim.keymap.set("", "<PageDown>", "<cmd>JupyniumScrollDown<cr>", { buffer = buf_id, desc = "Jupynium scroll down" })
end

function M.default_keybindings(augroup)
  vim.api.nvim_create_autocmd({ "BufWinEnter" }, {
    pattern = options.opts.jupynium_file_pattern,
    callback = function(event)
      M.set_default_keymaps(event.buf)
    end,
    group = augroup,
  })
end

function M.setup(opts)
  options.opts = vim.tbl_deep_extend("force", {}, options.default_opts, opts)

  server.add_commands()

  local augroup = vim.api.nvim_create_augroup("jupynium", { clear = true })

  if
    options.opts.auto_start_server.enable
    or options.opts.auto_attach_to_server.enable
    or options.opts.auto_start_sync.enable
  then
    server.register_autostart_autocmds(augroup, options.opts)
  end

  -- Check if we need to set up keymaps in case plugin is lazy loaded like event = "BufEnter *.ju.*"
  local filename = vim.fn.expand "%"
  local buf_id = vim.api.nvim_get_current_buf()
  if utils.list_wildcard_match(filename, options.opts.jupynium_file_pattern) then
    if options.opts.use_default_keybindings then
      M.set_default_keymaps(buf_id)
    end
    if options.opts.textobjects.use_default_keybindings then
      textobj.set_default_keymaps(buf_id)
    end
  end

  if options.opts.use_default_keybindings then
    -- Register autocmd for setting up keymaps
    M.default_keybindings(augroup)
  end

  vim.g.jupynium_auto_download_ipynb = options.opts.auto_download_ipynb

  vim.g.jupynium_scroll_page_step = options.opts.scroll.page.step
  vim.g.jupynium_scroll_cell_top_margin_percent = options.opts.scroll.cell.top_margin_percent
  vim.g.jupynium_autoscroll_enable = options.opts.autoscroll.enable
  vim.g.jupynium_autoscroll_mode = options.opts.autoscroll.mode
  vim.g.jupynium_autoscroll_cell_top_margin_percent = options.opts.autoscroll.cell.top_margin_percent

  if options.opts.textobjects.use_default_keybindings then
    -- Register autocmd for setting up keymaps
    textobj.default_keybindings(augroup)
  end

  highlighter.setup(options.opts)

  vim.g.__jupynium_setup_completed = true
end

return M
