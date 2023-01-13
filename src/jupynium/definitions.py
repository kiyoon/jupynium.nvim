import os
from pathlib import Path

PACKAGE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

persist_queue_path = PACKAGE_DIR / "jupynium_persist_queue"
