# Llameros Bugfix Workflow

## Overview

This document defines the mandatory test-first bugfix workflow for Llameros.
No bug may be fixed without a failing test that reproduces it.

## Workflow Steps

1. Identify a bug (either discovered by the agent or reported by me).
2. Create a failing test that:
   - Reproduces the bug deterministically
   - Fails for the correct reason
   - Flags the correct condition
3. Run the test to confirm it fails.
4. Implement the minimal fix.
5. Run the test again to confirm it now passes.
6. Expand the test with:
   - Edge cases
   - Common variations of the bug type
   - Regression scenarios
7. Add the test to the permanent suite.
8. Run the full suite:
   - Unit tests
   - Integration tests
   - Smoke tests
   - Live tests
   - Installer lifecycle tests:
     - tests/installer/test_clean_install.py
     - tests/installer/test_clean_uninstall.py
     - tests/installer/test_repair_install.py
     - tests/installer/test_reinstall.py
     - tests/installer/test_detect_previous_install.py
     - tests/installer/test_version_bump.py
9. Clear the VS Code Problems pane.
10. Bump the bugfix version number:
    - Major.Minor.Bugfix
    - Example: 1.1.10 -> 1.1.11
11. Commit, push, and sync to Git.

## Rules

- No fix may be written before a failing test exists.
- No test may be removed without explicit instruction.
- All tests must be deterministic.
- All bugfixes must update the Codex.
