"""
Implements the `Repo.du()` method.
"""
import math
from os.path import join
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, Optional, Tuple

if TYPE_CHECKING:
    from dvc.fs.dvc import DvcFileSystem


# The GNU coreutils version of `du` appears to default to a block size
# of 1024 bytes, regardless of the actual block size configured for the
# file system.  We adopt the same convention here for consistency.
# Note: GNU `du` enables the block size to be configured using environment
# variables, which we don't support here yet. Reference docs:
# https://www.gnu.org/software/coreutils/manual/html_node/Block-size.html
DEFAULT_BLOCK_SIZE = 1024


def du(
    url: str,
    path: Optional[str] = None,
    rev: Optional[str] = None,
    max_depth: Optional[int] = None,
    include_files: bool = False,
    dvc_only: bool = False,
    block_size: Optional[int] = None,
) -> Generator[Tuple[str, int], None, None]:
    """
    Yields (path, disk_usage) tuples.

    Args:
        url: Location of DVC repository.
        path: Path to a location within the repository to list (e.g., "data").
        rev: Git revision (e.g. SHA, branch, tag).
        max_depth: Show only objects `max_depth` or fewer levels below `path`.
        include_files: Show all files, not just directories.
        dvc_only: Show only DVC outputs.
        block_size: Size of file system blocks in bytes.

    Yields:
        (path, disk_usage): Disk usage expressed in units of `block_size`.
    """
    from . import Repo

    path = path or "."

    with Repo.open(url, rev=rev, subrepos=True, uninitialized=True) as repo:
        fs: "DvcFileSystem" = repo.dvcfs
        fs_path: str = fs.from_os_path(path)

        # Walk through the directories in a bottom-up fashion, so we can
        # use dynamic programming to compute the directory sizes efficiently.
        # ``usage_map`` will tabulate path=>usage along the way.
        usage_map: Dict[str, int] = {}
        walk = list(fs.walk(fs_path, dvcfiles=True, dvc_only=dvc_only))[::-1]
        for root, dirs, files in walk:
            # 1. Sum the sizes of all *files* in the current `root` dir
            total_file_usage = 0
            file_paths = [join(root, name) for name in files]
            for current_file in file_paths:
                current_file_usage = _disk_usage(
                    fs, current_file, block_size=block_size
                )
                total_file_usage += current_file_usage
                if include_files and _max_depth_satisfied(
                    current_file, max_depth
                ):
                    yield (current_file, current_file_usage)

            # 2. Sum the sizes of all *subdirs* in the current `root`
            total_subdir_usage = sum(
                usage_map.get(join(root, d), 0) for d in dirs
            )

            # 3. Determine total size of `root` by summing 1+2+size(root)
            usage_map[root] = (
                total_file_usage
                + total_subdir_usage
                + _disk_usage(fs, root, block_size=block_size)
            )
            if _max_depth_satisfied(root, max_depth):
                yield (root, usage_map[root])


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
    size = size if size else 0
    return math.ceil(size / block_size)  # blocks


def _max_depth_satisfied(path: str, max_depth: Optional[int]) -> bool:
    """Returns True if `path` has `max_depth` or fewer parents.

    Examples:
        >>> _max_depth_satisfied("./path/to/file", max_depth=10)
        True
        >>> _max_depth_satisfied("./path/to/file", max_depth=1)
        False
    """
    if (max_depth is None) or (len(Path(path).parents) <= max_depth):
        return True
    return False
