"""Regression tests for bugfix workflow-driven fixes."""
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_gui_treeview_uses_yscrollcommand_keyword():
    """Treeview.configure should use ttk's yscrollcommand keyword."""
    gui_source = _read_text("src/llameros/gui.py")
    assert "yscrollcommand=scroll_y.set" in gui_source
    assert "yscroll=scroll_y.set" not in gui_source


def test_docs_do_not_contain_hard_tabs():
    """Docs should not use hard tabs to avoid markdown lint violations."""
    codex = _read_text("docs/CODEX.md")
    workflow = _read_text("docs/BUGFIX_WORKFLOW.md")
    assert "\t" not in codex
    assert "\t" not in workflow
    assert "|---|---|" not in codex


def test_codex_update_log_fence_has_language():
    """The codex update-log code fence should include an explicit language."""
    codex = _read_text("docs/CODEX.md")
    assert "```text" in codex


def test_workflow_heading_spacing_regression():
    """Headings should be followed by a blank line for markdown consistency."""
    workflow_lines = _read_text("docs/BUGFIX_WORKFLOW.md").splitlines()
    for idx, line in enumerate(workflow_lines):
        if line.startswith("## ") and idx + 1 < len(workflow_lines):
            assert workflow_lines[idx + 1].strip() == ""