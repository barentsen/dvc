"""
Unit tests for the `dvc du` cli command.

Notes:
    * The tests in this file verify whether the cli command passes arguments
      to the `dvc.repo.Repo.du` API correctly.
    * The tests make use of the ``pytest-mock`` plugin which provides a
      ``mocker`` fixture which wraps the ``mock`` package.

Todo:
    * Increase coverage to cover all arguments.
"""
import pytest

from dvc.cli import parse_args
from dvc.commands.du import CmdDU


def _test_cli(mocker, *args):
    cli_args = parse_args(["du", *args])
    assert cli_args.func == CmdDU

    cmd = cli_args.func(cli_args)
    m = mocker.patch("dvc.repo.Repo.du")

    assert cmd.run() == 0
    return m


def test_du(mocker):
    """Does `dvc du` call `dvc.repo.Repo.du` with the default args?"""
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


@pytest.mark.parametrize("argument", ["-a", "--all"])
def test_du_include_files(mocker, argument):
    """Can `dvc du` be called with the "-a"/"--all" option?"""
    url = "local_dir"
    m = _test_cli(mocker, url, argument)
    m.assert_called_once_with(
        url,
        path=None,
        rev=None,
        max_depth=None,
        include_files=True,
        dvc_only=False,
        block_size=None,
    )


def test_du_path(mocker):
    """Can `dvc du` be called with the "path" argument?"""
    url = "local_dir"
    path = "subdir"
    m = _test_cli(mocker, url, path)
    m.assert_called_once_with(
        url,
        path=path,
        rev=None,
        max_depth=None,
        include_files=False,
        dvc_only=False,
        block_size=None,
    )


def test_basic_formatting(mocker, capsys):
    """Verify the basic stdout formatting of ``dvc du``."""
    cli_args = parse_args(["du", "local_dir"])
    assert cli_args.func == CmdDU
    cmd = cli_args.func(cli_args)

    result = [
        ("README.md", 10),
        ("data/data.xml", 100),
        (".", 1000),
    ]
    mocker.patch("dvc.repo.Repo.du", return_value=result)

    assert cmd.run() == 0
    out, _ = capsys.readouterr()
    output = out.splitlines()

    assert output == [
        "10      README.md",
        "100     data/data.xml",
        "1000    .",
    ]


@pytest.mark.parametrize("argument", ["-H", "--human-readable"])
@pytest.mark.parametrize(
    "file_size,expected",
    [
        (100, "100"),
        (1.0 * 1024, "1.0K"),
        (1.5 * 1024**2, "1.5M"),
        (1.9 * 1024**3, "1.9G"),
        (2.5 * 1024**4, "2.5T"),
        (5 * 1024**5, "5.0P"),
        (10 * 1024**6, "10E"),
        (100 * 1024**7, "100Z"),
        (999 * 1024**8, "999Y"),
        (1024**9, "1.0?"),
    ],
)
def test_human_readable_formatting(
    mocker, capsys, argument, file_size, expected
):
    """Verify the output of ``dvc du --human-friendly``."""
    cli_args = parse_args(["du", "local_dir", argument])
    cmd = cli_args.func(cli_args)

    result = [("data/data.xml", file_size)]
    mocker.patch("dvc.repo.Repo.du", return_value=result)

    assert cmd.run() == 0
    out, _ = capsys.readouterr()
    assert out.startswith(expected)
