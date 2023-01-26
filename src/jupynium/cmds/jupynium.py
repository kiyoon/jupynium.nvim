#!/use/bin/env python3
from __future__ import annotations

import argparse
import configparser
import logging
import os
import secrets
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

import coloredlogs
import git
import persistqueue
import verboselogs
from git.exc import InvalidGitRepositoryError
from persistqueue.exceptions import Empty
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from .. import __version__
from .. import selenium_helpers as sele
from ..definitions import persist_queue_path
from ..events_control import process_events
from ..nvim import NvimInfo
from ..process import already_running_pid
from ..pynvim_helpers import attach_and_init

logger = verboselogs.VerboseLogger(__name__)

SOURCE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


def webdriver_firefox(
    profiles_ini_path="~/.mozilla/firefox/profiles.ini", profile_name=None
):
    """
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
                        else:
                            if config[section]["Name"] == profile_name:
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

    profile = webdriver.FirefoxProfile(profile_path)
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
        # default="localhost:18898",
        help="TCP or socket path (file path)",
    )
    parser.add_argument(
        "--attach_only",
        action="store_true",
        help="Attach to an existing Jupynium instance."
        "If False, start a new instance or attach to an existing one."
        "If True, all arguments except nvim_listen_addr and notebook_URL are ignored.",
    )
    parser.add_argument(
        "--sleep_time_idle",
        type=float,
        default=0.1,
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
        default="~/.mozilla/firefox/profiles.ini",
        help="Path to firefox profiles.ini which will be used to remember the last session (password, etc.)",
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
        help="Command to start Jupyter Notebook (but without notebook)."
        "To use conda env, use `--jupyter_command ~/miniconda3/envs/env_name/bin/jupyter`."
        "Don't use `conda run ..` as it won't be killed afterwards (it opens another process with different pid so it's hard to keep track of it.)"
        "It is used only when the --notebook_URL is localhost, and is not running.",
    )
    parser.add_argument(
        "--notebook_dir",
        type=str,
        help="When jupyter notebook has started using --jupyter_command, the root dir will be this."
        "If None, open at a git dir of nvim's buffer path and still navigate to the buffer dir."
        "(e.g. localhost:8888/tree/path/to/buffer)",
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
    else:
        if args.attach_only:
            logger.error(
                "Jupynium is not running. Remove --attach_only option to start a new instance."
            )
            return 1

    # If Jupynium is not running, clear the message queue before starting.
    while True:
        try:
            _ = q.get(block=False)
        except Empty:
            break

    return None


def attach_new_neovim(
    driver,
    new_args,
    nvims: dict[str, NvimInfo],
    URL_to_home_windows: dict[str, str],
):
    logger.info(f"New nvim wants to attach: {new_args}")
    if new_args.nvim_listen_addr in nvims:
        logger.info("Already attached.")
    else:
        try:
            nvim = attach_and_init(new_args.nvim_listen_addr)
            if new_args.notebook_URL in URL_to_home_windows.keys():
                home_window = URL_to_home_windows[new_args.notebook_URL]
            else:
                prev_num_windows = len(driver.window_handles)
                driver.switch_to.new_window("tab")
                driver.get(new_args.notebook_URL)

                # Wait for the notebook to load
                driver_wait = WebDriverWait(driver, 10)
                driver_wait.until(EC.number_of_windows_to_be(prev_num_windows + 1))
                sele.wait_until_loaded(driver)

                home_window = driver.current_window_handle
                URL_to_home_windows[new_args.notebook_URL] = home_window

            nvim_info = NvimInfo(nvim, home_window)
            nvims[new_args.nvim_listen_addr] = nvim_info
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


def generate_notebook_token():
    return secrets.token_urlsafe(16)


def exception_no_notebook(notebook_URL, nvim):
    logger.exception(
        f"Exception occurred. Are you sure you're running Jupyter Notebook at {notebook_URL}? Use --jupyter_command to specify the command to start Jupyter Notebook."
    )
    if nvim is not None:
        nvim.lua.Jupynium_notify.error(
            [
                "Can't connect to Jupyter Notebook.",
                f"Are you sure you're running Jupyter Notebook at {notebook_URL}?",
                "Use jupyter_command to specify the command to start Jupyter Notebook.",
            ],
        )
        nvim.lua.Jupynium_reset_channel()

    sys.exit(1)


def kill_notebook_proc(notebook_proc):
    """
    Kill the notebook process.
    Used if we opened a Jupyter Notebook server using the --jupyter_command and when no server is running.
    """
    if notebook_proc is not None:
        notebook_proc.terminate()
        # notebook_proc.kill()
        notebook_proc.wait()
        logger.info("Jupyter Notebook server has been killed.")


def fallback_open_notebook_server(
    notebook_port, jupyter_command, notebook_dir, nvim, driver
):
    # Fallback: if the URL is localhost and if selenium can't connect,
    # open the Jupyter Notebook server and even start syncing.
    rel_dir = ""

    if notebook_dir is None or notebook_dir == "":
        notebook_dir = None
        if nvim is not None:
            # Root dir of the notebook is either the buffer's dir or the git dir.
            buffer_path = str(nvim.eval("expand('%:p')"))
            buffer_dir = os.path.dirname(buffer_path)
            try:
                repo = git.Repo(buffer_dir, search_parent_directories=True)
                notebook_dir = repo.working_tree_dir
                rel_dir = os.path.relpath(buffer_dir, notebook_dir)
            except InvalidGitRepositoryError:
                notebook_dir = buffer_dir

    notebook_token = generate_notebook_token()
    notebook_args = [
        "notebook",
        "--port",
        str(notebook_port),
        "--no-browser",
        f"--NotebookApp.token",
        notebook_token,
    ]

    if notebook_dir is not None:
        # notebook_args += [f"--ServerApp.root_dir={root_dir}"]
        notebook_args += ["--NotebookApp.notebook_dir", notebook_dir]

    try:
        # strip commands because we need to escape args with dashes.
        # e.g. --jupyter_command conda run ' --no-capture-output' ' -n' env_name jupyter
        # However, conda run will run process with another pid so it won't work well here. Don't use it.

        jupyter_command = [command.strip() for command in jupyter_command]
        jupyter_command[0] = os.path.expanduser(jupyter_command[0])

        jupyter_stdout = tempfile.NamedTemporaryFile()
        logger.info(f"Writing Jupyter Notebook server log to: {jupyter_stdout.name}")
        notebook_proc = subprocess.Popen(
            jupyter_command + notebook_args, stdout=jupyter_stdout
        )
    except FileNotFoundError:
        # Command doesn't exist
        exception_no_notebook(f"localhost:{notebook_port}", nvim)

    time.sleep(1)
    for _ in range(20):
        try:
            driver.get(
                f"localhost:{notebook_port}/tree/{rel_dir}?token={notebook_token}"
            )
            break
        except WebDriverException:
            poll = notebook_proc.poll()
            if poll is not None:
                # Process finished
                exception_no_notebook(f"localhost:{notebook_port}", nvim)

        time.sleep(0.3)
    else:
        # Process still running but timeout for connecting to notebook. Maybe wrong command?
        kill_notebook_proc(notebook_proc)
        exception_no_notebook(f"localhost:{notebook_port}", nvim)
    return notebook_proc


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
            try:
                driver.get(args.notebook_URL)
            except WebDriverException:
                notebook_URL = args.notebook_URL
                if "://" not in args.notebook_URL:
                    notebook_URL = "http://" + notebook_URL
                url = urlparse(notebook_URL)
                if url.port is not None and url.hostname in ["localhost", "127.0.0.1"]:
                    notebook_proc = fallback_open_notebook_server(
                        url.port, args.jupyter_command, args.notebook_dir, nvim, driver
                    )

                else:
                    # Not localhost, so not trying to start the notebook server.
                    exception_no_notebook(args.notebook_URL, nvim)

            # Wait for the notebook to load
            driver_wait = WebDriverWait(driver, 10)
            driver_wait.until(EC.number_of_windows_to_be(1))
            sele.wait_until_loaded(driver)

            home_window = driver.current_window_handle

            URL_to_home_windows = {args.notebook_URL: home_window}
            if args.nvim_listen_addr is not None and nvim is not None:
                nvims = {args.nvim_listen_addr: NvimInfo(nvim, home_window)}
            else:
                logger.info(
                    "No nvim attached. Waiting for nvim to attach. Run jupynium --nvim_listen_addr /tmp/example (use `:echo v:servername` of nvim)"
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
                        new_args = q.get(block=False)
                    except Empty:
                        pass
                    else:
                        attach_new_neovim(driver, new_args, nvims, URL_to_home_windows)

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
