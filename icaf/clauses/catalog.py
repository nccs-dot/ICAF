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
    "1.1.3": {
        "name": "Role-Based Access Control",
        "testcases": [
            {"id": "TC1_RBAC_FEATURE_AVAILABILITY", "name": "RBAC feature availability", "description": "Create and verify users across at least three roles."},
            {"id": "TC2_ROLE_COMMAND_AUTHORIZATION", "name": "Role command authorization", "description": "Confirm allowed commands succeed and prohibited commands are denied."},
            {"id": "TC3_ALLOWED_OPERATIONS_PER_ROLE", "name": "Allowed operations per role", "description": "Compare each role's enforced operations with its DUT policy."},
            {"id": "TC4_USER_CREATION_WITHOUT_ROLE", "name": "User creation without a role", "description": "Verify role-less users are assigned a safe default role or rejected."},
        ],
    },
    "1.2.1": {
        "name": "User Authentication",
        "testcases": [
            {"id": "TC1", "name": "Console — no authentication", "description": "Verify console access cannot proceed without credentials."},
            {"id": "TC2", "name": "Console — correct authentication", "description": "Verify valid console credentials are accepted."},
            {"id": "TC3", "name": "Console — incorrect authentication", "description": "Verify invalid console credentials are rejected."},
            {"id": "TC4", "name": "SSH — no authentication", "description": "Verify SSH access cannot proceed without credentials."},
            {"id": "TC5", "name": "SSH — correct authentication", "description": "Verify valid SSH credentials are accepted."},
            {"id": "TC6", "name": "SSH — incorrect authentication", "description": "Verify invalid SSH credentials are rejected."},
            {"id": "TC7", "name": "SFTP — no authentication", "description": "Verify SFTP access cannot proceed without credentials."},
            {"id": "TC8", "name": "SFTP — correct authentication", "description": "Verify valid SFTP credentials are accepted."},
            {"id": "TC9", "name": "SFTP — incorrect authentication", "description": "Verify invalid SFTP credentials are rejected."},
            {"id": "TC10", "name": "SCP — no authentication", "description": "Verify SCP access cannot proceed without credentials."},
            {"id": "TC11", "name": "SCP — correct authentication", "description": "Verify valid SCP credentials are accepted."},
            {"id": "TC12", "name": "SCP — incorrect authentication", "description": "Verify invalid SCP credentials are rejected."},
        ],
    },
    "1.2.4": {"name": "Password Policy Compliance", "testcases": []},
    "1.6.1": {"name": "Network Security", "testcases": []},
    "1.6.5": {"name": "Secure Remote Access", "testcases": []},
}


def clause_names() -> dict[str, str]:
    return {clause_id: item["name"] for clause_id, item in CLAUSE_CATALOG.items()}


def execution_plan(clause_id: str) -> list[dict[str, str]]:
    """Return a copy suitable for serialising to the web client."""
    return [dict(testcase) for testcase in CLAUSE_CATALOG[clause_id]["testcases"]]
