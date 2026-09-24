"""Clause metadata shared by the CLI, desktop UI and local web UI.

Keep the execution plan here so every interface describes the same suite that
the clause runner will execute.
"""

from __future__ import annotations


CLAUSE_CATALOG = {
    "1.1.1": {
        "name": "Secure Management Protocols",
        "testcases": [
            {"id": "TC1", "name": "SNMPv3 positive authentication", "description": "Verify authenticated SNMPv3 access is accepted."},
        ],
    },
    "1.6.1": {"name": "Network Security", "testcases": []},
    "1.6.5": {"name": "Secure Remote Access", "testcases": []},
}


def clause_names() -> dict[str, str]:
    return {clause_id: item["name"] for clause_id, item in CLAUSE_CATALOG.items()}


def execution_plan(clause_id: str) -> list[dict[str, str]]:
    """Return a copy suitable for serialising to the web client."""
    return [dict(testcase) for testcase in CLAUSE_CATALOG[clause_id]["testcases"]]
