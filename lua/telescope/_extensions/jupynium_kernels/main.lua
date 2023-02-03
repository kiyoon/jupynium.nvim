local pickers = require "telescope.pickers"
local finders = require "telescope.finders"
local actions = require "telescope.actions"
local action_state = require "telescope.actions.state"
local conf = require("telescope.config").values

local M = {}

M.setup = function(setup_config)
  --
end

M.jupynium_kernels = function(opts)
  opts = opts or {}
  local status, jupynium_kernel_name_and_spec = pcall(Jupynium_get_kernel_spec)
  if not status then
    error "Jupynium not installed or attached."
    return false
  end

  if jupynium_kernel_name_and_spec == nil then
    -- it should have already errored out with notification.
    return false
  end

  local current_kernel_name = jupynium_kernel_name_and_spec[1]
  local jupynium_kernel_spec = jupynium_kernel_name_and_spec[2]

  -- Example:
  -- local jupynium_kernels = { "python3", "conda-env-jupynium-py" } -- first one is default
  -- local jupynium_kernels_disp = {
  --   ["conda-env-jupynium-py"] = "Python [conda env: jupynium]",
  --   ["python3"] = "Python 3 (ipykernel)",
  -- }
  local jupynium_kernels, jupynium_kernels_disp = {}, {}
  for kernel_name, kern in pairs(jupynium_kernel_spec) do
    -- filter by language
    if kern.spec.language:lower() == vim.bo.filetype then
      if kernel_name ~= current_kernel_name then
        table.insert(jupynium_kernels, kernel_name)
      else
        -- current kernel is always first (default)
        table.insert(jupynium_kernels, 1, kernel_name)
      end
      jupynium_kernels_disp[kernel_name] = kern.spec.display_name
    end
  end

  if jupynium_kernels[1] ~= current_kernel_name then
    -- by applying filtering, we dropped the current kernel.
    -- cancel the filtering and include everything.
    jupynium_kernels = {}
    jupynium_kernels_disp = {}
    for kernel_name, kern in pairs(jupynium_kernel_spec) do
      if kernel_name ~= current_kernel_name then
        table.insert(jupynium_kernels, kernel_name)
      else
        -- current kernel is always first (default)
        table.insert(jupynium_kernels, 1, kernel_name)
      end
      jupynium_kernels_disp[kernel_name] = kern.spec.display_name
    end
  end

  local jupynium_finder = function()
    local jupynium_maker = function(entry)
      local disp = jupynium_kernels_disp[entry]

      return { value = entry, display = disp, ordinal = disp }
    end

    return finders.new_table { results = jupynium_kernels, entry_maker = jupynium_maker }
  end

  pickers
    .new(opts, {
      prompt_title = "Select a kernel for Jupynium (Jupyter)",
      results_title = "Jupyter Kernels for Notebook",
      finder = jupynium_finder(),
      sorter = conf.generic_sorter(opts),

      attach_mappings = function(prompt_bufnr, map)
        actions.select_default:replace(function()
          actions.close(prompt_bufnr)
          local selection = action_state.get_selected_entry()
          Jupynium_change_kernel(0, selection.value)
        end)
        return true
      end,
    })
    :find()
end

return M
