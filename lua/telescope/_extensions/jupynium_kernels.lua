local has_telescope, telescope = pcall(require, "telescope")
local main = require "telescope._extensions.jupynium_kernels.main"

if not has_telescope then
  -- error "This plugins requires nvim-telescope/telescope.nvim"
  return
end

return telescope.register_extension {
  -- setup = main.setup,
  exports = { jupynium_kernels = main.jupynium_kernels },
}
