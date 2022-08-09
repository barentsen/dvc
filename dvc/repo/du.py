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


# The GNU coreutils version of `du` appears to default to a block size
# of 1024 bytes, regardless of the actual block size configured for the
# file system.  We adopt the same convention here for consistency.
# Note: GNU `du` enables the block size to be configured using environment
# variables, which we don't support here yet. Reference docs:
# https://www.gnu.org/software/coreutils/manual/html_node/Block-size.html
DEFAULT_BLOCK_SIZE = 1024


def _disk_usage(
    fs: "DvcFileSystem", path: str, block_size: Optional[int] = None
) -> int:
    """
    Returns the expected number of blocks used by an object at location `path`.

    This is a helper function used by the `_du` function below.

    Note:
        The usage reported by this function may differ from the true device
        usage. For example, we do not account for internal fragmentation
        (e.g., unused gaps in blocks allocated to a file), sparse files,
        or the space used for file system data structures (e.g., the space
        needed to store indirect blocks which store the locations of data
        blocks). The numbers reported by this function match those obtained
        by calling the standard GNU `du` command with the `--apparent-size`
        argument.

    Args:
        fs: repository file system.
        path: location and name of the target (e.g., "data/data.xml").
        block_size: bytes per file system block.  Defaults to 1024 bytes.

    Returns:
        blocks: Number of blocks used by `path` on the file system.
    """
    block_size = block_size or DEFAULT_BLOCK_SIZE
    size = fs.size(path)  # bytes
    # TODO: is defaulting to zero size OK when size info is missing?
    size = size if size else 0
    return math.ceil(size / block_size)  # blocks


def du(
    url: str,
    path: Optional[str] = None,
    rev: Optional[str] = None,
    max_depth: Optional[int] = None,
    include_files: bool = False,
    dvc_only: bool = False,
    block_size: Optional[int] = None,
) -> List[Tuple[str, int]]:
    """
    Returns disk usage in unit blocks (not bytes).

    This function returns a list of (path, disk_usage) tuples,
    sorted by `path`.

    Args:
        url: Location of DVC repository.
        path: Path to a location within the repository to list (e.g., "data").
        rev: Git revision (e.g. SHA, branch, tag).
        max_depth: Show only objects `max_depth` or fewer levels below `path`.
        include_files: Show all files, not just directories.
        dvc_only: Show only DVC outputs.
        block_size: Size of file system blocks in bytes.

    Returns:
        disk_usage: list of (path, disk_usage) tuples.
            The usage is expressed in blocks (not bytes).
    """
    from . import Repo

    with Repo.open(url, rev=rev, subrepos=True, uninitialized=True) as repo:
        path = path or "."
        usage = _du(
            repo,
            path,
            max_depth=max_depth,
            include_files=include_files,
            dvc_only=dvc_only,
            block_size=block_size,
        )
        usage_list = sorted(usage.items(), key=lambda x: x[0])
        # The logic below ensures that the summary (path==".") appears last.
        # TODO: define a smarter sorting function to achieve this.
        if len(usage_list) > 1:
            usage_list = usage_list[1:] + [usage_list[0]]
        return usage_list


def _du(
    repo: "Repo",
    path: str,
    max_depth: Optional[int] = None,
    include_files: bool = False,
    dvc_only: bool = False,
    block_size: Optional[int] = None,
) -> Dict[str, int]:
    """
    Returns the disk usage as a dictionary mapping `path` onto `blocks`.
    """
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
