"""Dummy AI-like workload used by integration tests."""
from __future__ import annotations

import argparse
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="llama-test-agent")
    parser.parse_args()

    while True:
        time.sleep(0.2)


if __name__ == "__main__":
    main()