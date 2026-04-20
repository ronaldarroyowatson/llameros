"""Installer placeholder tests for version bump flow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import tools.bump_version


def test_version_bump_placeholder():
    assert tools.bump_version is not None
    assert True
