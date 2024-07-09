---@alias Jupynium.NotifyCode "download_ipynb" | "error_download_ipynb" | "attach_and_init" | "error_close_main_page" | "notebook_closed"

---@class (exact) Jupynium.Config.AutoStartServer
---@field enable boolean
---@field file_pattern string[]

---@class (exact) Jupynium.Config.AutoAttachToServer
---@field enable boolean
---@field file_pattern string[]

---@class (exact) Jupynium.Config.AutoStartSync
---@field enable boolean
---@field file_pattern string[]

---@class (exact) Jupynium.Config.Scroll.Cell
---@field top_margin_percent number

---@class (exact) Jupynium.Config.Autoscroll
---@field enable boolean
---@field mode string
---@field cell Jupynium.Config.Scroll.Cell

---@class (exact) Jupynium.Config.Scroll.Page
---@field step number

---@class (exact) Jupynium.Config.Scroll
---@field page Jupynium.Config.Scroll.Page
---@field cell Jupynium.Config.Scroll.Cell

---@class (exact) Jupynium.Config.Textobjects
---@field use_default_keybindings boolean

---@class (exact) Jupynium.Config.SyntaxHighlight
---@field enable boolean

---@class (exact) Jupynium.Config.KernelHover.FloatingWinOpts
---@field max_width number
---@field border string

---@class (exact) Jupynium.Config.KernelHover
---@field floating_win_opts Jupynium.Config.KernelHover.FloatingWinOpts

---@class (exact) Jupynium.Config.Notify
---@field ignore Jupynium.NotifyCode[]

---@class (exact) Jupynium.Config
---@field python_host string|string[]
---@field default_notebook_URL string
---@field jupyter_command string|string[]
---@field notebook_dir string?
---@field firefox_profiles_ini_path string?
---@field firefox_profile_name string?
---@field auto_start_server Jupynium.Config.AutoStartServer
---@field auto_attach_to_server Jupynium.Config.AutoAttachToServer
---@field auto_start_sync Jupynium.Config.AutoStartSync
---@field auto_download_ipynb boolean
---@field auto_close_tab boolean
---@field autoscroll Jupynium.Config.Autoscroll
---@field scroll Jupynium.Config.Scroll
---@field jupynium_file_pattern string[]
---@field use_default_keybindings boolean
---@field textobjects Jupynium.Config.Textobjects
---@field syntax_highlight Jupynium.Config.SyntaxHighlight
---@field shortsighted boolean
---@field kernel_hover Jupynium.Config.KernelHover
---@field notify Jupynium.Config.Notify

---@class Jupynium.UserConfig.AutoStartServer
---@field enable boolean?
---@field file_pattern string[]?

---@class Jupynium.UserConfig.AutoAttachToServer
---@field enable boolean?
---@field file_pattern string[]?

---@class Jupynium.UserConfig.AutoStartSync
---@field enable boolean?
---@field file_pattern string[]?

---@class Jupynium.UserConfig.Scroll.Cell
---@field top_margin_percent number?

---@class Jupynium.UserConfig.Autoscroll
---@field enable boolean?
---@field mode string?
---@field cell Jupynium.UserConfig.Scroll.Cell?

---@class Jupynium.UserConfig.Scroll.Page
---@field step number?

---@class Jupynium.UserConfig.Scroll
---@field page Jupynium.UserConfig.Scroll.Page?
---@field cell Jupynium.UserConfig.Scroll.Cell?

---@class Jupynium.UserConfig.Textobjects
---@field use_default_keybindings boolean?

---@class Jupynium.UserConfig.SyntaxHighlight
---@field enable boolean?

---@class Jupynium.UserConfig.KernelHover.FloatingWinOpts
---@field max_width number?
---@field border string?

---@class Jupynium.UserConfig.KernelHover
---@field floating_win_opts Jupynium.UserConfig.KernelHover.FloatingWinOpts

---@class Jupynium.UserConfig.Notify
---@field ignore Jupynium.NotifyCode[]?

---@class Jupynium.UserConfig
---@field python_host string|string[]|nil
---@field default_notebook_URL string?
---@field jupyter_command string|string[]|nil
---@field notebook_dir string?
---@field firefox_profiles_ini_path string?
---@field firefox_profile_name string?
---@field auto_start_server Jupynium.UserConfig.AutoStartServer?
---@field auto_attach_to_server Jupynium.UserConfig.AutoAttachToServer?
---@field auto_start_sync Jupynium.UserConfig.AutoStartSync?
---@field auto_download_ipynb boolean?
---@field auto_close_tab boolean?
---@field autoscroll Jupynium.UserConfig.Autoscroll?
---@field scroll Jupynium.UserConfig.Scroll?
---@field jupynium_file_pattern string[]?
---@field use_default_keybindings boolean?
---@field textobjects Jupynium.UserConfig.Textobjects?
---@field syntax_highlight Jupynium.UserConfig.SyntaxHighlight?
---@field shortsighted boolean?
---@field kernel_hover Jupynium.UserConfig.KernelHover?
---@field notify Jupynium.UserConfig.Notify?

local M = {}

---@type Jupynium.Config
M.opts = {}

---@type Jupynium.Config
M.default_opts = {
  --- For Conda environment named "jupynium",
  -- python_host = { "conda", "run", "--no-capture-output", "-n", "jupynium", "python" },
  ---@type string|string[]
  python_host = vim.g.python3_host_prog or "python3",

  default_notebook_URL = "localhost:8888/nbclassic",

  -- Write jupyter command but without "notebook"
  -- When you call :JupyniumStartAndAttachToServer and no notebook is open,
  -- then Jupynium will open the server for you using this command. (only when notebook_URL is localhost)
  jupyter_command = "jupyter",
  --- For Conda, maybe use base environment
  --- then you can `conda install -n base nb_conda_kernels` to switch environment in Jupyter Notebook
  -- jupyter_command = { "conda", "run", "--no-capture-output", "-n", "base", "jupyter" },

  -- Used when notebook is launched by using jupyter_command.
  -- If nil or "", it will open at the git directory of the current buffer,
  -- but still navigate to the directory of the current buffer. (e.g. localhost:8888/nbclassic/tree/path/to/buffer)
  notebook_dir = nil,

  -- Used to remember the last session (password etc.).
  -- e.g. '~/.mozilla/firefox/profiles.ini'
  -- or '~/snap/firefox/common/.mozilla/firefox/profiles.ini'
  firefox_profiles_ini_path = nil,
  -- nil means the profile with Default=1
  -- or set to something like 'default-release'
  firefox_profile_name = nil,

  -- Open the Jupynium server if it is not already running
  -- which means that it will open the Selenium browser when you open this file.
  -- Related command :JupyniumStartAndAttachToServer
  auto_start_server = {
    enable = false,
    file_pattern = { "*.ju.*" },
  },

  -- Attach current nvim to the Jupynium server
  -- Without this step, you can't use :JupyniumStartSync
  -- Related command :JupyniumAttachToServer
  auto_attach_to_server = {
    enable = true,
    file_pattern = { "*.ju.*", "*.md" },
  },

  -- Automatically open an Untitled.ipynb file on Notebook
  -- when you open a .ju.py file on nvim.
  -- Related command :JupyniumStartSync
  auto_start_sync = {
    enable = false,
    file_pattern = { "*.ju.*", "*.md" },
  },

  -- Automatically keep filename.ipynb copy of filename.ju.py
  -- by downloading from the Jupyter Notebook server.
  -- WARNING: this will overwrite the file without asking
  -- Related command :JupyniumDownloadIpynb
  auto_download_ipynb = true,

  -- Automatically close tab that is in sync when you close buffer in vim.
  auto_close_tab = true,

  -- Always scroll to the current cell.
  -- Related command :JupyniumScrollToCell
  autoscroll = {
    enable = true,
    mode = "always", -- "always" or "invisible"
    cell = {
      top_margin_percent = 20,
    },
  },

  scroll = {
    page = { step = 0.5 },
    cell = {
      top_margin_percent = 20,
    },
  },

  -- Files to be detected as a jupynium file.
  -- Add highlighting, keybindings, commands (e.g. :JupyniumStartAndAttachToServer)
  -- Modify this if you already have lots of files in Jupytext format, for example.
  jupynium_file_pattern = { "*.ju.*" },

  use_default_keybindings = true,
  textobjects = {
    use_default_keybindings = true,
  },

  syntax_highlight = {
    enable = true,
  },

  -- Dim all cells except the current one
  -- Related command :JupyniumShortsightedToggle
  shortsighted = false,

  -- Configure floating window options
  -- Related command :JupyniumKernelHover
  kernel_hover = {
    floating_win_opts = {
      max_width = 84,
      border = "none",
    },
  },

  notify = {
    ignore = {
      -- "download_ipynb",
      -- "error_download_ipynb",
      -- "attach_and_init",
      -- "error_close_main_page",
      -- "notebook_closed",
    },
  },
}

return M
