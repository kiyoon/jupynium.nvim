import os
from pathlib import Path

import sysv_ipc

PACKAGE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

IPC_KEY = 32985427282198 % sysv_ipc.KEY_MAX
IPC_TYPE_ATTACH_NEOVIM = 1
