from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tutor-custom-emailtpl")
except PackageNotFoundError:
    # Not installed as a package yet (e.g. running tests from a checkout).
    __version__ = "0.0.0+dev"

try:
    from . import plugin  # noqa: F401  (registers Tutor hooks on import)
except ImportError:
    # `tutor` is not installed in this environment (e.g. the Django-app-only
    # test suite doesn't need the Tutor SDK). Safe to skip.
    pass
