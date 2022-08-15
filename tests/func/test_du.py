"""
Functional tests for the `dvc du` cli command.
"""
from dvc.cli import main
from tests.basic_env import TestDvc


class TestCmdDU(TestDvc):
    def test_default(self):
        """Test running `dvc du` with the default parameters."""
        ret = main(["du"])
        self.assertEqual(ret, 0)
        out, _ = self._capsys.readouterr()
        assert sorted(out.splitlines()) == [
            "10      .",
            "2       ./data_dir/data_sub_dir",
            "4       ./data_dir",
        ]

    def test_summarize(self):
        """Test running `dvc du` with the `--summarize` flag."""
        for argument in ["-s", "--summarize"]:
            ret = main(["du", argument])
            self.assertEqual(ret, 0)
            out, _ = self._capsys.readouterr()
            assert out.splitlines() == ["10      ."]

    def test_include_all_files(self):
        """Test running `dvc du` with the `--all` flag."""
        for argument in ["-a", "--all"]:
            ret = main(["du", argument])
            self.assertEqual(ret, 0)
            out, _ = self._capsys.readouterr()
            assert sorted(out.splitlines()) == [
                "1       ./.dvcignore",
                "1       ./bar",
                "1       ./code.py",
                "1       ./data_dir/data",
                "1       ./data_dir/data_sub_dir/data_sub",
                "1       ./foo",
                "1       ./тест",
                "10      .",
                "2       ./data_dir/data_sub_dir",
                "4       ./data_dir",
            ]

    def test_max_depth(self):
        """Test running `dvc du` with the `--max-depth` parameter."""
        for argument in ["-d", "--max-depth="]:
            for depth in [0, 1, 2]:
                ret = main(["du", f"{argument}{depth}"])
                self.assertEqual(ret, 0)
                out, _ = self._capsys.readouterr()
                # The test repo contains exactly 1 dir and 1 subdir:
                assert len(out.splitlines()) == depth + 1
