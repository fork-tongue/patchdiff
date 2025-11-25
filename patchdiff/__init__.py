from importlib.metadata import version

__version__ = version("patchdiff")

from .apply import apply, iapply
from .diff import diff
from .serialize import to_json
