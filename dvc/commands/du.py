"""
Implements the `dvc du` command
"""
import argparse
import logging
import math
from typing import List, Tuple

from dvc.cli import completion
from dvc.cli.command import CmdBaseNoRepo
from dvc.cli.utils import append_doc_link
from dvc.exceptions import DvcException
from dvc.ui import ui

logger = logging.getLogger(__name__)

SIZE_SUFFIXES = ("", "K", "M", "G", "T", "P", "E", "Z", "Y")


def _human_readable(n_bytes: int, block_size: int = 1024) -> str:
    """
    Returns a human-readable string representing a number of bytes.
    """
    if n_bytes == 0:  # avoid log(0) below
        return "0"
    suffix_idx = int(math.floor(math.log(n_bytes, block_size)))
    # divide by the number of bytes that corresponds to the suffix
    value = n_bytes / math.pow(block_size, suffix_idx)
    if value < 10:
        value_fmt = f"{value:.1f}"
    else:
        value_fmt = f"{value:.0f}"
    return value_fmt + SIZE_SUFFIXES[suffix_idx]


def _format_du_output(
    disk_usage: List[Tuple[str, int]], human_readable: int = False
) -> List[str]:
    """
    Converts `Repo.du` output into strings suitable for terminal output.
    """

    def fmt(path, size):
        size = _human_readable(size) if human_readable else size
        return f"{size:<7} {path}"

    return [fmt(path, size) for path, size in disk_usage]


class CmdDU(CmdBaseNoRepo):
    def run(self):
        from dvc.repo import Repo

        try:
            max_depth = 0 if self.args.summarize else self.args.max_depth
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

            if disk_usage:
                disk_usage_fmt = _format_du_output(
                    disk_usage, human_readable=self.args.human_readable
                )
                ui.write("\n".join(disk_usage_fmt))
            return 0
        except DvcException:
            logger.exception("failed to du '%s'", self.args.url)
            return 1


def add_parser(subparsers, parent_parser):
    DU_HELP = (
        "List disk usage of repository contents, including files"
        " and directories tracked by DVC and by Git."
    )
    list_parser = subparsers.add_parser(
        "du",
        parents=[parent_parser],
        description=append_doc_link(DU_HELP, "du"),
        help=DU_HELP,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    list_parser.add_argument("url", help="Location of DVC repository    ")
    list_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show all files, not just directories.",
    )
    list_parser.add_argument(
        "-d",
        "--max-depth",
        nargs="?",
        help="Show only objects N or fewer levels below the command line "
        "argument; --max-depth=0 is the same as --summarize.",
        metavar="N",
        type=int,
    )
    list_parser.add_argument(
        "--dvc-only", action="store_true", help="Show only DVC outputs."
    )
    list_parser.add_argument(
        "-s", "--summarize", action="store_true", help="Display only a total."
    )
    list_parser.add_argument(
        "-H",
        "--human-readable",
        action="store_true",
        help="Show sizes in human readable format (e.g., 1K 234M 2G).",
    )
    list_parser.add_argument(
        "-B",
        "--block-size",
        nargs="?",
        help="Scale sizes by SIZE before printing them.",
        metavar="SIZE",
        type=int,
    )
    list_parser.add_argument(
        "--rev",
        nargs="?",
        help="Git revision (e.g. SHA, branch, tag)",
        metavar="<commit>",
    )
    list_parser.add_argument(
        "path",
        nargs="?",
        help="Path to directory within the repository to list sizes for",
    ).complete = completion.DIR
    list_parser.set_defaults(func=CmdDU)
