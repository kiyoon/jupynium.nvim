from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from jupynium import pynvim_helpers
from jupynium.buffer import JupyniumBuffer


@pytest.fixture(scope="session")
def jupbuf1():
    return JupyniumBuffer(["a", "b", "c", "# %% [markdown]", "# d", "# %%", "f"])


@pytest.fixture(scope="session")
def nvim_1():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "nvim")
        nvim_proc = subprocess.Popen(
            ["nvim", "--clean", "--headless", "--listen", path]
        )
        # os.system(f"nvim --clean --headless --listen {path} &")
        nvim = pynvim_helpers.attach_and_init(path)

        yield nvim

        # Teardown

        # nvim.quit() sometimes hangs
        nvim_proc.kill()
