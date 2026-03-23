import shutil
from pathlib import Path

import pytest


@pytest.fixture
def runtime_root(tmp_path):
    """Minimal runtime root with real config files copied in."""
    repo = Path(__file__).resolve().parents[1]
    shutil.copytree(repo / "config", tmp_path / "config")
    shutil.copytree(repo / "vault", tmp_path / "vault")
    shutil.copytree(repo / "frontend", tmp_path / "frontend")
    return tmp_path
