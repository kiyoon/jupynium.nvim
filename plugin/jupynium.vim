if !has('nvim-0.8')
  echohl WarningMsg
  echom "Jupynium needs Neovim >= 0.8"
  echohl None
  finish
endif

if !exists('g:__jupynium_setup_completed')
    lua require("jupynium").setup {}
endif

