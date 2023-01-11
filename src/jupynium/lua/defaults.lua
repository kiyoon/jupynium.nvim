-- Set default values
-- It is not necessary but it's good for cleaning up logging messages.
-- Also it is useful for users to understand what values exist.

-- Option values. You can customise in your init.lua
if vim.g.jupynium_auto_download_ipynb == nil then
  vim.g.jupynium_auto_download_ipynb = true
end

if vim.g.jupynium_autoscroll_enable == nil then
  vim.g.jupynium_autoscroll_enable = true
end

if vim.g.jupynium_autoscroll_mode == nil then
  vim.g.jupynium_autoscroll_mode = "always"
end

if vim.g.jupynium_autoscroll_cell_top_margin_percent == nil then
  vim.g.jupynium_autoscroll_cell_top_margin_percent = true
end

if vim.g.jupynium_scroll_page_step == nil then
  vim.g.jupynium_scroll_page_step = 0.5
end

if vim.g.jupynium_scroll_cell_top_margin_percent == nil then
  vim.g.jupynium_scroll_cell_top_margin_percent = 20
end

-- max messages = max(vim.api.nvim_buf_line_count(all_buffer), vim.g.jupynium_num_max_msgs)
-- If we're processing more than this many events, ignore everything and perform full-sync instead.
-- However, the full-sync can be more expensive depending on how big the files are.
-- It's an old method I implemented to make things faster a little, but the current lazy processing seems to work much better so we can maybe deprecate this.
if vim.g.jupynium_num_max_msgs == nil then
  vim.g.jupynium_num_max_msgs = 1000
end

-- System values. You should not customise in your init.lua
-- These values are used for internal processing.
if vim.g.jupynium_channel_id == nil then
  vim.g.jupynium_channel_id = -1
end
