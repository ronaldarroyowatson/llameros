"""Tests for repair behavior."""

from __future__ import annotations

import subprocess
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


def test_repair_restores_missing_files(installer_sandbox: dict) -> None:
    run_script(installer_sandbox, "install.ps1")

    main_py = installer_sandbox["install_root"] / "src" / "main.py"
    version_file = installer_sandbox["install_root"] / "VERSION"
    main_py.unlink()
    version_file.unlink()

    detect_before = run_script(installer_sandbox, "detect_previous_install.ps1")
    assert detect_before.stdout.strip().splitlines()[-1] == "corrupted"

    run_script(installer_sandbox, "repair.ps1")

    assert main_py.exists()
    assert version_file.exists()

    detect_after = run_script(installer_sandbox, "detect_previous_install.ps1")
    assert detect_after.stdout.strip().splitlines()[-1] == "installed"

    install_log = installer_sandbox["install_log"]
    assert "Repair completed." in install_log.read_text(encoding="utf-8")
