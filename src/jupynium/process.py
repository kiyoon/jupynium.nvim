# https://stackoverflow.com/questions/36799192/check-if-python-script-is-already-running
from __future__ import annotations

from os import PathLike, getpid
from pathlib import Path

from psutil import Process, pid_exists

from .definitions import jupynium_pid_path


def already_running_pid(
    name: str = "jupynium", pid_path: str | PathLike = jupynium_pid_path
):
    pid_path = Path(pid_path)
    my_pid = getpid()
    if pid_path.exists():
        with open(pid_path) as f:
            pid = f.read()
            pid = int(pid) if pid.isnumeric() else None
        if pid is not None and pid_exists(pid):
            if name in "".join(Process(my_pid).cmdline()) and name in "".join(  # noqa: SIM114
                Process(pid).cmdline()
            ):
                return pid
            elif Process(pid).cmdline() == Process(my_pid).cmdline():
                return pid
    with open(pid_path, "w") as f:
        f.write(str(my_pid))
    return 0
