"""Run the full Llameros test suite in deterministic stage order."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_stage(stage_path: Path) -> int:
    command = [sys.executable, "-m", "pytest", str(stage_path)]
    print(f"\n=== Running {stage_path.name} tests ===")
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    tests_root = repo_root / "tests"
    stages = [
        "unit",
        "integration",
        "smoke",
        "live",
        "installer",
    ]

    results: list[tuple[str, int]] = []
    for stage in stages:
        stage_path = tests_root / stage
        exit_code = run_stage(stage_path)
        results.append((stage, exit_code))
        if exit_code != 0:
            break

    print("\n=== Full Test Suite Summary ===")
    for stage, code in results:
        status = "PASS" if code == 0 else "FAIL"
        print(f"{stage}: {status}")

    all_passed = len(results) == len(stages) and all(code == 0 for _, code in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
