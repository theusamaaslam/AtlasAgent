"""Tests for source-based refreshes when Atlas is installed without git."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _patch_managed_uv():
    """Keep updater tests offline and make uv availability deterministic."""
    with patch("atlas_cli.managed_uv.update_managed_uv"), patch(
        "atlas_cli.managed_uv.ensure_uv", return_value=None
    ):
        yield


def test_pip_recommendation_points_at_the_checked_out_source():
    from atlas_cli import config

    command = config.recommended_update_command_for_method("pip")

    assert "-m pip install -e" in command
    assert str(Path(config.__file__).resolve().parent.parent) in command
    assert "--upgrade atlas-agent" not in command


class TestCmdUpdateSourceInstall:
    @patch("subprocess.run")
    def test_uses_uv_editable_install_outside_venv(self, mock_run, monkeypatch):
        from atlas_cli import main as atlas_main

        mock_run.return_value = subprocess.CompletedProcess([], 0)
        monkeypatch.setattr(atlas_main.sys, "prefix", "/usr")
        monkeypatch.setattr(atlas_main.sys, "base_prefix", "/usr")

        with patch("atlas_cli.managed_uv.ensure_uv", return_value="/usr/bin/uv"):
            atlas_main._cmd_update_pip(SimpleNamespace())

        assert mock_run.call_args.args[0] == [
            "/usr/bin/uv",
            "pip",
            "install",
            "--system",
            "-e",
            str(atlas_main.PROJECT_ROOT),
        ]
        assert "env" not in mock_run.call_args.kwargs

    @patch("subprocess.run")
    def test_exports_virtualenv_for_uv_editable_install(self, mock_run, monkeypatch):
        from atlas_cli import main as atlas_main

        mock_run.return_value = subprocess.CompletedProcess([], 0)
        monkeypatch.setattr(atlas_main.sys, "prefix", "/home/u/.atlas/venv")
        monkeypatch.setattr(atlas_main.sys, "base_prefix", "/usr")

        with patch("atlas_cli.managed_uv.ensure_uv", return_value="/usr/bin/uv"):
            atlas_main._cmd_update_pip(SimpleNamespace())

        assert mock_run.call_args.args[0] == [
            "/usr/bin/uv",
            "pip",
            "install",
            "-e",
            str(atlas_main.PROJECT_ROOT),
        ]
        assert mock_run.call_args.kwargs["env"]["VIRTUAL_ENV"] == "/home/u/.atlas/venv"

    @patch("subprocess.run")
    def test_falls_back_to_python_pip_editable_install(self, mock_run):
        from atlas_cli import main as atlas_main

        mock_run.return_value = subprocess.CompletedProcess([], 0)
        atlas_main._cmd_update_pip(SimpleNamespace())

        assert mock_run.call_args.args[0] == [
            atlas_main.sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            str(atlas_main.PROJECT_ROOT),
        ]

    @patch("subprocess.run")
    def test_refuses_a_non_source_public_package_upgrade(self, mock_run):
        from atlas_cli import main as atlas_main

        with patch("atlas_cli.config.running_from_source_tree", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                atlas_main._cmd_update_pip(SimpleNamespace())

        assert exc_info.value.code == 1
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_exits_nonzero_when_editable_install_fails(self, mock_run):
        from atlas_cli import main as atlas_main

        mock_run.return_value = subprocess.CompletedProcess([], 1)

        with pytest.raises(SystemExit) as exc_info:
            atlas_main._cmd_update_pip(SimpleNamespace())

        assert exc_info.value.code == 1
