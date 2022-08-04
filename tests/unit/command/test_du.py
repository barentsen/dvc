"""
Unit tests for the `dvc du` cli command.
"""
from dvc.cli import parse_args
from dvc.commands.du import CmdDU


def _test_cli(mocker, *args):
    cli_args = parse_args(["du", *args])
    assert cli_args.func == CmdDU

    cmd = cli_args.func(cli_args)
    m = mocker.patch("dvc.repo.Repo.du")

    assert cmd.run() == 0
    return m


def test_list(mocker):
    url = "local_dir"
    m = _test_cli(mocker, url)
    m.assert_called_once_with(
        url,
        path=None,
        rev=None,
        max_depth=None,
        include_files=False,
        dvc_only=False,
        block_size=None,
    )
