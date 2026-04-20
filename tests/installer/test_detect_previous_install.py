"""Tests for previous-install detection script."""

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


def test_detect_previous_install_states(installer_sandbox: dict) -> None:
    none_result = run_script(installer_sandbox, "detect_previous_install.ps1")
    assert none_result.stdout.strip().splitlines()[-1] == "none"

    run_script(installer_sandbox, "install.ps1")

    installed_result = run_script(installer_sandbox, "detect_previous_install.ps1")
    assert installed_result.stdout.strip().splitlines()[-1] == "installed"

    (installer_sandbox["install_root"] / "VERSION").unlink()

    corrupted_result = run_script(installer_sandbox, "detect_previous_install.ps1")
    assert corrupted_result.stdout.strip().splitlines()[-1] == "corrupted"
