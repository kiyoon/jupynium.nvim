from pathlib import Path

import platformdirs

CACHE_DIR = Path(platformdirs.user_cache_dir("jupynium"))
persist_queue_path = CACHE_DIR / "jupynium_persist_queue"
jupynium_pid_path = CACHE_DIR / "jupynium_pid.txt"
