local augroup = vim.api.nvim_create_augroup("jupynium_global", { clear = true })
vim.api.nvim_create_autocmd({ "VimLeavePre" }, {
  -- Don't set the buffer. You can leave from another file.
  callback = function()
    if vim.fn.has "win32" == 1 then
      -- On Windows, when the VimLeavePre event is triggered, the rpc is not able to respond to the request.
      Jupynium_rpcnotify("VimLeavePre", 0)
    else
      Jupynium_rpcrequest("VimLeavePre", 0)
    end
  end,
  group = augroup,
})
