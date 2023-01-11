local notify_ok, nvim_notify = pcall(require, "notify")

local PLUGIN_NAME = notify_ok and "Jupynium" or "Jupynium"

Jupynium_notify = {}

---Wraper for vim.notify and nvim-notify
---@param msg table
---@param level number vim.levels[level]
---@vararg string Strings for substitute
Jupynium_notify.notify = function(msg, level)
  level = level or vim.log.levels.INFO

  if notify_ok then
    -- Make it possible to use newline within the message table
    lines = {}
    for _, str in ipairs(msg) do
      for s in str:gmatch "[^\r\n]+" do
        table.insert(lines, s)
      end
    end

    nvim_notify(lines, level, {
      title = PLUGIN_NAME,
      on_open = function(win)
        local buf = vim.api.nvim_win_get_buf(win)
        vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
      end,
    })
  else
    vim.notify(("[%s]: %s"):format(PLUGIN_NAME, table.concat(msg, " ")), level)
  end
end

Jupynium_notify.error = function(msg)
  Jupynium_notify.notify(msg, vim.log.levels.ERROR)
end

Jupynium_notify.warn = function(msg)
  Jupynium_notify.notify(msg, vim.log.levels.WARN)
end

Jupynium_notify.info = function(msg)
  Jupynium_notify.notify(msg, vim.log.levels.INFO)
end
