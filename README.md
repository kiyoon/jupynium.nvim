# Jupynium: Control Jupyter Notebook on Neovim with ZERO Compromise

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<a href="https://github.com/kiyoon/jupynium.nvim/actions/workflows/tests.yml">
<img src="https://github.com/kiyoon/jupynium.nvim/workflows/Tests/badge.svg?style=flat" />
</a>

**It's just like a markdown live preview, but it's Jupyter Notebook live preview!**

Jupynium uses Selenium to automate Jupyter Notebook, synchronising everything you type on Neovim.  
Never leave Neovim. Switch tabs on the browser as you switch files on Neovim.

Note that it doesn't sync from Notebook to Neovim so only modify from Neovim.

<img src=https://user-images.githubusercontent.com/12980409/221559945-46f12a38-2fb8-4156-bb94-b87e831ac8f5.gif width=100% />

## How does it work?

<img src=https://user-images.githubusercontent.com/12980409/211933889-e31e844c-1cf3-4d1a-acdc-70cb6e244ee4.png width=50% />

The Jupynium server will receive events from Neovim, keep the copy of the buffer and apply that to the Jupyter Notebook by using Selenium browser automation. It interacts only through the front end so it doesn't require installing extensions on the kernel etc., which makes it possible to:

- Develop locally, run remotely (or vice versa)
- Use university-hosted Jupyter Notebook
- Use any other languages / kernels such as R

## 🛠️ Installation

### Requirements

- 💻 Linux, macOS and Windows (CMD, PowerShell, WSL2)
- ✌️ Neovim >= v0.8
- 🦊 Firefox
  - Other browsers are not supported due to their limitation with Selenium (see [#49](https://github.com/kiyoon/jupynium.nvim/issues/49#issuecomment-1443304753))
- 🦎 Mozilla geckodriver
  - May already be installed with Firefox. Check `geckodriver -V`
- 🐍 Python >= 3.7
  - Supported Python installation methods include system-level and [Conda](https://docs.conda.io/en/latest/miniconda.html)
- 📔 Jupyter Notebook >= 6.2
  - Jupyter Lab is not supported
  - 
    ```sh
    # jupyter-console is optional and used for `:JupyniumKernelOpenInTerminal`
    pip install notebook nbclassic jupyter-console
    ```

#### Important note about Notebook 7 (breaking change!)
Jupynium does not support Notebook 7 yet. In the meantime, you can change the `default_notebook_URL = "localhost:8888/nbclassic"` in `require("jupynium").setup({ ... })` to use the classic (Notebook 6) interface with Jupynium. This is the new default setting from now on.

Don't forget to upgrade your notebook and install nbclassic (`pip install --upgrade notebook nbclassic`) when you set this.


### Install Python

Don't have system Python 3.7? You can use [Conda](https://docs.conda.io/en/latest/miniconda.html):

```bash
conda create -n jupynium python=3
conda activate jupynium
```

Upgrade pip. This solves many problems:

```bash
# pip >= 23.0 recommended
pip3 install --upgrade pip
```

### Install Jupynium

<details>
<summary>
Click to see vim-plug and packer installation.
</summary>

With vim-plug:

```vim
Plug 'kiyoon/jupynium.nvim', { 'do': 'pip3 install --user .' }
" Plug 'kiyoon/jupynium.nvim', { 'do': 'conda run --no-capture-output -n jupynium pip install .' }
Plug 'rcarriga/nvim-notify'   " optional
Plug 'stevearc/dressing.nvim' " optional, UI for :JupyniumKernelSelect
```

With packer.nvim:

```lua
use { "kiyoon/jupynium.nvim", run = "pip3 install --user ." }
-- use { "kiyoon/jupynium.nvim", run = "conda run --no-capture-output -n jupynium pip install ." }
use { "rcarriga/nvim-notify" }   -- optional
use { "stevearc/dressing.nvim" } -- optional, UI for :JupyniumKernelSelect
```
</details>

With 💤lazy.nvim:

```lua
  {
    "kiyoon/jupynium.nvim",
    build = "pip3 install --user .",
    -- build = "conda run --no-capture-output -n jupynium pip install .",
    -- enabled = vim.fn.isdirectory(vim.fn.expand "~/miniconda3/envs/jupynium"),
  },
  "rcarriga/nvim-notify",   -- optional
  "stevearc/dressing.nvim", -- optional, UI for :JupyniumKernelSelect
```

#### Configure Jupynium

The default configuration values are below and work well for system-level Python users. If you're a Conda user, you need to change `python_host` to execute using the `conda` command instead.

<details>
<summary>
Click to see the setup defaults
</summary>

```lua
require("jupynium").setup({
  --- For Conda environment named "jupynium",
  -- python_host = { "conda", "run", "--no-capture-output", "-n", "jupynium", "python" },
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
})

-- You can link highlighting groups.
-- This is the default (when colour scheme is unknown)
-- Try with CursorColumn, Pmenu, Folded etc.
vim.cmd [[
hi! link JupyniumCodeCellSeparator CursorLine
hi! link JupyniumMarkdownCellSeparator CursorLine
hi! link JupyniumMarkdownCellContent CursorLine
hi! link JupyniumMagicCommand Keyword
]]

-- Please share your favourite settings on other colour schemes, so I can add defaults.
-- Currently, tokyonight is supported.
```

</details>

#### Optionally, configure `nvim-cmp` to show Jupyter kernel completion

```lua
local cmp = require "cmp"
local compare = cmp.config.compare

cmp.setup {
  sources = {
    { name = "jupynium", priority = 1000 },  -- consider higher priority than LSP
    { name = "nvim_lsp", priority = 100 },
    -- ...
  },
  sorting = {
    priority_weight = 1.0,
    comparators = {
      compare.score,            -- Jupyter kernel completion shows prior to LSP
      compare.recently_used,
      compare.locality,
      -- ...
    },
  },
}
```

#### Optionally, configure `nvim-ufo` to fold cells

There is an API serving as a folds provider, which will return a table with format `{startLine=#num, endLine=#num}`.  

```lua
require("jupynium").get_folds()
```

You should use it with a fold plugin like [nvim-ufo](https://github.com/kevinhwang91/nvim-ufo).  
See [#88](https://github.com/kiyoon/jupynium.nvim/pull/88) for more detail and an example configuration.

## 🏃 Quick Start

- Open a `*.ju.py` file.
- Execute `:JupyniumStartAndAttachToServer`. This will open Jupyter Notebook on the Firefox browser.
  - If not, clarify option `jupyter_command` or just open the Notebook server by yourself: `jupyter notebook`
- Execute `:JupyniumStartSync`. This will create an `Untitled.ipynb` file on the browser.
- Now you can type `# %%` in Neovim to create a code cell.
  - You'll see everything you type below that will be synchronised in the browser.
  - Execute cells using the default keybind `<space>x`.

For detailed instructions, see Usage below.

## 🚦 Usage

There are 2 general steps to using Jupynium:

1. Setup a Jupynium file
2. Connect to the Jupynium server

The Jupynium server stays alive as long as the browser is alive. So you can see them as the same thing in this doc.
For example:

- Starting Jupynium server = opening a Selenium browser
- Manually closing the browser = closing the Jupynium server

### Setup a Jupynium file

Jupynium uses a Jupytext's percent format (see the `Jupynium file format` section below). This Jupytext file named `.ju.py` is what you will primarily be interacting with, rather than the `.ipynb` file directly. The contents of the Jupynium file are synced to the browser notebook where it can be viewed in real-time. If you want to keep a copy of the notebook, it can be downloaded as an `.ipynb` file later.

First, it's recommended to set a password on your notebook (rather than using tokens):

```console
$ jupyter notebook password
Enter password: 🔒

$ jupyter notebook    # leave notebook opened
```

#### If you want to start a new notebook

1. Manually create a local Jupynium file called `<filename>.ju.py`
2. Done! The rest happens after connecting to the server

#### If you want to open an existing notebook

There are currently 2 ways of converting an existing `.ipynb` file to a Jupynium file:

**Option 1**: Use an included command line tool:

```bash
ipynb2jupytext [-h] [--stdout] [--code_only] file.ipynb [file.ju.py]
```

If you're already familiar with Jupytext, feel free to use it instead.

**Option 2**: This method requires that you have already connected to the Jupynium server:

1. Open your `.ipynb` file in the web browser after connecting to the server
2. In a new Neovim buffer, run `:JupyniumLoadFromIpynbTab`. This will convert the contents of the notebook file to Jupynium format.
3. Save your buffer as `<filename>.ju.py`

When using Jupynium for the first time, it's recommended to start a new notebook to make sure everything works before trying to load existing files.

### Connect to the Jupynium server

(This is for local Neovim only. For remote Neovim, see [Command-Line Usage](#%EF%B8%8F-command-line-usage-attach-to-remote-neovim))

In Neovim, with your Jupynium `.ju.py` file open, you can run `:JupyniumStartAndAttachToServer` to start the notebook server.

#### Sync current buffer to the Jupynium server

You need to be on the main notebook page (file browser) for the next few steps.

Although Neovim is now attached to the server, it won't automatically start syncing.

To sync your Neovim Jupynium file to a notebook, run `:JupyniumStartSync`.

You can also:

- `:JupyniumStartSync filename` to give a name to the notebook (`filename.ipynb`) instead of `Untitled.ipynb`. This does not open existing files. If a file with that name already exists then the filename argument will just be ignored.
- To sync a Jupynium file to an existing notebook, manually open the file in the browser, and `:JupyniumStartSync 2` to sync to the 2nd tab (count from 1).

At this point, any changes you make within the Neovim Jupynium file will be reflected live in the browser. Make sure you do not make changes inside the browser itself, as the sync is only one-way (from Neovim to browser).

If you want to save a copy of the `.ipynb` file, run `:JupyniumDownloadIpynb`. There is also a configuration option to enable automatic downloading.

#### Sync multiple Jupynium files

You can sync multiple files at the same time. Simple run `:JupyniumStartSync` again with the new file you want to sync.

#### Use multiple Neovim

You can run `:JupyniumStartSync` on a new Neovim instance.  
If you have `auto_attach_to_server = false` during setup, you need to run `:JupyniumAttachToServer` and `:JupyniumStartSync`.

## 📝 Jupynium file format (.ju.py or .ju.\*)

The Jupynium file format follows Jupytext's percent format. In order for Jupynium to detect the files, name them as `*.ju.py` or specify `jupynium_file_pattern` in `require("jupynium").setup()`.

**Code cell:**  
Any code below this line (and before the next separator) will be the content of a code cell.

- `# %%`

**Magic commands**

- `# %time` becomes `%time` in notebook.
- If you want to really comment out magic commands, comment it two times like `## %time`.

**Markdown cell:**
Any code below this line will be markdown cell content.

- `# %% [md]`
- `# %% [markdown]`

In Python, the recommended way is to wrap the whole cell content as a multi-line string.

```python
# %% [md]
"""
# This is a markdown heading
This is markdown content
"""
```

In other languages like R, you'll need to comment every line.

```r
# %% [md]
# # This is a markdown heading
# This is markdown content
```

**Explicitly specify the first cell separator to use it like a notebook.**

- If there is one or more cells, it works as a notebook mode.
  - Contents before the first cell are ignored, so use it as a heading (shebang etc.)
- If there is no cell, it works as a markdown preview mode.
  - It will still open ipynb file but will one have one markdown cell.

## ⌨️ Keybindings

- `<space>x`: Execute selected cells
- `<space>c`: Clear selected cells
- `<PageUp>`, `<PageDown>`: Scroll notebook
- `<space>js`: Scroll to cell (if autoscroll is disabled)
- `<space>K`: Hover (inspect a variable)
- `<space>jo`: Toggle output scroll (when output is long)

If you want custom keymaps, add `use_default_keybindings = false` and follow `M.default_keybindings()` in [lua/jupynium/init.lua](lua/jupynium/init.lua).

### Textobjects

- `[j`, `]j`: go to previous / next cell separator
  - Repeat with `;` and `,` if you have [nvim-treesitter-textobjects](https://github.com/nvim-treesitter/nvim-treesitter-textobjects).
    Follow their instructions for keybindings for this.
- `<space>jj`: go to current cell separator
- `vaj`,`vij`, `vaJ`, `viJ`: select current cell
  - `a`: include separator, `i`: exclude separator
  - `j`: exclude next separator, `J`: include next separator

If you want custom keymaps, add `textobjects = { use_default_keybindings = false }` and follow `M.default_keybindings()` in [lua/jupynium/textobj.lua](lua/jupynium/textobj.lua).

## 📡 Available Vim Commands

```vim
" Server (only used when Neovim is local. See Command-Line Usage for remote neovim)
:JupyniumStartAndAttachToServer [notebook_URL]
:JupyniumStartAndAttachToServerInTerminal [notebook_URL]    " Useful for debugging
:JupyniumAttachToServer [notebook_URL]

" Sync
:JupyniumStartSync [filename / tab_index]
:JupyniumStopSync
:JupyniumLoadFromIpynbTab tab_index
:JupyniumLoadFromIpynbTabAndStartSync tab_index

" Notebook (while syncing)
:JupyniumSaveIpynb
:JupyniumDownloadIpynb [filename]
:JupyniumAutoDownloadIpynbToggle

:JupyniumScrollToCell
:JupyniumScrollUp
:JupyniumScrollDown
:JupyniumAutoscrollToggle

:JupyniumExecuteSelectedCells
:JupyniumClearSelectedCellsOutputs
:JupyniumToggleSelectedCellsOutputsScroll

:JupyniumKernelRestart
:JupyniumKernelInterrupt
:JupyniumKernelSelect
:JupyniumKernelHover      " See value like LSP hover
:JupyniumKernelOpenInTerminal [hostname] " Connect to kernel of synchronized notebook

" Highlight
:JupyniumShortsightedToggle
```

## Lua API

The core API is provided as a global function.

```lua
--- Execute javascript in the browser. It will switch to the correct tab before executing.
---@param bufnr: integer | nil If given, before executing the code it will switch to the tab of this buffer. Requires syncing in advance.
---@param code string Javascript code
---@return boolean, object: Success, response
Jupynium_execute_javascript(bufnr, code)
```

Example: get kernel name and language

```lua
-- Use bufnr=nil if you don't want to switch tab
local code = [[return [Jupyter.notebook.kernel.name, Jupyter.kernelselector.kernelspecs];]]
local status_ok, kernel_name_and_spec = Jupynium_execute_javascript(0, code)
if status_ok then
  local kernel_name = kernel_name_and_spec[1]   -- "python3"
  local kernel_spec = kernel_name_and_spec[2]
  local kernel_language = kernel_spec[kernel_name].spec.language  -- "python"
  local kernel_display_name = kernel_spec[kernel_name].spec.display_name  -- "Python 3 (ipykernel)"
end
```

## 👨‍💻️ Command-Line Usage (attach to remote Neovim)

**You don't need to install the vim plugin to use Jupynium.** The plugin is responsible of adding `:JupyniumStartAndAttachToServer` etc. that just calls the command line program, plus it has textobjects and shortsighted support.

Install Jupynium if you haven't already:

```bash
pip3 install jupynium
```

Open a python/markdown file with nvim and see `:echo v:servername`.  
Run Jupynium like:

```bash
jupynium --nvim_listen_addr /tmp/your_socket_path
```

Or, you can run Neovim like

```bash
nvim --listen localhost:18898 notebook.ju.py
```

Then start Jupynium as well as attaching the neovim to it.

```bash
jupynium --nvim_listen_addr localhost:18898
```

Note that you can attach to remote neovim by changing `localhost` to `servername.com` or using SSH port forwarding.

This will open Firefox with Selenium, defaulting to `http://localhost:8888/nbclassic`.

Additionally,

- You can run `jupynium` command multiple times to attach more than one Neovim instance.
- `jupynium --notebook_URL localhost:18888` to view different notebook.
- You can just run `jupynium` without arguments to just leave the server / browser running and wait for nvim to attach.

## ⚠️ Caution

The program is in the alpha stage. If it crashes it's likely that the whole browser turns off without saving!

### Rules

1. Always leave the home page accessible. Jupynium interacts with it to open files. Do not close, or move to another website.

- It's okay to move between directories.

2. It's OK to close the notebook pages. If you do so, it will stop syncing that buffer.
3. Changing tab ordering or making it to a separate window is OK.

## 🤔 FAQ

> 🌽 How do I use different languages / kernels?

Instead of `*.ju.py` if you make files named `*.ju.*` (e.g. `*.ju.r`) you will see all the keybindings and commands.  
All the procedures should be the same.

> The notebook content is not in sync with vim. How do I fix it?

You probably would have accidentally modified directly from the notebook.

1. If you want to keep the vim content and sync to the notebook, just <ins>add one more cell in the notebook and start making changes in vim</ins>. It works because Jupynium tries to only update the currently modified cell if the number of cells is the same in both. If it differs, it will fully update the entire content.
2. To keep the notebook content and load that to vim, run `:JupyniumLoadFromIpynbTab [tab_index]` without making changes on vim.

## 📰 Fun Facts

- I spent my whole Christmas and New Year holidays (and more) just making this plugin.
- This is the star history chart with relevant plugins. Thank you for helping it grow!

[![Star History Chart](https://api.star-history.com/svg?repos=kiyoon/jupynium.nvim,untitled-ai/jupyter_ascending,untitled-ai/jupyter_ascending.vim,dccsillag/magma-nvim,luk400/vim-jukit&type=Date)](https://star-history.com/#kiyoon/jupynium.nvim&untitled-ai/jupyter_ascending&untitled-ai/jupyter_ascending.vim&dccsillag/magma-nvim&luk400/vim-jukit&Date)
