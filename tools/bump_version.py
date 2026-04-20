"""Increment the bugfix segment in the VERSION file."""
from __future__ import annotations

from pathlib import Path


def bump_bugfix(version_text: str) -> str:
    raw = version_text.strip()
    parts = raw.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid version format: {raw!r}. Expected Major.Minor.Bugfix")

    major, minor, bugfix = (int(part) for part in parts)
    return f"{major}.{minor}.{bugfix + 1}"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    version_path = repo_root / "VERSION"

    current = version_path.read_text(encoding="utf-8").strip()
    next_version = bump_bugfix(current)
    version_path.write_text(f"{next_version}\n", encoding="utf-8")

    print(f"Bumped version: {current} -> {next_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
