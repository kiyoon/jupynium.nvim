from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .buffer import JupyniumBuffer

if TYPE_CHECKING:
    import pynvim
    from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


@dataclass
class NvimInfo:
    """Information about the pynvim and Jupynium instance."""

    nvim: pynvim.Nvim
    home_window: str
    jupbufs: dict[int, JupyniumBuffer] = field(default_factory=dict)  # key = buffer ID
    window_handles: dict[int, str] = field(default_factory=dict)  # key = buffer ID
    auto_close_tab: bool = True

    def attach_buffer(self, buf_id: int, content: list[str], window_handle: str):
        if buf_id in self.jupbufs or buf_id in self.window_handles:
            logger.warning(f"Buffer {buf_id} is already attached")

        self.jupbufs[buf_id] = JupyniumBuffer(content)
        self.window_handles[buf_id] = window_handle

    def detach_buffer(self, buf_id: int, driver: WebDriver):
        if buf_id in self.jupbufs:
            del self.jupbufs[buf_id]
        if buf_id in self.window_handles:
            if (
                self.auto_close_tab
                and self.window_handles[buf_id] in driver.window_handles
            ):
                driver.switch_to.window(self.window_handles[buf_id])
                driver.close()
                driver.switch_to.window(self.home_window)
            del self.window_handles[buf_id]

    def check_window_alive_and_update(self, driver: WebDriver):
        detach_buffer_list = []
        for buf_id, window in self.window_handles.items():
            if window not in driver.window_handles:
                self.nvim.lua.Jupynium_notify.error(
                    [
                        "Notebook closed.",
                        f"Detaching the buffer {buf_id} from Jupynium..",
                    ],
                    "notebook_closed",
                    async_=True,
                )
                self.nvim.lua.Jupynium_stop_sync(buf_id)
                detach_buffer_list.append(buf_id)

        for buf_id in detach_buffer_list:
            self.detach_buffer(buf_id, driver)

    def close(self, driver: WebDriver):
        with contextlib.suppress(Exception):
            # Even if you fail it's not a big problem
            self.nvim.lua.Jupynium_reset_channel(async_=True)

        for buf_id in list(self.jupbufs.keys()):
            self.detach_buffer(buf_id, driver)

    def __len__(self):
        return len(self.jupbufs)
