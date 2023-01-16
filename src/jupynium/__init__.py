try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("jupynium")
    except PackageNotFoundError:
        # package is not installed
        __version__ = "unknown"
except ImportError:
    # For versions of python before 3.8
    from pkg_resources import DistributionNotFound, get_distribution

    try:
        __version__ = get_distribution("jupynium").version
    except DistributionNotFound:
        # package is not installed
        __version__ = "unknown"
