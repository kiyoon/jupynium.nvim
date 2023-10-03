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
Jupynium_bufs_attached = {} -- key = bufnr, value = 1

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

--- API: Execute javascript in the browser. It will switch to the correct tab before executing.
---@param bufnr integer | nil If given, before executing the code it will switch to the tab of this buffer. Requires syncing in advance.
---@param code string Javascript code
---@return boolean, object: Success, response
function Jupynium_execute_javascript(bufnr, code)
  local ensure_syncing = true
  if bufnr == nil then
    ensure_syncing = false
  elseif bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end

  if ensure_syncing and Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error {
      [[Cannot execute javascript because it's not synchronised]],
      [[Run `:JupyniumStartSync` or set bufnr=nil in Jupynium_execute_javascript()]],
    }
    return false, nil
  end

  -- set ensure_syncing to false, because we checked that already.
  return true, Jupynium_rpcrequest("execute_javascript", bufnr, false, code)
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

---Start synchronising the buffer with the ipynb file
---@param bufnr integer buffer number
---@param ipynb_filename string name of the ipynb file
---@param ask boolean whether to ask for confirmation
function Jupynium_start_sync(bufnr, ipynb_filename, ask)
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

  -- Used for choosing the correct kernel
  local buf_filetype = vim.api.nvim_buf_get_option(bufnr, "filetype")
  local conda_or_venv_path = vim.env.CONDA_PREFIX or vim.env.VIRTUAL_ENV

  local response =
    Jupynium_rpcrequest("start_sync", bufnr, false, ipynb_filename, ask, content, buf_filetype, conda_or_venv_path)
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

  -- Load completion items when cursor hold
  -- vim.api.nvim_create_autocmd({ "CursorHoldI" }, {
  --   buffer = bufnr,
  --   callback = function()
  --     local winid = vim.call("bufwinid", bufnr)
  --     -- (1, 0)-indexed
  --     local row, col = unpack(vim.api.nvim_win_get_cursor(winid))
  --     -- 0-indexed
  --     local code_line = vim.api.nvim_buf_get_lines(bufnr, row - 1, row, false)[1]
  --     local completion = Jupynium_kernel_complete(bufnr, code_line, col)
  --     vim.pretty_print(completion)
  --   end,
  --   group = augroup,
  -- })

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
      local buf_filepath = vim.api.nvim_buf_get_name(bufnr)
      Jupynium_rpcnotify("BufWritePre", bufnr, true, buf_filepath)
    end,
    group = augroup,
  })

  vim.api.nvim_create_autocmd({ "BufUnload" }, {
    buffer = bufnr,
    callback = function()
      Jupynium_rpcnotify("BufUnload", bufnr, true)
      Jupynium_stop_sync(bufnr)
    end,
    group = augroup,
  })

  if Jupynium_bufs_attached[bufnr] ~= nil then
    -- on_lines event handler already attached for this buffer
    return
  end

  vim.api.nvim_buf_attach(bufnr, false, {
    on_lines = function(_, _, _, start_row, old_end_row, new_end_row, _)
      if Jupynium_syncing_bufs[bufnr] == nil then
        -- Detach on_lines event handler
        Jupynium_bufs_attached[bufnr] = nil
        return true
      end

      local lines = vim.api.nvim_buf_get_lines(bufnr, start_row, new_end_row, false)
      Jupynium_rpcnotify("on_lines", bufnr, true, lines, start_row, old_end_row, new_end_row)
    end,
  })

  Jupynium_bufs_attached[bufnr] = 1
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

  local buf_filepath = vim.api.nvim_buf_get_name(bufnr)
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

function Jupynium_kernel_get_spec(bufnr)
  -- Users shouldn't have to call this function directly, and thus it won't be available as a command.
  -- returns a table
  -- ret[1] = current kernel name
  -- ret[2] = table of kernel names to spec
  --   ret[2].python3.spec.display_name
  --   ret[2].python3.spec.language
  --   ret[2].python3.spec.metadata.conda_env_name
  --   ret[2].python3.spec.metadata.conda_env_path

  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot get kernel list without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  local kernel_spec = Jupynium_rpcrequest("kernel_get_spec", bufnr, true)
  return kernel_spec
end

function Jupynium_kernel_change(bufnr, kernel_name)
  -- note that the kernel name is different from the display name in the kernel list in Jupyter Notebook.
  -- Users shouldn't have to call this function directly, and thus it won't be available as a command.
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot change kernel without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  Jupynium_rpcnotify("kernel_change", bufnr, true, kernel_name)
end

function Jupynium_restart_kernel(bufnr)
  Jupynium_notify.warn { [[Sorry! Command name changed.]], [[Please use :JupyniumKernelRestart]] }
  return Jupynium_kernel_restart(bufnr)
end

function Jupynium_kernel_restart(bufnr)
  -- note that the kernel name is different from the display name in the kernel list in Jupyter Notebook.
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot restart kernel without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  Jupynium_rpcnotify("kernel_restart", bufnr, true)
end

function Jupynium_kernel_interrupt(bufnr)
  -- note that the kernel name is different from the display name in the kernel list in Jupyter Notebook.
  -- Users shouldn't have to call this function directly, and thus it won't be available as a command.
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot interrupt kernel without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  Jupynium_rpcnotify("kernel_interrupt", bufnr, true)
end

function Jupynium_select_kernel(bufnr)
  Jupynium_notify.warn { [[Sorry! Command name changed.]], [[Please use :JupyniumKernelSelect]] }
  return Jupynium_kernel_select(bufnr)
end

function Jupynium_kernel_select(bufnr)
  -- note that the kernel name is different from the display name in the kernel list in Jupyter Notebook.
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot select kernel without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end

  local jupynium_kernel_name_and_spec = Jupynium_kernel_get_spec(bufnr)
  local current_kernel_name = jupynium_kernel_name_and_spec[1]
  local kernel_spec = jupynium_kernel_name_and_spec[2]
  local kernel_display_names, kernel_dispname_to_name = {}, {}
  for kernel_name, kern in pairs(kernel_spec) do
    -- filter by language
    if kern.spec.language:lower() == vim.bo.filetype then
      if kernel_name ~= current_kernel_name then
        table.insert(kernel_display_names, kern.spec.display_name)
      else
        -- current kernel is always first (default)
        table.insert(kernel_display_names, 1, kern.spec.display_name)
      end
      kernel_dispname_to_name[kern.spec.display_name] = kernel_name
    end
  end

  if kernel_dispname_to_name[kernel_display_names[1]] ~= current_kernel_name then
    -- by applying filtering, we dropped the current kernel.
    -- cancel the filtering and include everything.
    kernel_display_names = {}
    kernel_dispname_to_name = {}
    for kernel_name, kern in pairs(kernel_spec) do
      if kernel_name ~= current_kernel_name then
        table.insert(kernel_display_names, kern.spec.display_name)
      else
        -- current kernel is always first (default)
        table.insert(kernel_display_names, 1, kern.spec.display_name)
      end
      kernel_dispname_to_name[kern.spec.display_name] = kernel_name
    end
  end

  -- Use dressing.nvim to use Telescope, fzf-lua etc.
  vim.ui.select(kernel_display_names, {
    prompt = "Select a kernel for Jupynium (Jupyter Notebook)",
  }, function(selected)
    if selected == nil then
      return
    end
    Jupynium_kernel_change(bufnr, kernel_dispname_to_name[selected])
  end)
end

--- Inspect kernel and return the response.
---@param bufnr integer
---@param code_line string
---@param col integer 0-indexed
---@return table | nil
function Jupynium_kernel_inspect(bufnr, code_line, col)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot inspect kernel without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end
  return Jupynium_rpcrequest("kernel_inspect", bufnr, true, code_line, col)
end

--- Inspect kernel at cursor and display the response on a floating window.
--- Just like vim.lsp.buf.hover().
--- Code mainly from https://github.com/lkhphuc/jupyter-kernel.nvim
---@param bufnr integer
function Jupynium_kernel_hover(bufnr)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error { [[Cannot inspect kernel without synchronising.]], [[Run `:JupyniumStartSync`]] }
    return
  end
  -- (1, 0)-indexed
  local winid = vim.call("bufwinid", bufnr)
  local row, col = unpack(vim.api.nvim_win_get_cursor(winid))
  -- 0-indexed
  local code_line = vim.api.nvim_buf_get_lines(bufnr, row - 1, row, false)[1]
  local inspect = Jupynium_kernel_inspect(bufnr, code_line, col)
  local out = ""

  if inspect == nil or inspect == vim.NIL then
    out = "Failed to inspect kernel. Maybe the kernel has timed out."
  elseif inspect.status ~= "ok" then
    out = inspect.status
  elseif inspect.found == false then
    out = "No information from kernel"
  elseif inspect.found == true then
    local sections = vim.split(inspect.data["text/plain"], "\x1b%[0;31m")
    for _, section in ipairs(sections) do
      section = section
        -- Strip ANSI Escape code: https://stackoverflow.com/a/55324681
        -- \x1b is the escape character
        -- %[%d+; is the ANSI escape code for a digit color
        :gsub(
          "\x1b%[%d+;%d+;%d+;%d+;%d+m",
          ""
        )
        :gsub("\x1b%[%d+;%d+;%d+;%d+m", "")
        :gsub("\x1b%[%d+;%d+;%d+m", "")
        :gsub("\x1b%[%d+;%d+m", "")
        :gsub("\x1b%[%d+m", "")
        :gsub("\x1b%[H", "\t")
        -- Groups: name, 0 or more new line, content till end
        -- TODO: Fix for non-python kernel
        :gsub(
          "^(Call signature):(%s*)(.-)\n$",
          "```python\n%3 # %1\n```"
        )
        :gsub("^(Init signature):(%s*)(.-)\n$", "```python\n%3 # %1\n```")
        :gsub("^(Signature):(%s*)(.-)\n$", "```python\n%3 # %1\n```")
        :gsub("^(String form):(%s*)(.-)\n$", "```python\n%3 # %1\n```")
        :gsub("^(Docstring):(%s*)(.-)$", "\n---\n```rst\n%3\n```")
        :gsub("^(Class docstring):(%s*)(.-)$", "\n---\n```rst\n%3\n```")
        :gsub("^(File):(%s*)(.-)\n$", "*%1*: `%3`\n")
        :gsub("^(Type):(%s*)(.-)\n$", "*%1*: %3\n")
        :gsub("^(Length):(%s*)(.-)\n$", "*%1*: %3\n")
        :gsub("^(Subclasses):(%s*)(.-)\n$", "*%1*: %3\n")
      if section:match "%S" ~= nil and section:match "%S" ~= "" then
        -- Only add non-empty section
        out = out .. section
      end
    end
  end

  local markdown_lines = vim.lsp.util.convert_input_to_markdown_lines(out)
  markdown_lines = vim.lsp.util.trim_empty_lines(markdown_lines)

  local opts = { max_width = 84 }
  local ok, options = pcall(require, "jupynium.options")
  if ok then
    opts = vim.tbl_extend("force", opts, options.opts.kernel_hover.floating_win_opts)
  end

  vim.lsp.util.open_floating_preview(markdown_lines, "markdown", opts)
end

local function get_memory_addr(t)
  return string.format("%p", t)
end

--- Get completion candidates from kernel.
---@param bufnr integer
---@param code_line string
---@param col integer 0-indexed
---@param callback function nvim-cmp complete callback.
---@return table | nil
function Jupynium_kernel_complete_async(bufnr, code_line, col, callback)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if Jupynium_syncing_bufs[bufnr] == nil then
    Jupynium_notify.error {
      [[Cannot get completion through kernel without synchronising.]],
      [[Run `:JupyniumStartSync`]],
    }
    return
  end

  -- We don't want to update the completion menu if there's a newer request.
  -- So we use a callback_id to identify the callback, and only call it if it didn't change.
  local callback_id = get_memory_addr(callback)

  -- Store the callback in a global variable so that we can call it from python.
  Jupynium_kernel_complete_async_callback = callback
  vim.g.jupynium_kernel_complete_async_callback_id = callback_id

  Jupynium_rpcnotify("kernel_complete_async", bufnr, true, code_line, col, callback_id)
end

function Jupynium_get_kernel_connect_shcmd(bufnr, hostname)
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end

  local kernel_id = nil
  if Jupynium_syncing_bufs[bufnr] ~= nil then
    kernel_id = Jupynium_rpcrequest("kernel_connect_info", bufnr, true)
  end
  if kernel_id == nil then
    kernel_id = ""
  end
  local jupyter_command = "jupyter"
  local ok, options = pcall(require, "jupynium.options")
  if ok then
    if type(options.opts.jupyter_command) == "string" then
      jupyter_command = options.opts.jupyter_command
    elseif type(options.opts.jupyter_command) == "table" then
      jupyter_command = table.concat(options.opts.jupyter_command, " ")
    else
      Jupynium_notify.error { "Invalid jupyter_command type." }
    end
  end
  if hostname ~= "" then
    jupyter_command = "ssh " .. hostname .. " -t " .. jupyter_command
  end
  Jupynium_notify.info { "Connecting to kernel " .. kernel_id }
  local cmd = jupyter_command .. " console --existing " .. kernel_id
  return cmd
end

function Jupynium_kernel_connect_cmd(args)
  local hostname = args.args
  local buf = vim.api.nvim_get_current_buf()
  local cmd = Jupynium_get_kernel_connect_shcmd(buf, hostname)
  vim.cmd([[split | terminal ]] .. cmd)
  vim.cmd [[normal! G]]
end
