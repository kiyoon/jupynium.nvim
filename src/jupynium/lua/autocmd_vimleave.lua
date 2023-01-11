local augroup = vim.api.nvim_create_augroup("jupynium_global", { clear = true })
vim.api.nvim_create_autocmd({ "VimLeavePre" }, {
  -- Don't set the buffer. You can leave from another file.
  callback = function()
    Jupynium_rpcrequest("VimLeavePre", 0)
  end,
  group = augroup,
})
