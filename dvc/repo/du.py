"""
Implements the `Repo.du()` method.
"""
import math
from os.path import join
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from dvc.fs.dvc import DvcFileSystem

    from . import Repo


def du(
    url: str,
    path: Optional[str] = None,
    rev: Optional[str] = None,
    max_depth: Optional[int] = None,
    include_files: bool = False,
    dvc_only: bool = False,
    block_size: int = 1024,
) -> List[Tuple[str, int]]:
    """
    Returns the disk usage.

    Args:
        TBC

    Returns:
        usage: list of dict
    """
    from . import Repo

    with Repo.open(url, rev=rev, subrepos=True, uninitialized=True) as repo:
        path = path or "."
        block_size = block_size or 1024
        usage = _du(
            repo,
            path,
            max_depth=max_depth,
            include_files=include_files,
            dvc_only=dvc_only,
            block_size=block_size,
        )
        usage_list = sorted(usage.items(), key=lambda x: x[0])
        # Put "." at the end (TODO: define a smarter sorting function)
        usage_list = usage_list[1:] + [usage_list[0]]
        return usage_list


def _du(
    repo: "Repo",
    path: str,
    max_depth: Optional[int] = None,
    include_files: bool = False,
    dvc_only: bool = False,
    block_size: int = 1024,
) -> Dict[str, int]:
    fs: "DvcFileSystem" = repo.dvcfs
    fs_path: str = fs.from_os_path(path)
    usage: Dict[str, int] = {}  # path => disk usage (bytes)

    # Walk through the directories in a bottom-up fashion, so we can
    # use dynamic programming to compute the directory sizes efficiently
    walk = list(fs.walk(fs_path, dvcfiles=True, dvc_only=dvc_only))[::-1]
    for root, dirs, files in walk:
        # 1. Sum the sizes of all *files* in the current `root` dir
        file_paths = [join(root, name) for name in files]
        file_usage = {
            path: _disk_usage(fs, path, block_size=block_size)
            for path in file_paths
        }
        total_file_usage = sum(file_usage.values())
        if include_files:
            usage |= file_usage

        # 2. Sum the sizes of all *subdirs* in the current `root`
        total_subdir_usage = sum(usage.get(join(root, d), 0) for d in dirs)

        # 3. Determine total size of `root` by summing 1+2
        usage[root] = total_file_usage + total_subdir_usage

    # Note: the max_depth parameter only affects the output,
    # not the depth of the scanning.
    if max_depth is not None:
        usage = {
            path: size
            for path, size in usage.items()
            if len(Path(path).parents) <= max_depth
        }

    return usage


def _disk_usage(fs: "DvcFileSystem", path: str, block_size: int = 1024) -> int:
    """
    Returns the number of blocks used by the file at location `path`.

    Note:
        This function does not currently include the space occupied by inodes.

    Args:
        fs (DvcFileSystem): repository file system.
        path (str): location and file name of the target.
        repo (str): location of the DVC project or Git Repo.
        block_size (int, optional): bytes per file system block.

    Returns:
        blocks: Number of blocks used by the file on the file system.
    """
    size = fs.size(path)  # bytes
    size = (
        size if size else 0
    )  # TODO: Consider how to deal with missing size info
    return math.ceil(size / block_size)  # blocks
