from __future__ import annotations

import dataclasses
import json
import logging
import os
from dataclasses import dataclass

from pkg_resources import resource_stream
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
)
from selenium.webdriver.common.by import By

from . import selenium_helpers as sele
from .buffer import JupyniumBuffer
from .ipynb import cells_to_jupy
from .nvim import NvimInfo
from .rpc_messages import len_pending_messages, receive_message

logger = logging.getLogger(__name__)


update_cell_selection_js_code = (
    resource_stream("jupynium", "js/update_cell_selection.js").read().decode("utf-8")
)

get_cell_inputs_js_code = (
    resource_stream("jupynium", "js/get_cell_inputs.js").read().decode("utf-8")
)


@dataclass
class OnLinesArgs:
    lines: list[str]
    start_row: int
    old_end_row: int
    new_end_row: int

    # Optimisations
    def is_chainable(self, other: "OnLinesArgs") -> bool:
        return (
            self.start_row == other.start_row and self.new_end_row == other.old_end_row
        )

    def chain(self, other: "OnLinesArgs") -> "OnLinesArgs":
        assert self.is_chainable(other)
        return OnLinesArgs(
            other.lines,
            self.start_row,
            self.old_end_row,
            other.new_end_row,
        )


@dataclass
class UpdateSelectionArgs:
    cursor_pos_row: int
    visual_start_row: int


@dataclass
class PrevLazyArgs:
    """
    Args that haven't been processed yet.
    """

    on_lines_args: OnLinesArgs | None = None
    update_selection_args: UpdateSelectionArgs | None = None

    def process(self, nvim_info: NvimInfo, driver, bufnr) -> None:
        if self.on_lines_args is not None:
            process_on_lines_event(nvim_info, driver, bufnr, self.on_lines_args)
            self.on_lines_args = None
        if self.update_selection_args is not None:
            update_cell_selection(nvim_info, driver, bufnr, self.update_selection_args)
            self.update_selection_args = None


@dataclass
class PrevLazyArgsPerBuf:
    """
    Keep separate lazy procedures per buffer.
    """

    data: dict[int, PrevLazyArgs] = dataclasses.field(default_factory=dict)

    def process(self, bufnr: int, nvim_info: NvimInfo, driver) -> None:
        if bufnr in self.data:
            self.data[bufnr].process(nvim_info, driver, bufnr)

    def process_all(self, nvim_info: NvimInfo, driver) -> None:
        for bufnr, lazy_args in self.data.items():
            lazy_args.process(nvim_info, driver, bufnr)
        self.data.clear()

    def lazy_on_lines_event(
        self, nvim_info: NvimInfo, driver, bufnr: int, on_lines_args: OnLinesArgs
    ) -> None:
        if bufnr not in self.data:
            self.data[bufnr] = PrevLazyArgs()

        self.data[bufnr].on_lines_args = lazy_on_lines_event(
            nvim_info, driver, bufnr, self.data[bufnr].on_lines_args, on_lines_args
        )

    def overwrite_update_selection(
        self,
        bufnr: int,
        update_selection_args: UpdateSelectionArgs,
    ) -> None:
        """
        Simply ignore the previous update selection and overwrite to the current one.
        """
        if bufnr not in self.data:
            self.data[bufnr] = PrevLazyArgs()

        self.data[bufnr].update_selection_args = update_selection_args


def process_events(nvim_info: NvimInfo, driver):
    """
    Controls events for a single nvim, and a single cycle of events.

    For example, if there are pending messages do process them all.

    Returns:
        bool status: False if nvim needs to be cleared up.
        rpcrequest event: Notify nvim after cleared up. None if status==True or no need to notify
    """
    # Check if the browser is still alive
    if nvim_info.home_window not in driver.window_handles:
        nvim_info.nvim.lua.Jupynium_notify.error(
            ["Do not close the main page. Detaching the nvim from Jupynium.."],
            async_=True,
        )
        return False, None

    # Check for each buffer
    nvim_info.check_window_alive_and_update(driver)

    # Receive message from this nvim
    # vim.g.jupynium_num_pending_msgs is not reliable
    # but so far it seems to be always smaller than the actual number of pending messages

    prev_lazy_args_per_buf = PrevLazyArgsPerBuf()
    while (
        len_pending_messages(nvim_info.nvim) > 0
        or nvim_info.nvim.vars["jupynium_num_pending_msgs"] > 0
    ):
        event = receive_message(nvim_info.nvim)
        logger.info(f"Event from nvim: {event}")

        if event is None:
            logger.error("Received event=None")
            return False, None

        assert event[1] is not None
        assert event[2] is not None

        if event[0] == "request":
            status, request_event = process_request_event(nvim_info, driver, event)
            if not status:
                return False, request_event
        else:
            # process and update prev_lazy_args
            process_notification_event(nvim_info, driver, event, prev_lazy_args_per_buf)

    # After the loop (here) you need to process the last on_lines event.
    prev_lazy_args_per_buf.process_all(nvim_info, driver)

    return True, None


def start_sync_with_filename(
    bufnr: int,
    filename: str,
    ask: bool,
    content: list[str],
    nvim_info: NvimInfo,
    driver,
):
    """
    Start sync using a filename (not tab index)
    filename has to end with .ipynb
    """
    driver.switch_to.window(nvim_info.home_window)
    sele.wait_until_notebook_list_loaded(driver)

    if filename == "":
        file_found = False
    else:
        notebook_items = driver.find_elements(
            By.CSS_SELECTOR, "#notebook_list > div > div"
        )
        file_found = False
        for notebook_item in notebook_items:
            # is notebook?
            try:
                notebook_item.find_element(By.CSS_SELECTOR, "i.notebook_icon")
            except NoSuchElementException:
                continue

            try:
                notebook_elem = notebook_item.find_element(By.CSS_SELECTOR, "a > span")
            except NoSuchElementException:
                continue
            notebook_name = notebook_elem.text
            if notebook_name == filename:
                prev_windows = set(driver.window_handles)
                driver.execute_script("arguments[0].scrollIntoView();", notebook_elem)
                notebook_elem.click()
                file_found = True
                sele.wait_until_new_window(driver, prev_windows)
                break

    if file_found:
        new_window = set(driver.window_handles) - set(prev_windows)
        assert len(new_window) == 1
        new_window = new_window.pop()

        driver.switch_to.window(new_window)
        sele.wait_until_notebook_loaded(driver)

        if ask:
            sync_input = nvim_info.nvim.eval(
                """input("Press 'v' to sync from n[v]im, 'i' to load from [i]pynb and sync. (v/i/[c]ancel): ")"""
            )
            sync_input = str(sync_input).strip()
        else:
            # if ask == False, sync from vim to ipynb
            sync_input = "v"

        if sync_input in ["v", "V"]:
            # Start sync from vim to ipynb tab
            nvim_info.attach_buffer(bufnr, content, new_window)
            nvim_info.jupbufs[bufnr].full_sync_to_notebook(driver)
        elif sync_input in ["i", "I"]:
            # load from ipynb tab and start sync
            cell_types, texts = driver.execute_script(get_cell_inputs_js_code)
            jupy = cells_to_jupy(cell_types, texts)
            nvim_info.nvim.buffers[bufnr][:] = jupy

            nvim_info.attach_buffer(bufnr, jupy, new_window)
    else:
        new_btn = driver.find_element(By.ID, "new-buttons")
        driver.execute_script("arguments[0].scrollIntoView(true);", new_btn)
        python_btn = driver.find_element(By.ID, "kernel-python3")
        prev_windows = set(driver.window_handles)
        try:
            python_btn.click()
        except ElementNotInteractableException:
            new_btn.click()
            python_btn.click()

        sele.wait_until_new_window(driver, prev_windows)
        new_window = set(driver.window_handles) - prev_windows
        assert len(new_window) == 1
        new_window = new_window.pop()

        driver.switch_to.window(new_window)
        sele.wait_until_notebook_loaded(driver)
        if filename != "":
            driver.execute_script(
                "Jupyter.notebook.rename(arguments[0]);",
                filename,
            )
        # start sync
        nvim_info.attach_buffer(bufnr, content, driver.current_window_handle)
        nvim_info.jupbufs[bufnr].full_sync_to_notebook(driver)


def process_request_event(nvim_info: NvimInfo, driver, event):
    """
    Returns:
        status (bool)
        request_event (rpcrequest event) to notify nvim after cleared up. None if no need to notify
    """
    assert event[0] == "request"
    # Request from nvim
    # send back response

    bufnr = event[2][0]
    event_args = event[2][1:]

    if event[1] == "start_sync":
        filename, ask, content = event_args
        filename = filename.strip()

        filename: str
        if not filename.isnumeric():
            if filename != "" and not filename.lower().endswith(".ipynb"):
                filename += ".ipynb"

            start_sync_with_filename(bufnr, filename, ask, content, nvim_info, driver)
        else:
            # start sync with tab index
            tab_idx = int(filename)
            driver.switch_to.window(driver.window_handles[tab_idx - 1])

            continue_input = "y"
            if ask:
                continue_input = nvim_info.nvim.eval(
                    "input('This will remove all content from the Notebook. Continue? (y/n): ')"
                )
            if continue_input in ["y", "Y"]:
                nvim_info.attach_buffer(bufnr, content, driver.current_window_handle)
                nvim_info.jupbufs[bufnr].full_sync_to_notebook(driver)
            else:
                event[3].send("N")
                event[3] = None
    elif event[1] == "load_from_ipynb_tab":
        (tab_idx,) = event_args
        if tab_idx > len(driver.window_handles) or tab_idx < 1:
            nvim_info.nvim.lua.Jupynium_notify.error(
                [f"Tab {tab_idx} doesn't exist."],
                async_=True,
            )
            event[3].send("N")
            return False, None
        driver.switch_to.window(driver.window_handles[tab_idx - 1])

        cell_types, texts = driver.execute_script(get_cell_inputs_js_code)
        jupy = cells_to_jupy(cell_types, texts)
        nvim_info.nvim.buffers[bufnr][:] = jupy
        logger.info(f"Loaded ipynb to the nvim buffer.")

    elif event[1] == "VimLeavePre":
        logger.info("Nvim closed. Clearing nvim")
        return False, event[3]

    if event[3] is not None:
        event[3].send("OK")

    return True, None


def skip_bloated(nvim_info: NvimInfo):
    if nvim_info.nvim.vars["jupynium_message_bloated"]:
        logger.info("Message bloated. Skipping..")
        if len_pending_messages(nvim_info.nvim) == 0:
            nvim_info.nvim.vars["jupynium_num_pending_msgs"] = 0
            nvim_info.nvim.vars["jupynium_message_bloated"] = False

            logger.info("Reloading all buffers from nvim")
            for buf_id in nvim_info.jupbufs.keys():
                nvim_info.nvim.lua.Jupynium_grab_entire_buffer(buf_id)

        return True
    return False


def lazy_on_lines_event(
    nvim_info: NvimInfo,
    driver,
    bufnr: int,
    previous_on_lines: OnLinesArgs | None,
    current_on_lines: OnLinesArgs,
):
    """
    Lazy-process on_lines events.
    ----
    Often, completion plugins like coc.nvim and nvim-cmp spams on_lines events.
    But they will have the same (bufnr, start_row, old_end_row, new_end_row) values.
    If the series of line changes are chainable, we can just process the last one.
    In order to do that, process the previous on_lines only if current on_lines is not chainable.
    After the loop you need to process the last one as well.
    """
    if previous_on_lines is None:
        return current_on_lines

    if previous_on_lines.is_chainable(current_on_lines):
        return previous_on_lines.chain(current_on_lines)

    process_on_lines_event(nvim_info, driver, bufnr, previous_on_lines)
    return current_on_lines


def process_on_lines_event(
    nvim_info: NvimInfo, driver, bufnr, on_lines_args: OnLinesArgs
):
    driver.switch_to.window(nvim_info.window_handles[bufnr])

    nvim_info.jupbufs[bufnr].process_on_lines(
        driver,
        True,
        on_lines_args.lines,
        on_lines_args.start_row,
        on_lines_args.old_end_row,
        on_lines_args.new_end_row,
    )


# flake8: noqa: C901
def process_notification_event(
    nvim_info: NvimInfo,
    driver,
    event,
    prev_lazy_args_per_buf: PrevLazyArgsPerBuf | None = None,
):
    assert event[0] == "notification"

    if skip_bloated(nvim_info):
        return

    bufnr = event[2][0]
    event_args = event[2][1:]
    if event[1] == "on_lines":
        current_on_lines = OnLinesArgs(*event_args)

        if prev_lazy_args_per_buf is None:
            process_on_lines_event(nvim_info, driver, bufnr, current_on_lines)
        else:
            prev_lazy_args_per_buf.lazy_on_lines_event(
                nvim_info, driver, bufnr, current_on_lines
            )
    elif event[1] in [
        "CursorMoved",
        "CursorMovedI",
        "visual_enter",
        "visual_leave",
    ]:
        current_args = UpdateSelectionArgs(*event_args)

        if prev_lazy_args_per_buf is not None:
            # Lazy. Process at the end of event loop cycle or if needed for the next event.
            prev_lazy_args_per_buf.overwrite_update_selection(bufnr, current_args)
        else:
            update_cell_selection(nvim_info, driver, bufnr, current_args)
    else:
        # For all the other events, it requires lazy events to be performed in advance.
        if prev_lazy_args_per_buf is not None:
            prev_lazy_args_per_buf.process(bufnr, nvim_info, driver)

        if event[1] == "scroll_ipynb":
            (scroll,) = event_args
            driver.switch_to.window(nvim_info.window_handles[bufnr])

            driver.execute_script(
                "Jupyter.notebook.scroll_manager.animation_speed = 0; Jupyter.notebook.scroll_manager.scroll_some(arguments[0]);",
                scroll,
            )
        elif event[1] == "save_ipynb":
            driver.switch_to.window(nvim_info.window_handles[bufnr])

            driver.execute_script("Jupyter.notebook.save_notebook();")
            driver.execute_script("Jupyter.notebook.save_checkpoint();")
        elif event[1] == "BufWritePre":
            (buf_filepath,) = event_args
            driver.switch_to.window(nvim_info.window_handles[bufnr])

            driver.execute_script("Jupyter.notebook.save_notebook();")
            driver.execute_script("Jupyter.notebook.save_checkpoint();")

            if (
                ".ju." in buf_filepath
                and nvim_info.nvim.vars["jupynium_auto_download_ipynb"]
            ):
                output_ipynb_path = os.path.splitext(buf_filepath)[0]
                output_ipynb_path = os.path.splitext(output_ipynb_path)[0]
                output_ipynb_path += ".ipynb"

                download_ipynb(driver, nvim_info, bufnr, output_ipynb_path)
        elif event[1] == "download_ipynb":
            (buf_filepath, filename) = event_args
            assert buf_filepath != ""

            if filename is not None and filename != "":
                if os.path.isabs(filename):
                    output_ipynb_path = filename
                else:
                    output_ipynb_path = os.path.join(
                        os.path.dirname(buf_filepath), filename
                    )

                if not output_ipynb_path.endswith(".ipynb"):
                    output_ipynb_path += ".ipynb"
            else:
                output_ipynb_path = os.path.splitext(buf_filepath)[0]
                output_ipynb_path = os.path.splitext(output_ipynb_path)[0]
                output_ipynb_path += ".ipynb"

            download_ipynb(driver, nvim_info, bufnr, output_ipynb_path)

        elif event[1] == "toggle_selected_cells_outputs_scroll":
            driver.switch_to.window(nvim_info.window_handles[bufnr])
            driver.execute_script(
                "Jupyter.notebook.toggle_cells_outputs_scroll(Jupyter.notebook.get_selected_cells_indices())"
            )
        elif event[1] == "execute_selected_cells":
            driver.switch_to.window(nvim_info.window_handles[bufnr])
            driver.execute_script("Jupyter.notebook.execute_selected_cells();")
        elif event[1] == "clear_selected_cells_outputs":
            driver.switch_to.window(nvim_info.window_handles[bufnr])
            driver.execute_script(
                "Jupyter.notebook.clear_cells_outputs(Jupyter.notebook.get_selected_cells_indices())"
            )
            # driver.execute_script("Jupyter.notebook.clear_output();")
        elif event[1] == "scroll_to_cell":
            (cursor_pos_row,) = event_args
            scroll_to_cell(driver, nvim_info, bufnr, cursor_pos_row)

        elif event[1] == "grab_entire_buf":
            # Refresh entire buffer from nvim
            # But do not necessarily sync to Jupyter Notebook
            # because it happens when you spam events and it slows down.
            (content,) = event_args

            nvim_info.jupbufs[bufnr] = JupyniumBuffer(content)
            if driver.current_window_handle == nvim_info.window_handles[bufnr]:
                nvim_info.jupbufs[bufnr].full_sync_to_notebook(driver)

        elif event[1] == "BufWinLeave":
            logger.info("Buffer closed on nvim. Closing on Jupyter Notebook")
            # driver.switch_to.window(nvim_info.window_handles[buf])
            # driver.close()
            nvim_info.detach_buffer(bufnr, driver)

        elif event[1] == "stop_sync":
            logger.info(f"Received stop_sync request: bufnr = {bufnr}")
            nvim_info.detach_buffer(bufnr, driver)


def update_cell_selection(
    nvim_info: NvimInfo, driver, bufnr, update_selection_args: UpdateSelectionArgs
):

    cursor_pos_row, visual_start_row = dataclasses.astuple(update_selection_args)

    if nvim_info.jupbufs[bufnr].num_cells == 1:
        # No autoscroll for markdown mode
        driver.switch_to.window(nvim_info.window_handles[bufnr])
    else:
        # Which cell?
        try:
            cell_index, _, _ = nvim_info.jupbufs[bufnr].get_cell_index_from_row(
                cursor_pos_row
            )
        except IndexError:
            if cursor_pos_row == nvim_info.jupbufs[bufnr].num_rows:
                # Nvim 0.8.1 has a bug where it
                # doesn't send on_byte event but it
                # sends CursorMoved event when
                # you create a new line with 'o' at the end of file.
                # So we have to manually add a new line
                nvim_info.jupbufs[bufnr].buf.append("")
                nvim_info.jupbufs[bufnr].process_on_lines(
                    driver,
                    True,
                    [""],
                    nvim_info.jupbufs[bufnr].num_rows,
                    nvim_info.jupbufs[bufnr].num_rows,
                    nvim_info.jupbufs[bufnr].num_rows + 1,
                )
                cell_index, _, _ = nvim_info.jupbufs[bufnr].get_cell_index_from_row(
                    cursor_pos_row
                )
            else:
                logger.exception("Cannot find cell index given row")
                return

        cell_index_visual, _, _ = nvim_info.jupbufs[bufnr].get_cell_index_from_row(
            visual_start_row
        )

        # select the cell
        # 0-th cell is not a cell, but it's the header. You can put anything above and it won't be synced to Jupyter Notebook.
        cell_index = max(cell_index - 1, 0)
        cell_index_visual = max(cell_index_visual - 1, 0)

        driver.switch_to.window(nvim_info.window_handles[bufnr])

        selection_updated = driver.execute_script(
            update_cell_selection_js_code, cell_index, cell_index_visual
        )

        if selection_updated:
            autoscroll_enable = nvim_info.nvim.vars.get(
                "jupynium_autoscroll_enable", True
            )
            if autoscroll_enable:
                autoscroll_mode = nvim_info.nvim.vars.get(
                    "jupynium_autoscroll_mode", "always"
                )

                if autoscroll_mode == "always":
                    do_scroll = True
                else:
                    do_scroll = not driver.execute_script(
                        "return Jupyter.notebook.scroll_manager.is_cell_visible(Jupyter.notebook.get_cell(arguments[0]));",
                        cell_index,
                    )

                if do_scroll:
                    # scroll to cell
                    top_margin_percent = nvim_info.nvim.vars.get(
                        "jupynium_autoscroll_cell_top_margin_percent", 0
                    )
                    driver.execute_script(
                        "Jupyter.notebook.scroll_cell_percent(arguments[0], arguments[1], 0);",
                        cell_index,
                        top_margin_percent,
                    )


def download_ipynb(driver, nvim_info, bufnr, output_ipynb_path):
    driver.switch_to.window(nvim_info.window_handles[bufnr])

    with open(output_ipynb_path, "w") as f:
        json.dump(
            driver.execute_script(
                "return Jupyter.notebook.toJSON();",
            ),
            f,
            indent=4,
        )
        nvim_info.nvim.lua.Jupynium_notify.info(
            ["Downloaded ipynb file to", output_ipynb_path],
            async_=True,
        )
        logger.info(f"Downloaded ipynb to {output_ipynb_path}")


def scroll_to_cell(driver, nvim_info, bufnr, cursor_pos_row):
    # Which cell?
    cell_index, _, _ = nvim_info.jupbufs[bufnr].get_cell_index_from_row(cursor_pos_row)

    cell_index = max(cell_index - 1, 0)

    driver.switch_to.window(nvim_info.window_handles[bufnr])

    top_margin_percent = nvim_info.nvim.vars.get(
        "jupynium_autoscroll_cell_top_margin_percent", 0
    )
    driver.execute_script(
        "Jupyter.notebook.scroll_cell_percent(arguments[0], arguments[1], 0);",
        cell_index,
        top_margin_percent,
    )
