# https://stackoverflow.com/questions/36799192/check-if-python-script-is-already-running
from os import getpid
from os.path import exists
from psutil import pid_exists, Process

from .definitions import PACKAGE_DIR


def already_running_pid(name="jupynium"):
    pidpath = PACKAGE_DIR / f"{name}_pid.txt"
    my_pid = getpid()
    if exists(pidpath):
        with open(pidpath) as f:
            pid = f.read()
            pid = int(pid) if pid.isnumeric() else None
        if pid is not None and pid_exists(pid):
            if name in "".join(Process(my_pid).cmdline()) and name in "".join(
                Process(pid).cmdline()
            ):
                return pid
            elif Process(pid).cmdline() == Process(my_pid).cmdline():
                return pid
    with open(pidpath, "w") as f:
        f.write(str(my_pid))
    return 0
