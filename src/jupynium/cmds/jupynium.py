#!/usr/bin/env python
# ruff: noqa: T201
from __future__ import annotations

import argparse
import configparser
import logging
import os
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import coloredlogs
import git
import persistqueue
import psutil
import verboselogs
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from persistqueue.exceptions import Empty
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from jupynium import __version__
from jupynium import selenium_helpers as sele
from jupynium.definitions import persist_queue_path
from jupynium.events_control import process_events
from jupynium.nvim import NvimInfo
from jupynium.process import already_running_pid
from jupynium.pynvim_helpers import attach_and_init

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pynvim import Nvim
    from selenium.webdriver.remote.webdriver import WebDriver

logger = verboselogs.VerboseLogger(__name__)


def webdriver_firefox(
    profiles_ini_path: str | PathLike | None = "~/.mozilla/firefox/profiles.ini",
    profile_name: str | None = None,
):
    """
    Get a Firefox webdriver with a specific profile.

    profiles.ini path is used to remember the last session (password, etc.)

    Args:
        profiles_ini_path: Path to profiles.ini
        profile_name: Profile name in profiles.ini. If None, use the default profile.
    """
    # Read firefox profile path from profiles.ini
    profile_path = None

    if profiles_ini_path is not None:
        profiles_ini_path = Path(profiles_ini_path).expanduser()
        if profiles_ini_path.exists():
            config = configparser.ConfigParser()
            config.read(profiles_ini_path)
            for section in config.sections():
                if section.startswith("Profile"):
                    try:
                        if profile_name is None or profile_name == "":
                            if config[section]["Default"] == "1":
                                section_ = section
                                break
                        elif config[section]["Name"] == profile_name:
                            section_ = section
                            break
                    except KeyError:
                        pass
            else:
                section_ = None
                profile_path = None

            if section_ is not None:
                try:
                    profile_path = config[section_]["Path"]
                    is_relative = config[section_]["IsRelative"]
                    if is_relative == "1":
                        profile_path = profiles_ini_path.parent / profile_path
                    else:
                        profile_path = Path(profile_path)
                    if not profile_path.exists():
                        profile_path = None
                except KeyError:
                    profile_path = None

    logger.info(f"Using firefox profile: {profile_path}")

    options = Options()
    options.profile = webdriver.FirefoxProfile(profile_path)
    options.set_preference("browser.link.open_newwindow", 3)
    options.set_preference("browser.link.open_newwindow.restriction", 0)
    # profile.setAlwaysLoadNoFocusLib(True);

    service = Service(log_path=os.path.devnull)
    return webdriver.Firefox(options=options, service=service)


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
        default="localhost:8888/nbclassic",
        help="Jupyter Notebook URL to open from the Selenium browser",
    )
    parser.add_argument(
        "--nvim_listen_addr",
        # default="localhost:18898",
        help="TCP or socket path (file path)",
    )
    parser.add_argument(
        "--attach_only",
        action="store_true",
        help="Attach to an existing Jupynium instance."
        "If False, start a new instance or attach to an existing one.\n"
        "If True, all arguments except nvim_listen_addr and notebook_URL are ignored.",
    )
    parser.add_argument(
        "--sleep_time_idle",
        type=float,
        default=0.05,
        help="Sleep time when there is no event to process.",
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
    parser.add_argument(
        "--firefox_profiles_ini_path",
        help="Path to firefox profiles.ini which will be used to remember the last session (password, etc.)\n"
        "Example path:\n"
        "~/.mozilla/firefox/profiles.ini\n"
        "~/snap/firefox/common/.mozilla/firefox/profiles.ini",
    )
    parser.add_argument(
        "--firefox_profile_name",
        help="Firefox profile name. If None, use the default profile.",
    )
    parser.add_argument(
        "--jupyter_command",
        type=str,
        nargs="+",
        default=["jupyter"],
        help="Command to start Jupyter Notebook (but without notebook).\n"
        "To use conda env, use `--jupyter_command conda run ' --no-capture-output' ' -n' base jupyter`. "
        "Notice the space before the dash.\n"
        "It is used only when the --notebook_URL is localhost, and is not running.",
    )
    parser.add_argument(
        "--notebook_dir",
        type=str,
        help="When jupyter notebook has started using --jupyter_command, the root dir will be this.\n"
        "If None, open at a git dir of nvim's buffer path and still navigate to the buffer dir.\n"
        "(e.g. localhost:8888/nbclassic/tree/path/to/buffer)",
    )
    parser.add_argument(
        "--no_auto_close_tab",
        action="store_true",
        help="Disable auto closing of tabs when closing vim buffer that is in sync.",
    )

    # parser.add_argument(
    #     "--browser",
    #     choices=["firefox", "safari", "chrome"],
    #     default="firefox",
    #     help="Browser to use. Best with firefox. Chrome may often steal the focus.",
    # )
    return parser


def start_if_running_else_clear(args, q: persistqueue.UniqueQ):
    # If Jupynium is already running, send args and quit.
    if already_running_pid():
        if args.nvim_listen_addr is not None:
            q.put(args)
            logger.info(
                "Jupynium is already running. Attaching to the running process."
            )
            return 0
        else:
            logger.info(
                "Jupynium is already running. Attach nvim using --nvim_listen_addr"
            )
            return 1
    elif args.attach_only:
        logger.error(
            "Jupynium is not running. "
            "Remove --attach_only option to start a new instance."
        )
        return 1

    # If Jupynium is not running, clear the message queue before starting.
    while True:
        try:
            _ = q.get(block=False)
        except Empty:
            break

    return None


def number_of_windows_be_list(num_windows: list[int]):
    """
    An expectation for the number of windows to be one of the listed values.

    Slightly modified from EC.number_of_windows_to_be(num_windows).
    """

    def _predicate(driver: webdriver.Firefox):
        return len(driver.window_handles) in num_windows

    return _predicate


def attach_new_neovim(
    driver: WebDriver,
    new_args: argparse.Namespace,
    nvims: dict[str, NvimInfo],
    url_to_home_windows: dict[str, str],
):
    logger.info(f"New nvim wants to attach: {new_args}")
    if new_args.nvim_listen_addr in nvims:
        logger.info("Already attached.")
    else:
        try:
            nvim = attach_and_init(new_args.nvim_listen_addr)
            if new_args.notebook_URL in url_to_home_windows:
                home_window = url_to_home_windows[new_args.notebook_URL]
            else:
                prev_num_windows = len(driver.window_handles)
                driver.switch_to.new_window("tab")
                driver.get(new_args.notebook_URL)

                # Wait for the notebook to load
                driver_wait = WebDriverWait(driver, 10)
                driver_wait.until(EC.number_of_windows_to_be(prev_num_windows + 1))
                sele.wait_until_loaded(driver)

                home_window = driver.current_window_handle
                url_to_home_windows[new_args.notebook_URL] = home_window

            nvim_info = NvimInfo(
                nvim, home_window, auto_close_tab=not new_args.no_auto_close_tab
            )
            nvims[new_args.nvim_listen_addr] = nvim_info
        except Exception:
            logger.exception("Exception occurred while attaching a new nvim. Ignoring.")


def nvims_teardown(nvims):
    # Before exiting, tell vim about it.
    # Otherwise vim will need to communicate once more to find out.
    try:
        for nvim in nvims.values():
            nvim.nvim.lua.Jupynium_reset_channel(async_=True)
    except Exception:  # noqa: BLE001
        # Even if you fail it's not a big problem
        pass


def generate_notebook_token():
    return secrets.token_urlsafe(16)


def exception_no_notebook(notebook_url: str, nvim: Nvim | None):
    logger.exception(
        "Exception occurred. "
        f"Are you sure you're running Jupyter Notebook at {notebook_url}? "
        "Use --jupyter_command to specify the command to start Jupyter Notebook."
    )
    if nvim is not None:
        nvim.lua.Jupynium_notify.error(
            [
                "Can't connect to Jupyter Notebook.",
                f"Are you sure you're running Jupyter Notebook at {notebook_url}?",
                "Use jupyter_command to specify the command to start Jupyter Notebook.",
            ],
        )
        nvim.lua.Jupynium_reset_channel()

    sys.exit(1)


def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for process in children:
        process.send_signal(sig)
    psutil.wait_procs(children, timeout=3)


def kill_notebook_proc(notebook_proc: subprocess.Popen | None):
    """
    Kill the notebook process.

    Used if we opened a Jupyter Notebook server using the --jupyter_command
    and when no server is running.
    """
    if notebook_proc is not None:
        if os.name == "nt":
            # Windows
            os.kill(notebook_proc.pid, signal.CTRL_C_EVENT)
        else:
            # Need to kill children if the notebook server is started using
            # `conda run` like
            # conda run --no-capture-output -n base jupyter notebook
            kill_child_processes(notebook_proc.pid, signal.SIGKILL)

            # notebook_proc.terminate()
            notebook_proc.kill()
            notebook_proc.wait()

        logger.info(
            f"Jupyter Notebook server (pid={notebook_proc.pid}) has been killed."
        )


def fallback_open_notebook_server(
    notebook_port: int,
    notebook_url_path: str,
    jupyter_command: Sequence[str],
    notebook_dir: str | PathLike | None,
    nvim: Nvim | None,
    driver: WebDriver,
):
    """
    After firefox failing to try to connect to Notebook, open the Notebook server and try again.

    Args:
        notebook_url_path: e.g. "/nbclassic"

    Returns:
        notebook_proc: subprocess.Popen object
    """
    # Fallback: if the URL is localhost and if selenium can't connect,
    # open the Jupyter Notebook server and even start syncing.
    rel_dir = ""

    if notebook_dir is None or notebook_dir == "":
        notebook_dir = None
        if nvim is not None:
            # Root dir of the notebook is either the buffer's dir or the git dir.
            buffer_path = str(nvim.eval("expand('%:p')"))
            buffer_dir = Path(buffer_path).parent
            try:
                repo = git.Repo(buffer_dir, search_parent_directories=True)
                notebook_dir = repo.working_tree_dir
                rel_dir = os.path.relpath(buffer_dir, notebook_dir)
            except InvalidGitRepositoryError:
                notebook_dir = buffer_dir
            except NoSuchPathError:
                notebook_dir = Path.cwd()

    notebook_token = generate_notebook_token()
    notebook_args = [
        "notebook",
        "--port",
        str(notebook_port),
        "--no-browser",
        "--NotebookApp.token",
        notebook_token,
        "--NotebookApp.show_banner=False",
    ]

    if notebook_dir is not None:
        # notebook_args += [f"--ServerApp.root_dir={root_dir}"]
        notebook_args += ["--NotebookApp.notebook_dir", notebook_dir]

    notebook_proc = None
    try:
        # strip commands because we need to escape args with dashes.
        # e.g. --jupyter_command conda run ' --no-capture-output' ' -n' env_name jupyter

        jupyter_command = [command.strip() for command in jupyter_command]
        jupyter_command[0] = str(Path(jupyter_command[0]).expanduser())

        jupyter_stdout = tempfile.NamedTemporaryFile()  # noqa: SIM115
        logger.info(f"Writing Jupyter Notebook server log to: {jupyter_stdout.name}")
        notebook_proc = subprocess.Popen(
            jupyter_command + notebook_args,
            stdout=jupyter_stdout,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        # Command doesn't exist
        exception_no_notebook(f"localhost:{notebook_port}{notebook_url_path}", nvim)

    assert notebook_proc is not None

    time.sleep(1)
    for _ in range(20):
        try:
            driver.get(
                f"localhost:{notebook_port}{notebook_url_path}/tree/{rel_dir}?token={notebook_token}"
            )
            break
        except WebDriverException:
            poll = notebook_proc.poll()
            if poll is not None:
                # Process finished
                exception_no_notebook(
                    f"localhost:{notebook_port}{notebook_url_path}", nvim
                )

        time.sleep(0.3)
    else:
        # Process still running but timeout for connecting to notebook.
        # Maybe wrong command?
        kill_notebook_proc(notebook_proc)
        exception_no_notebook(f"localhost:{notebook_port}{notebook_url_path}", nvim)
    return notebook_proc


def main():  # noqa: C901 PLR0912
    # Initialise with NOTSET level and null device, and add stream handler separately.
    # This way, the root logging level is NOTSET (log all),
    # and we can customise each handler's behaviour.
    # If we set the level during the initialisation, it will affect to ALL streams,
    # so the file stream cannot be more verbose (lower level) than the console stream.
    coloredlogs.install(fmt="", level=logging.NOTSET, stream=open(os.devnull, "w"))  # noqa: SIM115

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = coloredlogs.ColoredFormatter(
        "%(name)s: %(lineno)4d - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_format)

    tmp_log_dir = Path(tempfile.gettempdir()) / "jupynium" / "logs"
    tmp_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = tmp_log_dir / f"{datetime.now(tz=timezone.utc):%Y-%m-%d_%H-%M-%S}.log"

    f_handler = logging.FileHandler(log_path)
    f_handler.setLevel(logging.INFO)
    f_format = logging.Formatter(
        "%(asctime)s - %(name)s: %(lineno)4d - %(levelname)s - %(message)s"
    )
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(f_handler)

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

    q = persistqueue.UniqueQ(persist_queue_path)
    return_code = start_if_running_else_clear(args, q)
    if return_code is not None:
        sys.exit(return_code)

    nvim = None
    if args.nvim_listen_addr is not None:
        try:
            nvim = attach_and_init(args.nvim_listen_addr)
        except Exception:
            logger.exception("Exception occurred")
            sys.exit(1)

    nvims = {}
    notebook_proc = None
    try:
        # Open selenium
        # If you load with Chrome, it will annoyingly set focus to the browser
        # when you open or change tab (basically happens every time you type)

        # If you load with Safari, it won't let you interact with the browser.

        with webdriver_firefox(
            args.firefox_profiles_ini_path, args.firefox_profile_name
        ) as driver:
            # Initial number of windows when launching browser
            init_num_windows = len(driver.window_handles)
            try:
                driver.get(args.notebook_URL)
            except WebDriverException:
                notebook_url = args.notebook_URL
                if "://" not in args.notebook_URL:
                    notebook_url = "http://" + notebook_url
                url = urlparse(notebook_url)
                if url.port is not None and url.hostname in ["localhost", "127.0.0.1"]:
                    notebook_proc = fallback_open_notebook_server(
                        url.port,
                        url.path,
                        args.jupyter_command,
                        args.notebook_dir,
                        nvim,
                        driver,
                    )

                else:
                    # Not localhost, so not trying to start the notebook server.
                    exception_no_notebook(args.notebook_URL, nvim)

            # Wait for the notebook to load
            driver_wait = WebDriverWait(driver, 10)
            # Acceptable number of windows is either:
            # - Initial number of windows, for regular case where jupynium handles
            # initally focused tab
            # - Initial number of windows + 1, if an extension automatically opens
            # a new tab
            # Ref: https://github.com/kiyoon/jupynium.nvim/issues/59
            accept_num_windows = [init_num_windows, init_num_windows + 1]
            driver_wait.until(number_of_windows_be_list(accept_num_windows))
            sele.wait_until_loaded(driver)

            home_window = driver.current_window_handle

            url_to_home_windows = {args.notebook_URL: home_window}
            if args.nvim_listen_addr is not None and nvim is not None:
                nvims = {
                    args.nvim_listen_addr: NvimInfo(
                        nvim, home_window, auto_close_tab=not args.no_auto_close_tab
                    )
                }
            else:
                logger.info(
                    "No nvim attached. Waiting for nvim to attach. "
                    "Run jupynium --nvim_listen_addr /tmp/example "
                    "(use `:echo v:servername` of nvim)"
                )

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
                                "Uncaught exception occurred while processing events. "
                                "Detaching nvim."
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
                        new_args: argparse.Namespace = q.get(block=False)
                    except Empty:
                        pass
                    else:
                        attach_new_neovim(driver, new_args, nvims, url_to_home_windows)

                    time.sleep(args.sleep_time_idle)
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
    kill_notebook_proc(notebook_proc)


if __name__ == "__main__":
    main()
