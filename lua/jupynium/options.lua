local M = {}

M.opts = {}
M.default_opts = {
  -- Conda users:
  -- python_host = "~/miniconda3/envs/jupynium/bin/python"
  python_host = vim.g.python3_host_prog or "python3",

  default_notebook_URL = "localhost:8888",

  -- Write jupyter command but without "notebook"
  -- When you call :JupyniumStartAndAttachToServer and no notebook is open,
  -- then Jupynium will open the server for you using this command. (only when notebook_URL is localhost)
  jupyter_command = "jupyter",
  -- jupyter_command = "~/miniconda3/bin/jupyter",

  -- Used when notebook is launched by using jupyter_command.
  -- If nil or "", it will open at the git directory of the current buffer,
  -- but still navigate to the directory of the current buffer. (e.g. localhost:8888/tree/path/to/buffer)
  notebook_dir = nil,

  -- Used to remember the last session (password etc.).
  -- You may need to change the path.
  firefox_profiles_ini_path = vim.fn.isdirectory(vim.fn.expand "~/snap/firefox/common/.mozilla/firefox")
      and "~/snap/firefox/common/.mozilla/firefox/profiles.ini"
    or "~/.mozilla/firefox/profiles.ini",
  firefox_profile_name = nil, -- nil means the default profile

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

  use_default_keybindings = true,
  textobjects = {
    use_default_keybindings = true,
  },

  -- Dim all cells except the current one
  -- Related command :JupyniumShortsightedToggle
  shortsighted = false,
}

return M
