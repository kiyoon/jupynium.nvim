-- keymaps
function callIfCallable(f)
  return function(...)
    error, result = pcall(f, ...)
    if error then -- f exists and is callable
      -- print('ok')
      return result
    end
    return "not_callable"
  end
end

if callIfCallable(Jupynium_custom_keymaps)() == "not_callable" then
  vim.keymap.set({ "n" }, "<space>x", "<cmd>JupyniumExecuteCell<CR>")
  vim.keymap.set({ "n" }, "<space>X", "<cmd>JupyniumExecuteAllCells<cr>")
  vim.keymap.set({ "n" }, "<space>c", "<cmd>JupyniumClearOutput<CR>")
  vim.keymap.set({ "n" }, "<space>C", "<cmd>JupyniumClearAllOutput<cr>")
  vim.keymap.set({ "n" }, "<space>S", "<cmd>JupyniumScrollToCell<cr>")
  vim.keymap.set("", "<PageUp>", "<cmd>JupyniumScrollUp<cr>")
  vim.keymap.set("", "<PageDown>", "<cmd>JupyniumScrollDown<cr>")
end
