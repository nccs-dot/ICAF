"""
icaf/core/result_recorder.py
─────────────────────────────────────────────────────────────────────────────
Shared result recorder for clause test cases.

Your testcases call:
    record_result(tc_id, tc_name, description, input_cmd, output,
                  expected, actual_status, verdict, evidence_files)
    save_evidence(tc_id, command, output)

Results are stored in a flat list for the report generator.
"""

import os
import datetime

from icaf.utils.logger import logger

# ── In-memory store (reset each run) ─────────────────────────────────────────
_results: list[dict] = []
_terminal_manager = None


# ── Public API ────────────────────────────────────────────────────────────────

def set_terminal_manager(tm):
    global _terminal_manager
    _terminal_manager = tm


def get_results() -> list[dict]:
    return _results


def clear_results():
    global _results
    _results = []


def record_result(
    tc_id: str,
    tc_name: str,
    description: str,
    input_cmd: str,
    output: str,
    expected: str,
    actual_status: str,
    verdict: str,
    evidence_files: list | None = None,
):
    """
    Store one test-case result.  Verdict must be 'PASS', 'FAIL', or 'ERROR'.
    """
    shot = _take_screenshot(tc_id, input_cmd, output, verdict)
    all_evidence = list(evidence_files or [])
    if shot:
        all_evidence.append(shot)

    entry = {
        "tc_id":          tc_id,
        "tc_name":        tc_name,
        "description":    description,
        "input_cmd":      input_cmd,
        "output":         output,
        "expected":       expected,
        "actual_status":  actual_status,
        "verdict":        verdict,
        "evidence_files": all_evidence,
        "timestamp":      datetime.datetime.now().isoformat(),
    }
    _results.append(entry)

    icon = "[+]" if verdict == "PASS" else ("[-]" if verdict == "FAIL" else "[!]")
    logger.info(f"{icon} {tc_id} — {tc_name}: {verdict}")


def save_evidence(tc_id: str, command: str, output: str, extra_info: str = "") -> str:
    """
    Write a plain-text evidence file and return its path.
    Files go into output/runs/clause_1_6_5/<tc_id>/logs/ (created on demand).
    """
    evidence_dir = _ensure_evidence_dir(tc_id)
    timestamp    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath     = os.path.join(evidence_dir, f"{tc_id}_{timestamp}.txt")

    with open(filepath, "w") as fh:
        fh.write(f"Test Case : {tc_id}\n")
        fh.write(f"Timestamp : {datetime.datetime.now().isoformat()}\n")
        fh.write("=" * 60 + "\n")
        fh.write(f"COMMAND:\n{command}\n\nOUTPUT:\n{output}\n")
        if extra_info:
            fh.write(f"\nADDITIONAL INFO:\n{extra_info}\n")

    return filepath


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ensure_evidence_dir(tc_id: str) -> str:
    base = os.path.join("output", "runs", "clause_1_6_5", tc_id, "logs")
    os.makedirs(base, exist_ok=True)
    return base


# Screenshots are handled by the clause runners.
def _take_screenshot(tc_id: str, command: str, output: str, verdict: str) -> str | None:
    return None
