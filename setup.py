import sys

from setuptools import setup

import versioneer

sys.path.insert(0, ".")

if __name__ == "__main__":
    setup(
        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),
    )
