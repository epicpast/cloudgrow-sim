"""Tests for cloudgrow_sim.main module."""

from __future__ import annotations

from typer.testing import CliRunner

from cloudgrow_sim import __version__
from cloudgrow_sim.main import app

runner = CliRunner()


def test_version() -> None:
    """Test that version is defined and follows semver."""
    assert __version__
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_app_shows_help() -> None:
    """Test that app shows help when called with no args."""
    result = runner.invoke(app, [])
    # With no_args_is_help=True, typer shows help but exits with code 2
    assert result.exit_code == 2
    assert "ASHRAE-compliant" in result.stdout or "Usage:" in result.stdout
