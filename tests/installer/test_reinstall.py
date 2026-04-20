"""Tests for reinstall lifecycle behavior."""

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


def _read_registry_values(subkey: str) -> dict[str, str]:
    values: dict[str, str] = {}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
        index = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, index)
                values[name] = value
                index += 1
            except OSError:
                break
    return values


def test_reinstall_overwrites_and_remains_clean(installer_sandbox: dict) -> None:
    run_script(installer_sandbox, "install.ps1")

    readme_installed = installer_sandbox["install_root"] / "README.md"
    readme_installed.write_text("stale content\n", encoding="utf-8")

    run_script(installer_sandbox, "install.ps1", "-Reinstall")

    expected_readme = (installer_sandbox["source_root"] / "README.md").read_text(encoding="utf-8")
    assert readme_installed.read_text(encoding="utf-8") == expected_readme

    registry_values = _read_registry_values(installer_sandbox["registry_subkey"])
    assert registry_values["InstallPath"] == str(installer_sandbox["install_root"])
    assert registry_values["Version"] == "1.0.1"

    persisted_path = installer_sandbox["path_persist_file"].read_text(encoding="ascii").strip()
    bin_path = str(installer_sandbox["install_root"] / "bin")
    entries = [entry for entry in persisted_path.split(";") if entry]
    matching = [entry for entry in entries if entry.lower() == bin_path.lower()]
    assert len(matching) == 1
