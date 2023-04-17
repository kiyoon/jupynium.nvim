vim.api.nvim_create_user_command("JupyniumStartSync", Jupynium_start_sync_cmd, { nargs = "?" })
vim.api.nvim_create_user_command("JupyniumLoadFromIpynbTab", Jupynium_load_from_ipynb_tab_cmd, { nargs = 1 })
vim.api.nvim_create_user_command(
  "JupyniumLoadFromIpynbTabAndStartSync",
  Jupynium_load_from_ipynb_tab_and_start_sync_cmd,
  { nargs = 1 }
)
vim.api.nvim_create_user_command("JupyniumStopSync", "lua Jupynium_stop_sync()", {})
vim.api.nvim_create_user_command("JupyniumExecuteSelectedCells", "lua Jupynium_execute_selected_cells()", {})
vim.api.nvim_create_user_command("JupyniumClearSelectedCellsOutputs", "lua Jupynium_clear_selected_cells_outputs()", {})
vim.api.nvim_create_user_command(
  "JupyniumToggleSelectedCellsOutputsScroll",
  "lua Jupynium_toggle_selected_cells_outputs_scroll()",
  {}
)
vim.api.nvim_create_user_command("JupyniumScrollToCell", "lua Jupynium_scroll_to_cell()", {})
vim.api.nvim_create_user_command("JupyniumSaveIpynb", "lua Jupynium_save_ipynb()", {})
vim.api.nvim_create_user_command("JupyniumDownloadIpynb", Jupynium_download_ipynb_cmd, { nargs = "?" })
vim.api.nvim_create_user_command("JupyniumAutoDownloadIpynbToggle", "lua Jupynium_auto_download_ipynb_toggle()", {})
vim.api.nvim_create_user_command("JupyniumScrollUp", "lua Jupynium_scroll_up()", {})
vim.api.nvim_create_user_command("JupyniumScrollDown", "lua Jupynium_scroll_down()", {})
vim.api.nvim_create_user_command("JupyniumAutoscrollToggle", "lua Jupynium_autoscroll_toggle()", {})

---@deprecated
vim.api.nvim_create_user_command("JupyniumRestartKernel", "lua Jupynium_restart_kernel()", {})
vim.api.nvim_create_user_command("JupyniumSelectKernel", "lua Jupynium_select_kernel()", {})

vim.api.nvim_create_user_command("JupyniumKernelRestart", "lua Jupynium_kernel_restart()", {})
vim.api.nvim_create_user_command("JupyniumKernelInterrupt", "lua Jupynium_kernel_interrupt()", {})
vim.api.nvim_create_user_command("JupyniumKernelSelect", "lua Jupynium_kernel_select()", {})
vim.api.nvim_create_user_command("JupyniumKernelHover", "lua Jupynium_kernel_hover()", {})
vim.api.nvim_create_user_command("JupyniumKernelOpenInTerminal", Jupynium_kernel_connect_cmd, { nargs = "?" })
