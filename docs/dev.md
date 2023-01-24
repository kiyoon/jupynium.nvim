# Dev note

## Structure

There are largely two (or three) parts of the plugin:

1. CLI written in python in `src/`  
   a. The CLI also contains lua files in `src/jupynium/lua/`.
2. nvim plugin in `lua/`

The CLI (1) does everything and you can operate Jupynium perfectly fine without even installing (2) using a plugin manager like vim-plug.

The reason for this design is that we don't know what kind of nvim we're attaching to (it can be remote nvim) and the CLI version and plugin version always have to match, if we define functions in the plugin (2). Therefore, we make as least relationship with (1) and (2) as possible so it is compatible in most situations.

(1) is in charge of

- Opening selenium browser and syncing / controlling

(1a) is in charge of

- Defining lua functions and nvim commands for python CLI to use to interact with nvim.
- Most events like start sync, stop sync, execute cells, ... all just send RPC events to the CLI.

(2) is in charge of

- Detecting file extension and define commands like `:JupyniumStartAndAttachToServer` to call (1) to open the Jupynium server / selenium browser.
- Text objects
- Short-sighted (dimming cells not in focus)
