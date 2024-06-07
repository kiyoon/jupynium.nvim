local notify_ok, nvim_notify = pcall(require, "notify")

Jupynium_notify = {}

---Wraper for vim.notify and nvim-notify
---@param msg string[]
---@param level number vim.levels[level]
---@param code string?
Jupynium_notify.notify = function(msg, level, code)
  level = level or vim.log.levels.INFO

  if code ~= nil and vim.g.jupynium_notify_ignore_codes[code] then
    return
  end

  local title
  if code ~= nil then
    title = ("Jupynium [%s]"):format(code)
  else
    title = "Jupynium"
  end

  if notify_ok then
    -- Make it possible to use newline within the message table
    local lines = {}
    for _, str in ipairs(msg) do
      for s in str:gmatch "[^\r\n]+" do
        table.insert(lines, s)
      end
    end

    nvim_notify(lines, level, {
      title = title,
      on_open = function(win)
        local buf = vim.api.nvim_win_get_buf(win)
        vim.bo[buf].filetype = "markdown"
      end,
    })
  else
    vim.notify(("%s: %s"):format(title, table.concat(msg, " ")), level)
  end
end

---@param msg string[]
---@param code string?
Jupynium_notify.error = function(msg, code)
  Jupynium_notify.notify(msg, vim.log.levels.ERROR, code)
end

---@param msg string[]
---@param code string?
Jupynium_notify.warn = function(msg, code)
  Jupynium_notify.notify(msg, vim.log.levels.WARN, code)
end

---@param msg string[]
---@param code string?
Jupynium_notify.info = function(msg, code)
  Jupynium_notify.notify(msg, vim.log.levels.INFO, code)
end
