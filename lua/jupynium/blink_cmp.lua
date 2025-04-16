--- @module 'blink.cmp'
--- @class blink.cmp.Source
local source = {}

-- `opts` table comes from `sources.providers.your_provider.opts`
-- You may also accept a second argument `config`, to get the full
-- `sources.providers.your_provider` table
function source.new(opts)
  local self = setmetatable({}, { __index = source })
  return self
end

-- (Optional) Enable the source in specific contexts only
function source:enabled()
  -- if the global variable Jupynium_syncing_bufs is not defined, return false
  if Jupynium_syncing_bufs == nil then
    return false
  end

  local bufnr = vim.api.nvim_get_current_buf()
  return Jupynium_syncing_bufs[bufnr] ~= nil
end

-- (Optional) Non-alphanumeric characters that trigger the source
function source:get_trigger_characters()
  if vim.bo.filetype == "julia" then
    return { ".", "[", "'", '"', "%", "/" }
  elseif vim.bo.filetype == "python" then
    return { ".", "[", "'", '"', "%", "/" }
  elseif vim.bo.filetype == "r" then
    return { ".", "[", "'", '"', "%", "/" }
  else
    return { ".", "[", "'", '"', "%", "/" }
  end
end

function source:get_completions(ctx, callback)
  -- ctx (context) contains the current keyword, cursor position, bufnr, etc.

  -- You should never filter items based on the keyword, since blink.cmp will
  -- do this for you

  -- (1, 0)-indexed
  local _, col = ctx.get_cursor()
  local code_line = ctx.get_line()
  Jupynium_kernel_complete_async(ctx.bufnr, code_line, col, callback, "blink")

  -- (Optional) Return a function which cancels the request
  -- If you have long running requests, it's essential you support cancellation
  return function() end
end

-- (Optional) Before accepting the item or showing documentation, blink.cmp will call this function
-- so you may avoid calculating expensive fields (i.e. documentation) for only when they're actually needed
-- function source:resolve(item, callback)
-- end

-- Called immediately after applying the item's textEdit/insertText
-- function source:execute(ctx, item, callback, default_implementation)
-- end

return source
