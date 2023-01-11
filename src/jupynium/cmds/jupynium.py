#!/use/bin/env python3

import argparse
import json
import logging
import os
from pathlib import Path
import sys
import traceback

import coloredlogs
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import WebDriverException
import sysv_ipc
import verboselogs

from .. import selenium_helpers as sele
from ..definitions import IPC_KEY, IPC_TYPE_ATTACH_NEOVIM
from ..events_control import process_events
from ..process import already_running_pid
from ..pynvim_helpers import attach_and_init
from ..nvim import NvimInfo
from .. import __version__

logger = verboselogs.VerboseLogger(__name__)

SOURCE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


def webdriver_firefox():
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.link.open_newwindow", 3)
    profile.set_preference("browser.link.open_newwindow.restriction", 0)
    # profile.setAlwaysLoadNoFocusLib(True);
    return webdriver.Firefox(profile, service_log_path=os.path.devnull)


# def webdriver_safari():
#     return webdriver.Safari()
#
#
# def webdriver_chrome():
#     from selenium.webdriver.chrome.service import Service
#     from webdriver_manager.chrome import ChromeDriverManager
#
#     options = webdriver.ChromeOptions()
#     return webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()), options=options
#     )


def get_parser():
    parser = argparse.ArgumentParser(
        description="Control Jupyter Notebook with Neovim",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--notebook_URL",
        default="localhost:8888",
        help="Jupyter Notebook URL to open from the Selenium browser",
    )
    parser.add_argument(
        "--nvim_listen_addr",
        default="localhost:18898",
        help="TCP or socket path (file path)",
    )
    parser.add_argument(
        "--attach_only",
        action="store_true",
        help="Attach to an existing Jupynium instance. If False, start a new instance or attach to an existing one.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    parser.add_argument(
        "--check_running",
        action="store_true",
        help="Print pid if Jupynium is running. Otherwise, print nothing.",
    )

    # parser.add_argument(
    #     "--browser",
    #     choices=["firefox", "safari", "chrome"],
    #     default="firefox",
    #     help="Browser to use. Best with firefox. Chrome may often steal the focus.",
    # )
    return parser


def start_if_running_else_clear(args, ipc_queue):
    # If Jupynium is already running, send args and quit.
    if already_running_pid():
        ipc_queue.send(json.dumps(args.__dict__), True, type=IPC_TYPE_ATTACH_NEOVIM)
        logger.info("Jupynium is already running. Attaching to the running process.")
        return 0
    else:
        if args.attach_only:
            logger.error(
                "Jupynium is not running. Remove --attach_only option to start a new instance."
            )
            return 1

    # If Jupynium is not running, clear the message queue before starting.
    while True:
        try:
            _, _ = ipc_queue.receive(block=False, type=IPC_TYPE_ATTACH_NEOVIM)
        except sysv_ipc.BusyError:
            break

    return None


def attach_new_neovim(
    driver,
    new_args,
    nvims: dict[str, NvimInfo],
    URL_to_home_windows: dict[str, str],
):
    logger.info(f"New nvim wants to attach: {new_args}")
    if new_args["nvim_listen_addr"] in nvims:
        logger.info("Already attached.")
    else:
        try:
            nvim = attach_and_init(new_args["nvim_listen_addr"])
            if new_args["notebook_URL"] in URL_to_home_windows.keys():
                home_window = URL_to_home_windows[new_args["notebook_URL"]]
            else:
                prev_num_windows = len(driver.window_handles)
                driver.switch_to.new_window("tab")
                driver.get(new_args["notebook_URL"])

                # Wait for the notebook to load
                driver_wait = WebDriverWait(driver, 10)
                driver_wait.until(EC.number_of_windows_to_be(prev_num_windows + 1))
                sele.wait_until_loaded(driver)

                home_window = driver.current_window_handle
                URL_to_home_windows[new_args["notebook_URL"]] = home_window

            nvim_info = NvimInfo(nvim, home_window)
            nvims[new_args["nvim_listen_addr"]] = nvim_info
        except Exception:
            logger.exception("Exception occurred while attaching a new nvim. Ignoring.")


def nvims_teardown(nvims):
    # Before exiting, tell vim about it.
    # Otherwise vim will need to communicate once more to find out.
    try:
        for nvim in nvims.values():
            nvim.nvim.lua.Jupynium_reset_channel(async_=True)
    except Exception:
        # Even if you fail it's not a big problem
        pass


# flake8: noqa: C901
def main():
    coloredlogs.install(
        fmt="%(name)s: %(lineno)4d - %(levelname)s - %(message)s", level=logging.INFO
    )

    parser = get_parser()
    args = parser.parse_args()

    if args.version:
        print(f"Jupynium v{__version__}")
        sys.exit(0)

    if args.check_running:
        pid = already_running_pid()
        if pid > 0:
            print(pid)
        sys.exit(0)

    ipc_queue = sysv_ipc.MessageQueue(IPC_KEY, sysv_ipc.IPC_CREAT)
    return_code = start_if_running_else_clear(args, ipc_queue)
    if return_code is not None:
        sys.exit(return_code)

    try:
        nvim = attach_and_init(args.nvim_listen_addr)
    except Exception:
        logger.exception("Exception occurred")
        sys.exit(1)

    nvims = {}
    try:
        # Open selenium
        # If you load with Chrome, it will annoyingly set focus to the browser
        # when you open or change tab (basically happens every time you type)

        # If you load with Safari, it won't let you interact with the browser.

        with webdriver_firefox() as driver:
            driver.get(args.notebook_URL)

            # Wait for the notebook to load
            driver_wait = WebDriverWait(driver, 10)
            driver_wait.until(EC.number_of_windows_to_be(1))
            sele.wait_until_loaded(driver)

            home_window = driver.current_window_handle

            URL_to_home_windows = {args.notebook_URL: home_window}
            nvims = {args.nvim_listen_addr: NvimInfo(nvim, home_window)}

            while not sele.is_browser_disconnected(driver):
                try:
                    del_list = []
                    for nvim_listen_addr, nvim_info in nvims.items():
                        try:
                            status, rpcrequest_event = process_events(nvim_info, driver)
                        except OSError:
                            logger.info("Nvim has been closed. Detaching nvim.")
                            del_list.append((nvim_listen_addr, None))
                        except Exception:
                            logger.exception(
                                "Uncaught exception occurred while processing events. Detaching nvim."
                            )
                            del_list.append((nvim_listen_addr, None))

                        else:
                            if not status:
                                del_list.append((nvim_listen_addr, rpcrequest_event))

                    # Remove nvim if browser is closed
                    # Must do it outside the loop
                    for listen_addr, rpcrequest_event in del_list:
                        nvims[listen_addr].close(driver)
                        if rpcrequest_event is not None:
                            rpcrequest_event.send("OK")
                        del nvims[listen_addr]

                    # Check if a new newvim instance wants to attach to this server.
                    try:
                        message, _ = ipc_queue.receive(
                            block=False, type=IPC_TYPE_ATTACH_NEOVIM
                        )
                    except sysv_ipc.BusyError:
                        pass
                    else:
                        new_args = json.loads(message.decode())
                        attach_new_neovim(driver, new_args, nvims, URL_to_home_windows)
                except WebDriverException:
                    break

            logger.info("Browser disconnected. Quitting Jupynium.")

    except Exception:
        logger.exception("Exception occurred")
        for nvim in nvims.values():
            nvim.nvim.lua.Jupynium_notify.error(
                [
                    "Closed due to exception:",
                    None,
                    "```",
                    traceback.format_exc(),
                    "```",
                ],
                async_=True,
            )
    else:
        logger.success("Piecefully closed as the browser is closed.")

    nvims_teardown(nvims)


if __name__ == "__main__":
    main()
