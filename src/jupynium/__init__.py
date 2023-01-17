try:
    from ._version import __version__, __version_tuple__
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)

all = ["__version__", "__version_tuple__"]
