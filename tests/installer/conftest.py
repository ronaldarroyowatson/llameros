"""Shared fixtures for installer lifecycle tests."""

from __future__ import annotations

import os
import platform
import shutil
import uuid
import winreg
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _create_source_tree(source_root: Path) -> None:
    (source_root / "src").mkdir(parents=True, exist_ok=True)
    (source_root / "config").mkdir(parents=True, exist_ok=True)

    (source_root / "src" / "main.py").write_text(
        '"""Sandbox main entry."""\nprint("llameros sandbox")\n',
        encoding="utf-8",
    )
    (source_root / "config" / "rules.yaml").write_text(
        "vram_limit_mb: 14000\nram_limit_mb: 30000\nprocesses:\n  - python.exe\n",
        encoding="utf-8",
    )
    (source_root / "VERSION").write_text("1.0.1\n", encoding="utf-8")
    (source_root / "README.md").write_text("Llameros sandbox\n", encoding="utf-8")
    (source_root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (source_root / "requirements.txt").write_text("pytest\n", encoding="utf-8")


def _registry_subkey_from_ps_path(ps_path: str) -> str:
    prefix = "HKCU:\\"
    if not ps_path.startswith(prefix):
        raise ValueError(f"Unsupported registry path for tests: {ps_path}")
    return ps_path[len(prefix) :]


def _delete_registry_tree(subkey: str) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as root:
            child_names = []
            index = 0
            while True:
                try:
                    child_names.append(winreg.EnumKey(root, index))
                    index += 1
                except OSError:
                    break
    except OSError:
        return

    for child in child_names:
        _delete_registry_tree(f"{subkey}\\{child}")

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)
    except OSError:
        pass


@pytest.fixture
def installer_sandbox(tmp_path: Path):
    if platform.system() != "Windows":
        pytest.skip("Installer lifecycle tests require Windows")

    source_root = tmp_path / "source"
    install_root = tmp_path / "ProgramFiles" / "Llameros"
    start_menu_root = tmp_path / "StartMenu"
    path_persist_file = tmp_path / "persisted_path.txt"
    install_log = install_root / "installer.log"
    user_data_root = tmp_path / "UserData"

    _create_source_tree(source_root)

    registry_base = f"HKCU:\\Software\\LlamerosInstallerTests\\{uuid.uuid4().hex}"

    env = os.environ.copy()
    env["LLAMEROS_SOURCE_ROOT"] = str(source_root)
    env["LLAMEROS_INSTALL_ROOT"] = str(install_root)
    env["LLAMEROS_START_MENU_ROOT"] = str(start_menu_root)
    env["LLAMEROS_PATH_PERSIST_FILE"] = str(path_persist_file)
    env["LLAMEROS_INSTALL_LOG"] = str(install_log)
    env["LLAMEROS_REGISTRY_BASE"] = registry_base
    env["LLAMEROS_USER_DATA_ROOT"] = str(user_data_root)

    data = {
        "env": env,
        "source_root": source_root,
        "install_root": install_root,
        "start_menu_root": start_menu_root,
        "path_persist_file": path_persist_file,
        "install_log": install_log,
        "registry_base": registry_base,
        "registry_subkey": _registry_subkey_from_ps_path(registry_base),
        "user_data_root": user_data_root,
    }

    yield data

    _delete_registry_tree(data["registry_subkey"])
    shutil.rmtree(tmp_path, ignore_errors=True)
