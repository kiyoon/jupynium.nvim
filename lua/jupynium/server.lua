local M = {}

local options = require "jupynium.options"
local utils = require "jupynium.utils"

M.server_state = {
  is_autostarted = false,
  is_autoattached = false,
}

local function TableConcat(t1, t2)
  for i = 1, #t2 do
    t1[#t1 + 1] = t2[i]
  end
  return t1
end

local function run_process_bg(cmd, args)
  args = args or {}
  local cmd_str
  if vim.fn.has "win32" == 1 then
    cmd_str = [[PowerShell "Start-Process -FilePath \"]]
      .. vim.fn.expand(cmd):gsub("\\", "\\\\")
      .. [[\" -ArgumentList \"]]

    for _, v in ipairs(args) do
      cmd_str = cmd_str .. [[ `\"]] .. v:gsub("\\", "\\\\") .. [[`\"]]
    end

    cmd_str = cmd_str .. [[\""]]
  else
    cmd_str = [["]] .. vim.fn.expand(cmd) .. [["]]

    for _, v in ipairs(args) do
      cmd_str = cmd_str .. [[ "]] .. v:gsub("\\", "\\\\") .. [["]]
    end

    -- prior to nvim 0.9.0, stderr will create graphical glitch.
    -- https://github.com/neovim/neovim/issues/21376
    cmd_str = cmd_str .. [[ 2> /dev/null &]]
  end

  io.popen(cmd_str)
end

local function run_process(cmd, args)
  args = args or {}
  local call_str = [[system('"]] .. vim.fn.expand(cmd) .. [["]]

  for _, v in ipairs(args) do
    call_str = call_str .. [[ "]] .. v:gsub("\\", "\\\\") .. [["]]
  end

  call_str = call_str .. [[')]]

  local output = vim.fn.eval(call_str)
  if output == nil then
    return ""
  else
    return output
  end
end

local function call_jupynium_cli(args, bg)
  args = args or {}
  if bg == nil then
    bg = true
  end

  args = TableConcat({ "-m", "jupynium", "--nvim_listen_addr", vim.v.servername }, args)

  local cmd
  if type(options.opts.python_host) == "string" then
    cmd = options.opts.python_host
  elseif type(options.opts.python_host) == "table" then
    cmd = options.opts.python_host[1]
    args = TableConcat({ unpack(options.opts.python_host, 2) }, args)
  else
    error "Invalid python_host type."
  end

  if bg then
    run_process_bg(cmd, args)
  else
    return run_process(cmd, args)
  end
end

function M.jupynium_pid()
  local pid = vim.fn.trim(call_jupynium_cli({ "--check_running" }, false))
  if pid == "" then
    return nil
  else
    return tonumber(pid)
  end
end

function M.register_autostart_autocmds(augroup, opts)
  -- Weird thing to note
  -- BufNew will be called when you even close vim, even without opening any .ju.py file
  -- Maybe because it access to a recent file history?
  local all_patterns = {}
  if opts.auto_start_server.enable then
    for _, v in pairs(opts.auto_start_server.file_pattern) do
      table.insert(all_patterns, v)
    end
  end
  if opts.auto_attach_to_server.enable then
    for _, v in pairs(opts.auto_attach_to_server.file_pattern) do
      table.insert(all_patterns, v)
    end
  end
  if opts.auto_start_sync.enable then
    for _, v in pairs(opts.auto_start_sync.file_pattern) do
      table.insert(all_patterns, v)
    end
  end

  all_patterns = utils.remove_duplicates(all_patterns)

  vim.api.nvim_create_autocmd({ "BufWinEnter" }, {
    pattern = all_patterns,
    callback = function()
      local bufname = vim.api.nvim_buf_get_name(0)
      local bufnr = vim.api.nvim_get_current_buf()
      if not M.server_state.is_autostarted then
        if
          opts.auto_start_server.enable
          and utils.list_wildcard_match(bufname, opts.auto_start_server.file_pattern) ~= nil
        then
          vim.cmd [[JupyniumStartAndAttachToServer]]
          M.server_state.is_autostarted = true
        end
      end

      if not M.server_state.is_autostarted and not M.server_state.is_autoattached then
        if
          opts.auto_attach_to_server.enable
          and utils.list_wildcard_match(bufname, opts.auto_attach_to_server.file_pattern) ~= nil
        then
          vim.cmd [[JupyniumAttachToServer]]
          M.server_state.is_autoattached = true
        end
      end

      if opts.auto_start_sync.enable then
        if utils.list_wildcard_match(bufname, opts.auto_start_sync.file_pattern) ~= nil then
          -- check if server is running
          if not M.server_state.is_autostarted then
            if M.jupynium_pid() == nil then
              return
            end
          end

          -- auto start sync
          filename_wo_ext = vim.fn.expand "%:r:r"
          if vim.fn.exists ":JupyniumStartSync" > 0 then
            Jupynium_start_sync(bufnr, filename_wo_ext)
            -- vim.cmd [[JupyniumStartSync]]
          else
            if M.server_state.is_autostarted or M.server_state.is_autoattached then
              -- wait until command exists
              local found, _ = vim.wait(1000, function()
                return vim.fn.exists ":JupyniumStartSync" > 0
              end)

              if found then
                Jupynium_start_sync(bufnr, filename_wo_ext)
                -- vim.cmd [[JupyniumStartSync]]
              end
            end
          end
        end
      end
    end,
    group = augroup,
  })
end

function M.add_commands()
  -- not all commands are added here.
  -- It only includes wrapper that calls Python Jupynium package.
  -- The rest of the commands will be added when you attach a server.
  vim.api.nvim_create_user_command("JupyniumStartAndAttachToServer", M.start_and_attach_to_server_cmd, { nargs = "?" })
  vim.api.nvim_create_user_command("JupyniumAttachToServer", M.attach_to_server_cmd, { nargs = "?" })
end

function M.start_and_attach_to_server_cmd(args)
  local notebook_URL = vim.fn.trim(args.args)

  if notebook_URL == "" then
    notebook_URL = options.opts.default_notebook_URL
  end
  args = { "--notebook_URL", notebook_URL, "--firefox_profiles_ini_path", options.opts.firefox_profiles_ini_path }
  if options.opts.notebook_dir ~= nil and options.opts.notebook_dir ~= "" then
    table.insert(args, "--notebook_dir")
    table.insert(args, options.opts.notebook_dir)
  end
  if options.opts.firefox_profile_name ~= nil and options.opts.firefox_profile_name ~= "" then
    table.insert(args, "--firefox_profile_name")
    table.insert(args, options.opts.firefox_profile_name)
  end
  table.insert(args, "--jupyter_command")
  if type(options.opts.jupyter_command) == "string" then
    table.insert(args, options.opts.jupyter_command)
  elseif type(options.opts.jupyter_command) == "table" then
    for i, arg in pairs(options.opts.jupyter_command) do
      -- add space to escape args starting with dashes.
      table.insert(args, " " .. arg)
    end
  else
    error "Invalid jupyter_command type."
  end
  call_jupynium_cli(args, true)
end

function M.attach_to_server_cmd(args)
  local notebook_URL = vim.fn.trim(args.args)

  if notebook_URL == "" then
    notebook_URL = options.opts.default_notebook_URL
  end
  call_jupynium_cli({ "--attach_only", "--notebook_URL", notebook_URL }, true)
end

return M
