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
from .ipynb import cells_to_jupytext
from .nvim import NvimInfo
from .rpc_messages import len_pending_messages, receive_message

logger = logging.getLogger(__name__)


update_cell_selection_js_code = (
    resource_stream("jupynium", "js/update_cell_selection.js").read().decode("utf-8")
)

get_cell_inputs_js_code = (
    resource_stream("jupynium", "js/get_cell_inputs.js").read().decode("utf-8")
)

kernel_inspect_js_code = (
    resource_stream("jupynium", "js/kernel_inspect.js").read().decode("utf-8")
)

kernel_complete_js_code = (
    resource_stream("jupynium", "js/kernel_complete.js").read().decode("utf-8")
)

CompletionItemKind = {
    "text": 1,
    "method": 2,
    "function": 3,
    "constructor": 4,
    "field": 5,
    "variable": 6,
    "class": 7,
    "interface": 8,
    "module": 9,
    "property": 10,
    "unit": 11,
    "value": 12,
    "enum": 13,
    "keyword": 14,
    "snippet": 15,
    "color": 16,
    "file": 17,
    "reference": 18,
    "folder": 19,
    "enumMember": 20,
    "constant": 21,
    "struct": 22,
    "event": 23,
    "operator": 24,
    "typeParameter": 25,
    # Jupyter specific
    "dict key": 14,
    "instance": 6,
    "magic": 23,
    "path": 19,
    "statement": 13,
}


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
        rpcrequest event: Notify nvim after cleared up. None if status==True or
                          no need to notify
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
    # but so far it seems to be always smaller than
    # the actual number of pending messages

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
            status = process_notification_event(
                nvim_info, driver, event, prev_lazy_args_per_buf
            )
            if not status:
                return False, None

    # After the loop (here) you need to process the last on_lines event.
    prev_lazy_args_per_buf.process_all(nvim_info, driver)

    return True, None


def start_sync_with_filename(
    bufnr: int,
    ipynb_filename: str,
    ask: bool,
    content: list[str],
    buf_filetype: str,
    conda_or_venv_path: str | None,
    nvim_info: NvimInfo,
    driver,
):
    """
    Start sync using a filename (not tab index)
    filename has to end with .ipynb
    """
    driver.switch_to.window(nvim_info.home_window)
    sele.wait_until_notebook_list_loaded(driver)

    if ipynb_filename == "":
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
            if notebook_name == ipynb_filename:
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
                """input("Press 'v' to sync from n[v]im, 'i' to load from [i]pynb and sync. (v/i/[c]ancel): ")"""  # noqa: E501
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
            jupy = cells_to_jupytext(cell_types, texts)
            nvim_info.nvim.buffers[bufnr][:] = jupy

            nvim_info.attach_buffer(bufnr, jupy, new_window)
    else:
        new_btn = driver.find_element(By.ID, "new-buttons")
        driver.execute_script("arguments[0].scrollIntoView(true);", new_btn)
        kernel_name = choose_default_kernel(
            driver, "main", buf_filetype, conda_or_venv_path
        )
        if kernel_name is None:
            kernel_name = "python3"
        kernel_btn = driver.find_element(By.ID, f"kernel-{kernel_name}")
        driver.execute_script("arguments[0].scrollIntoView(true);", kernel_btn)
        prev_windows = set(driver.window_handles)
        try:
            kernel_btn.click()
        except ElementNotInteractableException:
            new_btn.click()
            kernel_btn.click()

        sele.wait_until_new_window(driver, prev_windows)
        new_window = set(driver.window_handles) - prev_windows
        assert len(new_window) == 1
        new_window = new_window.pop()

        driver.switch_to.window(new_window)
        sele.wait_until_notebook_loaded(driver)
        if ipynb_filename != "":
            driver.execute_script(
                "Jupyter.notebook.rename(arguments[0]);",
                ipynb_filename,
            )
        # start sync
        nvim_info.attach_buffer(bufnr, content, driver.current_window_handle)
        nvim_info.jupbufs[bufnr].full_sync_to_notebook(driver)


def choose_default_kernel(driver, page_type: str, buf_filetype, conda_or_venv_path):
    """
    Choose kernel based on buffer's filetype and conda env
    """
    if page_type == "notebook":
        kernel_specs = driver.execute_script(
            "return Jupyter.kernelselector.kernelspecs;"
        )
    elif page_type == "main":
        kernel_specs = driver.execute_script("return Jupyter.kernel_list.kernelspecs;")
    else:
        raise ValueError(f"Invalid page_type: {page_type}")

    valid_kernel_names = []
    for kernel_name, kern in kernel_specs.items():
        # Filter by language
        if kern["spec"]["language"].lower() == buf_filetype.lower():
            valid_kernel_names.append(kernel_name)

    def match_with_path(env_path: str) -> str | None:
        """Match kernel executable path with conda/virtual environment bin directory

        Args:
            env_path (str): Path of the conda/virtual environment directory

        Returns:
            str: Name of the kernel matching the environment, returns None if no match
        """
        for kernel_name in valid_kernel_names:
            try:
                kernel_exec_path = kernel_specs[kernel_name]["spec"]["argv"][0]
                exec_name = os.path.basename(kernel_exec_path)
                env_exec_path = os.path.join(env_path, "bin", exec_name)
                if kernel_exec_path == env_exec_path:
                    return kernel_name
            except (KeyError, IndexError):
                pass
        return

    if len(valid_kernel_names) == 0:
        return
    elif len(valid_kernel_names) == 1:
        return valid_kernel_names[0]
    elif conda_or_venv_path is not None and conda_or_venv_path != "":
        # Search for kernel register with current conda environment's name
        for valid_kernel_name in valid_kernel_names:
            try:
                if (
                    kernel_specs[valid_kernel_name]["spec"]["metadata"][
                        "conda_env_path"
                    ]
                    == conda_or_venv_path
                ):
                    return valid_kernel_name
            except KeyError:
                pass
        # If no match based on conda_env_path metadata,
        # try matching with executable path
        path_match = match_with_path(conda_or_venv_path)
        if path_match is not None:
            return path_match
    else:
        # Conda env path was not defined, so remove conda kernels
        valid_kernel_names_old = valid_kernel_names
        valid_kernel_names = []
        for valid_kernel_name in valid_kernel_names_old:
            if (
                "conda_env_path"
                not in kernel_specs[valid_kernel_name]["spec"]["metadata"].keys()
            ):
                valid_kernel_names.append(valid_kernel_name)

        if len(valid_kernel_names) == 0:
            return
        else:
            return valid_kernel_names[0]

    return


def process_request_event(nvim_info: NvimInfo, driver, event):
    """
    Returns:
        status (bool)
        request_event (rpcrequest event): to notify nvim after cleared up.
                                          None if no need to notify
    """
    assert event[0] == "request"
    # Request from nvim
    # send back response

    bufnr = event[2][0]
    event_args = event[2][1:]

    if event[1] == "start_sync":
        ipynb_filename, ask, content, buf_filetype, conda_or_venv_path = event_args
        ipynb_filename: str
        ipynb_filename = ipynb_filename.strip()

        if not ipynb_filename.isnumeric():
            if ipynb_filename != "" and not ipynb_filename.lower().endswith(".ipynb"):
                ipynb_filename += ".ipynb"

            start_sync_with_filename(
                bufnr,
                ipynb_filename,
                ask,
                content,
                buf_filetype,
                conda_or_venv_path,
                nvim_info,
                driver,
            )
        else:
            # start sync with tab index
            tab_idx = int(ipynb_filename)
            driver.switch_to.window(driver.window_handles[tab_idx - 1])

            continue_input = "y"
            if ask:
                continue_input = nvim_info.nvim.eval(
                    "input('This will remove all content from the Notebook. "
                    "Continue? (y/n): ')"
                )
            if continue_input in ["y", "Y"]:
                nvim_info.attach_buffer(bufnr, content, driver.current_window_handle)
                nvim_info.jupbufs[bufnr].full_sync_to_notebook(driver)
                ## Automatically setting kernel not activated when sync with tab index
                ## In the future we could activate by doing the following
                #
                # kernel_name = choose_default_kernel(
                #     driver, "notebook", buf_filetype, conda_or_venv_path
                # )
                # if kernel_name is not None:
                #     driver.execute_script(
                #         "Jupyter.kernelselector.set_kernel(arguments[0])", kernel_name
                #     )
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

        kernel_name_and_specs = driver.execute_script(
            "return [Jupyter.notebook.kernel.name, Jupyter.kernelselector.kernelspecs];"
        )
        kernel_name = kernel_name_and_specs[0]
        kernel_specs = kernel_name_and_specs[1]
        kernel_language = kernel_specs[kernel_name]["spec"]["language"].lower()

        logger.info(f"Current kernel name: {kernel_name}")
        logger.info(f"Kernel language: {kernel_language}")

        cell_types, texts = driver.execute_script(get_cell_inputs_js_code)
        jupy = cells_to_jupytext(cell_types, texts, python=kernel_language == "python")
        nvim_info.nvim.buffers[bufnr][:] = jupy
        logger.info("Loaded ipynb to the nvim buffer.")

    elif event[1] == "VimLeavePre":
        # For non-Windows, use rpcrequest
        logger.info("Nvim closed. Clearing nvim")
        return False, event[3]

    elif event[1] == "kernel_get_spec":
        driver.switch_to.window(nvim_info.window_handles[bufnr])
        kernel_specs = driver.execute_script(
            "return [Jupyter.notebook.kernel.name, Jupyter.kernelselector.kernelspecs];"
        )
        logger.info(f"Current kernel name: {kernel_specs[0]}")
        logger.info(f"Kernel specs: {kernel_specs[1]}")
        event[3].send(kernel_specs)
        return True, None

    elif event[1] == "kernel_inspect":
        (line, col) = event_args
        driver.switch_to.window(nvim_info.window_handles[bufnr])
        inspect_result = driver.execute_async_script(kernel_inspect_js_code, line, col)
        logger.info(f"Kernel inspect: {inspect_result}")
        event[3].send(inspect_result)
        return True, None

    elif event[1] == "execute_javascript":
        (code,) = event_args
        if bufnr is not None:
            driver.switch_to.window(nvim_info.window_handles[bufnr])
            logger.info(f"Executing javascript code in bufnr {bufnr}, code {code}")

        logger.info(f"Executing javascript code in bufnr {bufnr}, code {code}")
        ret_obj = driver.execute_script(code)
        event[3].send(ret_obj)
        return True, None

    elif event[1] == "kernel_connect_info":
        driver.switch_to.window(nvim_info.window_handles[bufnr])
        kernel_id = driver.execute_script("return Jupyter.notebook.kernel.id")
        event[3].send(kernel_id)
        return True, None

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
    In order to do that, process the previous on_lines only if current on_lines is
    not chainable.
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
        return True

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
            # Lazy. Process at the end of event loop cycle or if needed for
            # the next event.
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
                "Jupyter.notebook.scroll_manager.animation_speed = 0; Jupyter.notebook.scroll_manager.scroll_some(arguments[0]);",  # noqa: E501
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
        elif event[1] == "kernel_restart":
            driver.switch_to.window(nvim_info.window_handles[bufnr])
            driver.execute_script("Jupyter.notebook.kernel.restart()")
        elif event[1] == "kernel_interrupt":
            driver.switch_to.window(nvim_info.window_handles[bufnr])
            driver.execute_script("Jupyter.notebook.kernel.interrupt()")
        elif event[1] == "kernel_change":
            (kernel_name,) = event_args
            driver.switch_to.window(nvim_info.window_handles[bufnr])
            driver.execute_script(
                "Jupyter.kernelselector.set_kernel(arguments[0])", kernel_name
            )
        elif event[1] == "kernel_complete_async":
            (line, col, callback_id) = event_args
            if (
                nvim_info.nvim.vars["jupynium_kernel_complete_async_callback_id"]
                != callback_id
            ):
                logger.info("Ignoring outdated kernel_complete_async request")
                return True
            driver.switch_to.window(nvim_info.window_handles[bufnr])
            reply = driver.execute_async_script(kernel_complete_js_code, line, col)
            logger.info(f"Kernel complete: {reply}")

            if reply is None:
                logger.info("Getting kernel completion timed out")
                return True

            # Code from jupyter-kernel.nvim
            has_experimental_types = (
                "metadata" in reply.keys()
                and "_jupyter_types_experimental" in reply["metadata"].keys()
            )
            if has_experimental_types:
                replies = reply["metadata"]["_jupyter_types_experimental"]
                matches = []
                for match in replies:
                    if "signature" in match.keys():
                        matches.append(
                            {
                                "label": match.get("text", ""),
                                "documentation": {
                                    "kind": "markdown",
                                    "value": f"```python\n{match['signature']}\n```",
                                },
                                # default kind: text = 1
                                # sometimes match['type'] is '<unknown>'
                                "kind": CompletionItemKind.get(
                                    match.get("type", "text"), 1
                                ),
                            }
                        )
                    else:
                        matches.append(
                            {
                                "label": match.get("text", ""),
                                # default kind: text = 1
                                # sometimes match['type'] is '<unknown>'
                                "kind": CompletionItemKind.get(
                                    match.get("type", "text"), 1
                                ),
                            }
                        )
            else:
                matches = [{"label": m} for m in reply["matches"]]

            if (
                nvim_info.nvim.vars["jupynium_kernel_complete_async_callback_id"]
                != callback_id
            ):
                logger.info("Ignoring outdated kernel_complete_async request")
                return True

            nvim_info.nvim.lua.Jupynium_kernel_complete_async_callback(matches)

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

        elif event[1] == "BufUnload":
            logger.info("Buffer unloaded on nvim. Closing on Jupyter Notebook")
            nvim_info.detach_buffer(bufnr, driver)

        elif event[1] == "stop_sync":
            logger.info(f"Received stop_sync request: bufnr = {bufnr}")
            nvim_info.detach_buffer(bufnr, driver)

        elif event[1] == "VimLeavePre":
            # Only for Windows, use rpcnotify
            logger.info("Nvim closed. Clearing nvim")
            return False

    return True


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
        # 0-th cell is not a cell, but it's the header.
        # You can put anything above and it won't be synced to Jupyter Notebook.
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
                        "return Jupyter.notebook.scroll_manager.is_cell_visible(Jupyter.notebook.get_cell(arguments[0]));",  # noqa: E501
                        cell_index,
                    )

                if do_scroll:
                    # scroll to cell
                    top_margin_percent = nvim_info.nvim.vars.get(
                        "jupynium_autoscroll_cell_top_margin_percent", 0
                    )
                    driver.execute_script(
                        "Jupyter.notebook.scroll_cell_percent(arguments[0], arguments[1], 0);",  # noqa: E501
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
