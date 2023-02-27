local status, cmp = pcall(require, "cmp")
if not status then
  return
end

local source = {}

source.new = function()
  local self = setmetatable({}, { __index = source })
  return self
end

---Return whether this source is available in the current context or not (optional).
---@return boolean
function source:is_available()
  local bufnr = vim.api.nvim_get_current_buf()
  return Jupynium_syncing_bufs[bufnr] ~= nil
end

function source:get_debug_name()
  return "jupynium"
end

function source:get_trigger_characters()
  if vim.bo.filetype == "julia" then
    return { ".", "[", "'", '"', "%" }
  elseif vim.bo.filetype == "python" then
    return { ".", "[", "'", '"', "%" }
  elseif vim.bo.filetype == "r" then
    return { ".", "[", "'", '"', "%" }
  else
    return { ".", "[", "'", '"', "%" }
  end
end

---Invoke completion (required).
---@param params cmp.SourceCompletionApiParams
---@param callback fun(response: lsp.CompletionResponse|nil)
function source:complete(params, callback)
  -- (1, 0)-indexed
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
  -- 0-indexed
  local code_line = vim.api.nvim_buf_get_lines(0, row - 1, row, false)[1]

  Jupynium_kernel_complete_async(0, code_line, col, callback)
end

---Resolve completion item (optional). This is called right before the completion is about to be displayed.
---Useful for setting the text shown in the documentation window (`completion_item.documentation`).
---@param completion_item lsp.CompletionItem
---@param callback fun(completion_item: lsp.CompletionItem|nil)
function source:resolve(completion_item, callback)
  callback(completion_item)
end

---Executed after the item was selected.
---@param completion_item lsp.CompletionItem
---@param callback fun(completion_item: lsp.CompletionItem|nil)
function source:execute(completion_item, callback)
  callback(completion_item)
end

cmp.register_source("jupynium", source.new())
