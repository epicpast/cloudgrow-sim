"""Tests for cloudgrow_sim.main module."""

from __future__ import annotations

from cloudgrow_sim import __version__
from cloudgrow_sim.main import main


def test_version() -> None:
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_main_returns_zero() -> None:
    """Test that main() returns 0."""
    result = main()
    assert result == 0
