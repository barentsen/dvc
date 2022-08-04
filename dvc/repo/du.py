"""
TODO
----
- Add dvc_only option?
- Deal with size=None?
- Think about reporting block sizes
"""
from os.path import join
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from dvc.fs.dvc import DvcFileSystem

    from . import Repo


def du(
    url: str,
    path: Optional[str] = None,
    rev: str = None,
    maxdepth: int = None,
    include_files: bool = False,
):
    from . import Repo

    with Repo.open(url, rev=rev, subrepos=True, uninitialized=True) as repo:
        path = path or "."
        usage = _du(repo, path, maxdepth=maxdepth, include_files=include_files)
        usage = dict(sorted(usage.items(), key=lambda x: x[0]))
        return usage


def _du(
    repo: "Repo", path: str, maxdepth: int = None, include_files: bool = False
):
    """
    Note: we assume that maxdepth only influences
    the output of the command, not the scanning.
    """
    fs: "DvcFileSystem" = repo.dvcfs
    fs_path = fs.from_os_path(path)

    usage: Dict[str, int] = {}  # path => usage

    # We walk through the directories in a bottom-up fashion, so we can
    # use dynamic programming to compute the directory sizes efficiently.
    walk = list(fs.walk(fs_path))[::-1]
    for root, dirs, files in walk:
        # Find sizes of all non-directory files
        file_paths = [join(root, name) for name in files]
        file_usage = {path: fs.size(path) for path in file_paths}

        # Sum the size of all files to get the current directory size
        total_file_usage = sum(file_usage.values())

        # Sum up the sizes of all sub-directories
        total_subdir_usage = sum(usage.get(join(root, d), 0) for d in dirs)

        usage[root] = total_file_usage + total_subdir_usage
        if include_files:
            usage |= file_usage

    if maxdepth is not None:
        usage = {
            path: size
            for path, size in usage.items()
            if len(Path(path).parents) <= maxdepth
        }

    return usage
