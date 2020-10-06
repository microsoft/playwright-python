import inspect
import stat
from pathlib import Path


def get_file_dirname() -> Path:
    """Returns the callee (`__file__`) directory name"""
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    assert module
    return Path(module.__file__).parent.absolute()


def make_file_executable(file_path: Path) -> Path:
    """Makes a file executable."""
    file_path.chmod(file_path.stat().st_mode | stat.S_IEXEC)
    return file_path
