"""
Implements the `dvc du` command
"""
import argparse
import logging
import math
from pathlib import Path

from dvc.cli import completion
from dvc.cli.command import CmdBaseNoRepo
from dvc.cli.utils import append_doc_link
from dvc.exceptions import DvcException
from dvc.ui import ui

logger = logging.getLogger(__name__)

SIZE_SUFFIXES = ("", "K", "M", "G", "T", "P", "E", "Z", "Y")


class CmdDU(CmdBaseNoRepo):
    def run(self):
        from dvc.repo import Repo

        try:
            # `--summarize` sets max-depth to the depth of the requested path
            if self.args.summarize:
                max_depth = (
                    len(Path(self.args.path).parents) if self.args.path else 0
                )
            else:
                max_depth = self.args.max_depth

            # `--human-readable` overrides the block size to be 1 byte
            block_size = (
                1 if self.args.human_readable else self.args.block_size
            )

            disk_usage = Repo.du(
                self.args.url,
                path=self.args.path,
                rev=self.args.rev,
                max_depth=max_depth,
                include_files=self.args.all,
                dvc_only=self.args.dvc_only,
                block_size=block_size,
            )

            # Format the output, line by line
            for path, usage in disk_usage:
                out = _format_du_output(
                    path, usage, human_readable=self.args.human_readable
                )
                ui.write(out)

            return 0
        except DvcException:
            logger.exception("failed to du '%s'", self.args.url)
            return 1


def add_parser(subparsers, parent_parser):
    DU_HELP = (
        "Show expected disk usage of repository contents, including files"
        " and directories tracked by DVC and by Git.  Note that this tool"
        " reports the apparent sizes of files, i.e., those you would obtain"
        " by calling the GNU `du` command with the `--apparent-size` option."
    )
    list_parser = subparsers.add_parser(
        "du",
        parents=[parent_parser],
        description=append_doc_link(DU_HELP, "du"),
        help=DU_HELP,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    list_parser.add_argument(
        "url", help="Location of the DVC repository.", nargs="?", default="."
    )
    list_parser.add_argument(
        "path",
        nargs="?",
        help="Path to directory within the repository to list sizes for",
    ).complete = completion.DIR
    list_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show all files, not just directories.",
    )
    list_parser.add_argument(
        "--dvc-only", action="store_true", help="Show only DVC outputs."
    )
    list_parser.add_argument(
        "--rev",
        nargs="?",
        help="Git revision (e.g. SHA, branch, tag).",
        metavar="<commit>",
    )
    list_parser.add_argument(
        "-d",
        "--max-depth",
        nargs="?",
        help="Show only objects N or fewer levels below the path.",
        metavar="N",
        type=int,
    )
    list_parser.add_argument(
        "-s", "--summarize", action="store_true", help="Display only a total."
    )
    list_parser.add_argument(
        "-H",
        "--human-readable",
        action="store_true",
        help="Show sizes in human readable format (e.g., 234M).",
    )
    list_parser.add_argument(
        "-B",
        "--block-size",
        nargs="?",
        help="Scale sizes by SIZE bytes before printing them."
        " Defaults to 1024 bytes.",
        metavar="SIZE",
        type=int,
    )
    list_parser.set_defaults(func=CmdDU)


def _human_readable(n_bytes: int, block_size: int = 1024) -> str:
    """
    Returns a human-readable string representing a number of bytes.

    Intends to replicate the format returned by GNU's ``du -h``.

    Examples:
        >>> _human_readable(0)
        '0'
        >>> _human_readable(1024)
        '1.0K'
        >>> _human_readable(20*1024**3)
        '20G'
    """
    if n_bytes == 0:  # avoid log(0) below
        return "0"
    suffix_idx = int(math.floor(math.log(n_bytes, block_size)))
    try:
        suffix = SIZE_SUFFIXES[suffix_idx]
    except IndexError:
        suffix = "?"  # Suffixes are undefined beyond 'yotta'
    value = n_bytes / math.pow(block_size, suffix_idx)
    # Note: GNU du appears to round up, so we do the same:
    if value < 10:
        value_fmt = f"{math.ceil(value*10)/10:.1f}"
    else:
        value_fmt = f"{math.ceil(value):.0f}"
    return value_fmt + suffix


def _format_du_output(
    path: str, usage: int, human_readable: int = False
) -> str:
    """
    Converts `Repo.du` output into strings suitable for terminal output.
    """
    usage_out = _human_readable(usage) if human_readable else usage
    return f"{usage_out:<7} {path}"