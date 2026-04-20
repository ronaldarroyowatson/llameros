"""Tests for clean uninstall behavior."""

from __future__ import annotations

import subprocess
import winreg
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_script(installer_sandbox: dict, script_name: str, *args: str, expect_code: int = 0) -> subprocess.CompletedProcess:
    script_path = REPO_ROOT / "installer" / script_name
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            *args,
        ],
        cwd=REPO_ROOT,
        env=installer_sandbox["env"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expect_code, result.stderr
    return result


def _registry_exists(subkey: str) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey):
            return True
    except OSError:
        return False


def test_clean_uninstall_removes_all_artifacts(installer_sandbox: dict) -> None:
    run_script(installer_sandbox, "install.ps1")

    installer_sandbox["user_data_root"].mkdir(parents=True, exist_ok=True)
    (installer_sandbox["user_data_root"] / "state.json").write_text("{}", encoding="utf-8")

    run_script(installer_sandbox, "uninstall.ps1", "-RemoveUserData")

    assert not installer_sandbox["install_root"].exists()
    assert not (installer_sandbox["start_menu_root"] / "Llameros").exists()
    assert not _registry_exists(installer_sandbox["registry_subkey"])

    path_value = installer_sandbox["path_persist_file"].read_text(encoding="ascii").strip()
    bin_path = str(installer_sandbox["install_root"] / "bin")
    assert all(entry.lower() != bin_path.lower() for entry in path_value.split(";") if entry)

    assert not installer_sandbox["user_data_root"].exists()
