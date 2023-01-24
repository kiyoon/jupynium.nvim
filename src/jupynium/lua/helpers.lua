vim.g.jupynium_message_bloated = false

-- This number is not strictly accurate. We only use this to detect blockage (bloated)
vim.g.jupynium_num_pending_msgs = 0

-- Remove syncing without sending stop message.
-- Use when initialising or no Jupynium server is running.
function Jupynium_reset_sync()
  for bufnr, _ in pairs(Jupynium_syncing_bufs) do
    -- This will clear autocmds if there are any
    vim.api.nvim_create_augroup(string.format("jupynium_buf_%d", bufnr), { clear = true })
  end
end

if Jupynium_syncing_bufs ~= nil then
  Jupynium_reset_sync()
end

Jupynium_syncing_bufs = {} -- key = bufnr, value = 1

function Jupynium_reset_channel()
  vim.g.jupynium_channel_id = -1
  vim.g.jupynium_message_bloated = false
  vim.g.jupynium_num_pending_msgs = 0
  Jupynium_reset_sync()
end

local function get_line_count_all_buffers()
  local line_count = 0
  for buf_id, _ in pairs(Jupynium_syncing_bufs) do
    line_count = line_count + vim.api.nvim_buf_line_count(buf_id)
  end
  return line_count
end

get_line_count_all_buffers()

local function get_num_max_events()
  return math.max(vim.g.jupynium_num_max_msgs, get_line_count_all_buffers())
end

local function rpc(method, event, buf, ...)
  if vim.g.jupynium_channel_id ~= nil and vim.g.jupynium_channel_id > 0 then
    -- If bloated, wait until the messages are cleared
    -- Jupynium server should detect this and clear the messages
    -- And send grab_entire_buf
    if vim.g.jupynium_message_bloated then
      return
    end

    if vim.g.jupynium_num_pending_msgs < get_num_max_events() then
      vim.g.jupynium_num_pending_msgs = vim.g.jupynium_num_pending_msgs + 1
      local status, res = pcall(method, vim.g.jupynium_channel_id, event, buf, ...)
      if not status then
        print "Jupynium: RPC channel closed. Stop sending all notifications."
        Jupynium_reset_channel()
      else
        return res
      end
    else
      vim.g.jupynium_message_bloated = true
    end
  else
    Jupynium_reset_channel()
  end
end

function Jupynium_rpcnotify(event, buf, ensure_syncing, ...)
  -- check if it's already syncing
  if ensure_syncing then
    if Jupynium_syncing_bufs[buf] == nil then
      return
    end
  end
  rpc(vim.rpcnotify, event, buf, ...)
end

-- block until jupynium responds to the message
function Jupynium_rpcrequest(event, buf, ensure_syncing, ...)
  if ensure_syncing then
    if Jupynium_syncing_bufs[buf] == nil then
      if event ~= "start_sync" then
        return
      end
    end
  end

  local response = rpc(vim.rpcrequest, event, buf, ...)
  return response
end

function Jupynium_grab_entire_buffer(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot grab buffer without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  local entire_buf = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  Jupynium_rpcnotify("grab_entire_buf", bufnr, true, entire_buf)
end

function Jupynium_load_from_ipynb_tab_cmd(args)
  local is_number = args.args:match "^%d+$"
  if is_number == nil then
    Jupynium_notify.error { "Tab index should be a number but got: " .. args.args }
    return
  end
  local tab_idx = tonumber(args.args)
  local buf = vim.api.nvim_get_current_buf()
  Jupynium_load_from_ipynb_tab(buf, tab_idx)
end

function Jupynium_load_from_ipynb_tab(bufnr, tab_idx)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  local response = Jupynium_rpcrequest("load_from_ipynb_tab", bufnr, false, tab_idx)

  if response ~= "OK" then
    Jupynium_notify.error { "Failed to load from ipynb tab" }
  end
end

function Jupynium_load_from_ipynb_tab_and_start_sync_cmd(args)
  local is_number = args.args:match "^%d+$"
  if is_number == nil then
    Jupynium_notify.error { "Tab index should be a number but got: " .. args.args }
    return
  end
  local tab_idx = tonumber(args.args)
  local buf = vim.api.nvim_get_current_buf()
  Jupynium_load_from_ipynb_tab_and_start_sync(buf, tab_idx)
end

function Jupynium_load_from_ipynb_tab_and_start_sync(bufnr, tab_idx)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  local response = Jupynium_rpcrequest("load_from_ipynb_tab", bufnr, false, tab_idx)

  if response == "OK" then
    -- start sync with no content copying from nvim and no asking.
    Jupynium_start_sync(bufnr, tostring(tab_idx), false)
  else
    Jupynium_notify.error { "Failed to load from ipynb tab" }
  end
end

function Jupynium_start_sync_cmd(args)
  local filename = args.args
  local buf = vim.api.nvim_get_current_buf()
  Jupynium_start_sync(buf, filename)
end

function Jupynium_start_sync(bufnr, filename, ask)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if ask == nil then
    ask = true
  end

  -- This will clear autocmds if there are any
  local augroup = vim.api.nvim_create_augroup(string.format("jupynium_buf_%d", bufnr), { clear = true })

  if Jupynium_syncing_bufs[bufnr] ~= nil then
    Jupynium_notify.error { "Already syncing this buffer.", ":JupyniumStopSync to stop." }
    return
  end

  local content = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)

  local response = Jupynium_rpcrequest("start_sync", bufnr, false, filename, ask, content)
  if response ~= "OK" then
    Jupynium_notify.info { "Cancelling sync.." }
    return
  end

  Jupynium_syncing_bufs[bufnr] = 1

  vim.api.nvim_create_autocmd({ "CursorMoved" }, {
    buffer = bufnr,
    callback = function()
      local winid = vim.call("bufwinid", bufnr)
      local cursor_pos = vim.api.nvim_win_get_cursor(winid)
      local cursor_pos_row = cursor_pos[1] - 1
      local visual_start_row = vim.fn.getpos("v")[2] - 1
      Jupynium_rpcnotify("CursorMoved", bufnr, true, cursor_pos_row, visual_start_row)
    end,
    group = augroup,
  })

  vim.api.nvim_create_autocmd({ "CursorMovedI" }, {
    buffer = bufnr,
    callback = function()
      local winid = vim.call("bufwinid", bufnr)
      local cursor_pos = vim.api.nvim_win_get_cursor(winid)
      local cursor_pos_row = cursor_pos[1] - 1
      Jupynium_rpcnotify("CursorMovedI", bufnr, true, cursor_pos_row, cursor_pos_row)
    end,
    group = augroup,
  })

  vim.api.nvim_create_autocmd({ "ModeChanged" }, {
    buffer = bufnr,
    callback = function()
      local old_mode = vim.api.nvim_get_vvar("event")["old_mode"]
      local new_mode = vim.api.nvim_get_vvar("event")["new_mode"]
      if new_mode == "V" or new_mode == "v" or new_mode == "\x16" then
        local winid = vim.call("bufwinid", bufnr)
        local cursor_pos = vim.api.nvim_win_get_cursor(winid)
        local cursor_pos_row = cursor_pos[1] - 1
        local visual_start_row = vim.fn.getpos("v")[2] - 1
        Jupynium_rpcnotify("visual_enter", bufnr, true, cursor_pos_row, visual_start_row)
      elseif
        (old_mode == "v" or old_mode == "V" or old_mode == "\x16")
        and (new_mode ~= "v" and new_mode ~= "V" and new_mode ~= "\x16")
      then
        local winid = vim.call("bufwinid", bufnr)
        local cursor_pos = vim.api.nvim_win_get_cursor(winid)
        local cursor_pos_row = cursor_pos[1] - 1
        Jupynium_rpcnotify("visual_leave", bufnr, true, cursor_pos_row, cursor_pos_row)
      end
    end,
    group = augroup,
  })

  vim.api.nvim_create_autocmd({ "BufWritePre" }, {
    buffer = bufnr,
    callback = function()
      buf_filepath = vim.api.nvim_buf_get_name(bufnr)
      Jupynium_rpcnotify("BufWritePre", bufnr, true, buf_filepath)
    end,
    group = augroup,
  })

  vim.api.nvim_create_autocmd({ "BufWinLeave" }, {
    buffer = bufnr,
    callback = function()
      -- notify before detaching
      Jupynium_rpcnotify("BufWinLeave", bufnr, true)
      Jupynium_stop_sync(bufnr)
    end,
    group = augroup,
  })

  vim.api.nvim_buf_attach(bufnr, false, {
    on_lines = function(_, _, _, start_row, old_end_row, new_end_row, _)
      if Jupynium_syncing_bufs[bufnr] == nil then
        return
      end

      local lines = vim.api.nvim_buf_get_lines(bufnr, start_row, new_end_row, false)
      Jupynium_rpcnotify("on_lines", bufnr, true, lines, start_row, old_end_row, new_end_row)
    end,
  })
end

function Jupynium_stop_sync(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  Jupynium_rpcnotify("stop_sync", bufnr, true)
  -- This will clear autocmds if there are any
  vim.api.nvim_create_augroup(string.format("jupynium_buf_%d", bufnr), { clear = true })
  Jupynium_syncing_bufs[bufnr] = nil

  -- detach doesn't work. We just disable the on_lines callback by looking at Jupynium_syncing_bufs
  -- vim.api.nvim_buf_detach(buf)
end

function Jupynium_execute_selected_cells(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot execute cells without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  Jupynium_rpcnotify("execute_selected_cells", bufnr, true)
end

function Jupynium_toggle_selected_cells_outputs_scroll(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot toggle output cell without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  Jupynium_rpcnotify("toggle_selected_cells_outputs_scroll", bufnr, true)
end

function Jupynium_scroll_to_cell(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot scroll to cell without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  local winid = vim.call("bufwinid", bufnr)
  local cursor_pos = vim.api.nvim_win_get_cursor(winid)
  Jupynium_rpcnotify("scroll_to_cell", bufnr, true, cursor_pos[1] - 1)
end

function Jupynium_save_ipynb(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot save notebook without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  Jupynium_rpcnotify("save_ipynb", bufnr, true)
end

function Jupynium_download_ipynb(bufnr, output_name)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  -- get winnr from bufnr
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot download ipynb without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  buf_filepath = vim.api.nvim_buf_get_name(bufnr)
  if buf_filepath == "" then
    Jupynium_notify.error { [[Cannot download ipynb without having the filename for the buffer.]] }
    return
  end

  Jupynium_rpcnotify("download_ipynb", bufnr, true, buf_filepath, output_name)
end

function Jupynium_download_ipynb_cmd(args)
  local output_name = args.args
  Jupynium_download_ipynb(nil, output_name)
end

function Jupynium_auto_download_ipynb_toggle()
  vim.g.jupynium_autodownload_ipynb = 1 - vim.g.jupynium_auto_download_ipynb
  Jupynium_notify.info { "Auto download ipynb is now ", vim.g.jupynium_auto_download_ipynb == 1 and "on" or "off" }
end

function Jupynium_scroll_up(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot scroll notebook without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  local scroll_page = vim.g.jupynium_scroll_page or 0.5
  Jupynium_rpcnotify("scroll_ipynb", bufnr, true, -scroll_page)
end

function Jupynium_scroll_down(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot scroll notebook without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  local scroll_page = vim.g.jupynium_scroll_page or 0.5
  Jupynium_rpcnotify("scroll_ipynb", bufnr, true, scroll_page)
end

function Jupynium_autoscroll_toggle()
  vim.g.jupynium_autoscroll = 1 - vim.g.jupynium_autoscroll
  Jupynium_notify.info { "Autoscroll is now ", vim.g.jupynium_autoscroll == 1 and "on" or "off" }
end

function Jupynium_clear_selected_cells_outputs(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot clear outputs without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  Jupynium_rpcnotify("clear_selected_cells_outputs", bufnr, true)
end
