"""
icaf/reporting/clause_reports/clause_1_1_3_report.py
─────────────────────────────────────────────────────────────────────────────
Report generator for ITSAR 1.1.3 — Role Based Access Control (RBAC).

Adapted from clause_1_6_5_report.py (same pattern/helpers), with:
  1. Reads results from context.scan_results["rbac_access_control"] (primary)
     then tc_objects[i].raw_result (fallback).
  2. Overall verdict: PASS only when every TC explicitly returned "PASS".
  3. Header patched: "ITSAR 1.1.1" → "ITSAR 1.1.3" via _patch_header_text().
  4. Safe imports — only imports symbols that exist in clause_1_2_4_report too.
  5. Content (requirement, objective, execution steps, compliance table) is
     written for the 4 RBAC test cases (TC1–TC4) covering:
       TC-113-001 — RBAC feature availability (≥3 roles created & verified)
       TC-113-002 — Authorised/unauthorised operations per configured role
       TC-113-003 — Allowed operations for each role vs. DUT-declared policy
       TC-113-004 — User creation without a role (default-assign or reject)

     ASSUMPTIONS (change in one place — see NOTE markers — if your
     record_result() uses different keys/IDs):
       - scan_results key = "rbac_access_control"
       - TC IDs = TC-113-001 .. TC-113-004
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import datetime
import subprocess

from icaf.reporting.helpers import (
    PURPLE, MID_GREY,
    PASS_GREEN, FAIL_RED,
    HEX_PURPLE,
    ERROR_ORANGE,
    section_heading, sub_heading, tc_heading,
    body_para, label_value_para, bullet_item,
    spacer, terminal_block, add_screenshot, status_result_table,
    two_col_info_table, four_col_table,
    build_doc_with_header_footer,
    _add_para_border_bottom,
)
from icaf.config.settings import settings

# NOTE: change this if your framework uses a different scan_results key.
SCAN_RESULTS_KEY = "rbac_access_control"


class Clause113Report:
    """
    Generates a .docx (then PDF) compliance report for ITSAR clause 1.1.3
    — Role Based Access Control.
    """

    def __init__(self, context, tc_objects: list):
        self.context    = context
        self.tc_objects = tc_objects

        # ── Primary: raw dicts written by record_result() ─────────────────
        scan = getattr(context, "scan_results", {}) or {}
        raw  = scan.get(SCAN_RESULTS_KEY, [])

        if raw:
            self.results = list(raw)
        else:
            # Fallback: unwrap from tc_objects
            self.results = [
                getattr(tc, "raw_result", {}) for tc in tc_objects
            ]

        # Drop empty dicts — they carry no useful information
        self.results = [r for r in self.results if r]

    # ── Public entry point ─────────────────────────────────────────────────

    def generate(self) -> str:
        results = self.results
        ctx     = self.context
        now     = datetime.datetime.now()

        passed  = sum(1 for r in results if r.get("verdict") == "PASS")
        total   = len(results)

        # PASS only when every TC passed — missing/empty verdict counts as FAIL
        overall = "PASS" if total > 0 and passed == total else "FAIL"

        failed  = total - passed
        errors  = sum(1 for r in results if r.get("verdict") == "ERROR")

        dut_name    = getattr(ctx, "dut_name",    None) or ctx.ssh_ip or "DUT"
        dut_version = getattr(ctx, "dut_version", None) or "Router OS"
        start_time  = (
            ctx.start_time.strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(ctx, "start_time")
            else now.strftime("%Y-%m-%d %H:%M:%S")
        )
        end_time = now.strftime("%Y-%m-%d %H:%M:%S")

        # ── Build document ─────────────────────────────────────────────────
        doc = build_doc_with_header_footer(dut_name, dut_version)
        # Patch header from hardcoded "1.1.1" to "1.1.3"
        self._patch_header_text(doc)

        # ── Front page ─────────────────────────────────────────────────────
        self._add_front_page(doc, dut_name, dut_version,
                             start_time, end_time, overall)

        # ── Section 1 ──────────────────────────────────────────────────────
        section_heading(doc, "1. Requirement Description")
        bullet_item(doc,
            "(i) The network product shall support Role Based Access Control "
            "(RBAC) with a minimum of 3 user roles for OAM privilege "
            "management, including authorization of the operation for "
            "configuration data and software via the network product "
            "console interface.")
        bullet_item(doc,
            "(ii) The RBAC system shall control how users or groups of users "
            "are allowed access to the various domains (Fault Management, "
            "Performance Management, System Admin, etc.) and what type of "
            "operation they can perform (View, Modify, Execute).")
        bullet_item(doc,
            "(iii) A user bound to one role must not be able to perform the "
            "operations reserved for a different role, and a user created "
            "without an explicit role must never be left in an ambiguous or "
            "unbounded-privilege state.")
        spacer(doc, small=True)

        # ── Section 2 ──────────────────────────────────────────────────────
        section_heading(doc, "2. DUT Configuration")
        sub_heading(doc, "2.1 Verification of RBAC Mechanisms")
        body_para(doc,
            "SSH inspection and CLI-driven configuration was performed to "
            "identify the RBAC configuration on the DUT. The following "
            "mechanisms were verified:")
        for b in [
            "Multiple user roles configured (rootsystem, netadmin, sysadmin, operator, or equivalent)",
            "User creation and role assignment restricted to the highest-privilege role",
            "Command-group / role policy inspectable via CLI (show running-config AAA authorization role)",
            "Per-role command authorization enforced for authorized and unauthorized operations",
            "Default role handling verified for users created without an explicit role",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "2.2 Test User Configuration")
        body_para(doc,
            "TC-113-001 creates at least three test users under distinct "
            f"roles on the DUT ({ctx.ssh_ip}) and verifies each on the DUT. "
            "TC-113-002 and TC-113-003 use these role accounts to exercise "
            "authorized and unauthorized operations. TC-113-004 creates a "
            "temporary test user without specifying any role to verify "
            "default-role handling; all test users are removed after "
            "execution.")
        spacer(doc, small=True)

        # ── Section 3 ──────────────────────────────────────────────────────
        section_heading(doc, "3. Preconditions")
        for b in [
            f"DUT must be running and reachable at {ctx.ssh_ip} on port 22 (SSH).",
            "Root/highest-privilege (rootsystem) credentials must be available for the primary session.",
            "The DUT must support CLI-based user creation and role assignment.",
            "Role/privilege list for the DUT must be obtained from vendor documentation beforehand.",
            "Python 3 with the ICAF framework and its SSH step libraries installed on the tester.",
            "Network connectivity between tester and DUT verified.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 4 ──────────────────────────────────────────────────────
        section_heading(doc, "4. Test Objective")
        body_para(doc,
            "To verify that the Device Under Test (DUT) correctly implements "
            "Role Based Access Control, as required by ITSAR clause 1.1.3. "
            "The test verifies that:")
        for b in [
            "RBAC is available and at least 3 distinct user roles can be created and verified on the DUT.",
            "Authorized operations succeed and unauthorized operations are denied, per configured role.",
            "Each role's actual command execution matches the role policy the DUT itself declares.",
            "A user created without an explicit role is either auto-assigned a defined default role "
            "with restricted privileges, or the creation is rejected outright — never left unbounded.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 5 ──────────────────────────────────────────────────────
        section_heading(doc, "5. Test Scenario")
        sub_heading(doc, "5.1 Number of Test Scenarios")
        body_para(doc, f"Total of {total} test cases were executed.")
        spacer(doc, small=True)

        two_col_info_table(doc,
            headers    =["Component", "Details"],
            col_widths =[3500, 5860],
            data_rows  =[
                ("Tester System",  f"Ubuntu Linux — {getattr(ctx, 'tester_ip', 'tester')}"),
                ("DUT",            f"IP Router — {ctx.ssh_ip}"),
                ("Protocol",       "SSH (CLI)"),
                ("Framework",      "ICAF — ITSAR Compliance Automation Framework"),
                ("Clause",         "ITSAR 1.1.3 — Role Based Access Control"),
            ]
        )
        spacer(doc, small=True)

        sub_heading(doc, "5.2 Tools Required")
        for b in [
            "Python 3 + ICAF SSH step libraries — CLI automation and command execution on DUT",
            "python-docx — ITSAR-format Word report generation",
            "tmux / visible terminal session — screenshot evidence capture",
            "wmctrl + xdotool + scrot/ImageMagick — real-time window screenshot capture",
            "OpenSSH client on tester for per-role session establishment",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "5.3 Test Execution Steps")
        for b in [
            "The tester establishes an SSH connection to the DUT as the rootsystem (highest-privilege) role.",
            "TC-113-001: Creates at least 3 users under different roles and verifies each on the DUT.",
            "TC-113-002: Executes an authorized and an unauthorized command for each configured role.",
            "TC-113-003: Reads each role's declared policy from the DUT, then verifies actual command "
            "enforcement matches that policy.",
            "TC-113-004: Attempts to create a user without specifying a role and verifies default-role "
            "assignment or outright rejection.",
            "After each TC, a screenshot of the terminal session is captured for evidence.",
            "Results are recorded per test case and a Word/PDF report is generated automatically.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 6 ──────────────────────────────────────────────────────
        section_heading(doc, "6. Expected Results for Pass")
        body_para(doc,
            "The DUT shall support RBAC with a minimum of 3 distinct user "
            "roles, verified by successful user creation and DUT-side "
            "confirmation. Authorized operations shall succeed and "
            "unauthorized operations shall be denied for every role. Actual "
            "command enforcement shall match the role policy declared by the "
            "DUT. A user created without an explicit role shall either be "
            "auto-assigned a defined default (least-privileged) role with "
            "correspondingly restricted operations, or the creation shall be "
            "rejected outright — no user shall be left with an undefined or "
            "unbounded privilege level.")
        spacer(doc, small=True)

        doc.add_page_break()

        # ── Section 7: Test Execution ──────────────────────────────────────
        section_heading(doc, "7. Test Execution")

        if not results:
            body_para(doc,
                "WARNING: No test results were recorded. "
                "Ensure record_result() is called in each TC and "
                f"context.scan_results['{SCAN_RESULTS_KEY}'] is populated.",
                bold=True)
        else:
            for r in results:
                tc_id   = r.get("tc_id",   "N/A")
                tc_name = r.get("tc_name", "N/A")
                verdict = r.get("verdict", "FAIL")
                vc = (PASS_GREEN  if verdict == "PASS"
                      else FAIL_RED if verdict in ("FAIL", "ERROR")
                      else ERROR_ORANGE)

                tc_heading(doc, f"Test Case: {tc_id}")
                label_value_para(doc, "a) Test Case Name",        tc_id)
                label_value_para(doc, "b) Test Case Description",
                                 r.get("description", tc_name))
                spacer(doc, small=True)

                body_para(doc, "c) Input Command:", bold=True)
                terminal_block(doc, [r.get("input_cmd", "(none)")])
                spacer(doc, small=True)

                label_value_para(doc, "d) Expected Result", r.get("expected", ""))
                body_para(doc, "e) Command Output:", bold=True)
                output_lines = str(r.get("output", "")).split("\n")[:50]
                terminal_block(doc, output_lines)
                spacer(doc, small=True)

                status_result_table(doc, verdict,
                                    label=f"{tc_id} — {tc_name[:60]}")
                spacer(doc, small=True)

                # Evidence: real screenshot or text dump
                for ef in (r.get("evidence_files") or []):
                    if not ef or not os.path.exists(ef):
                        continue
                    if ef.endswith(".png"):
                        body_para(doc, "Terminal Screenshot (Evidence):", bold=True)
                        add_screenshot(doc, ef, width_inches=5.5)

                spacer(doc)

        doc.add_page_break()

        # ── Section 8 ──────────────────────────────────────────────────────
        section_heading(doc, "8. Test Observation for Role Based Access Control")
        if overall == "PASS":
            body_para(doc,
                "It was observed that the Device Under Test (DUT) complies "
                "with the RBAC requirements of ITSAR clause 1.1.3. All test "
                "cases confirmed that RBAC is available with at least 3 "
                "distinct user roles, authorized/unauthorized operations are "
                "correctly enforced per role, actual enforcement matches the "
                "DUT-declared role policy, and users created without a role "
                "are never left with undefined or unbounded privileges.")
        else:
            failed_ids = [r.get("tc_id", "?") for r in results
                          if r.get("verdict") != "PASS"]
            body_para(doc,
                "It was observed that the Device Under Test (DUT) does not "
                "fully comply with the RBAC requirements of ITSAR clause "
                f"1.1.3. Failures identified in: "
                f"{', '.join(failed_ids) if failed_ids else 'unknown TCs'}.")
        spacer(doc, small=True)

        # ── Section 9 ──────────────────────────────────────────────────────
        section_heading(doc, "9. Test Case Result for Role Based Access Control")
        four_col_table(doc,
            headers    =["SL. No", "TEST CASE NAME", "PASS/FAIL", "Remarks"],
            col_widths =[700, 4500, 1500, 2660],
            data_rows  =(
                [
                    (str(i + 1),
                     f"{r.get('tc_id', '')} — {r.get('tc_name', '')[:45]}",
                     r.get("verdict", "FAIL"),
                     r.get("actual_status", "")[:60])
                    for i, r in enumerate(results)
                ]
                if results else [("—", "No results recorded", "FAIL", "")]
            ),
        )
        spacer(doc)

        status_result_table(doc, overall,
                            label=f"Overall Result — {passed}/{total} passed")
        spacer(doc)

        # ── Section 10 ─────────────────────────────────────────────────────
        section_heading(doc, "10. Compliance Analysis")
        two_col_info_table(doc,
            headers    =["Test Case", "Result"],
            col_widths =[7200, 2160],
            data_rows  =[
                ("TC-113-001 — RBAC Feature Availability (≥3 Roles Created & Verified)",
                 self._verdict("TC-113-001")),
                ("TC-113-002 — Authorised/Unauthorised Operations Per Configured Role",
                 self._verdict("TC-113-002")),
                ("TC-113-003 — Allowed Operations Per Role vs. DUT-Declared Policy",
                 self._verdict("TC-113-003")),
                ("TC-113-004 — User Creation Without a Role (Default-Assign or Reject)",
                 self._verdict("TC-113-004")),
            ]
        )
        spacer(doc)

        # ── Section 11 ─────────────────────────────────────────────────────
        section_heading(doc, "11. Conclusion")
        if overall == "PASS":
            body_para(doc,
                f"All {total} test cases passed. The DUT correctly implements "
                "Role Based Access Control. At least 3 distinct user roles "
                "were created and verified, authorized operations succeeded "
                "while unauthorized operations were denied for every role, "
                "actual enforcement matched the DUT-declared role policy, and "
                "users created without an explicit role were never left with "
                "undefined or unbounded privileges.")
        else:
            body_para(doc,
                f"The test run identified {failed} failing test case(s) and "
                f"{errors} error(s). The DUT does NOT fully comply with the "
                "RBAC requirements of ITSAR clause 1.1.3. Remediation is "
                "required before the DUT can be considered compliant.")
        spacer(doc, small=True)

        body_para(doc, "Recommendations:", bold=True)
        for b in [
            "Ensure the DUT supports at least 3 distinct, documented user roles for OAM privilege management.",
            "Restrict user creation and role assignment to the highest-privilege role only.",
            "Verify per-role command-group authorization is enforced consistently across all roles.",
            "Confirm actual command enforcement matches the role policy reported by the DUT's CLI.",
            "Ensure users created without an explicit role are either auto-assigned a defined default "
            "role or the creation is rejected — never left unbounded.",
            "Re-run this test suite after any configuration change to verify continued compliance.",
        ]:
            bullet_item(doc, b)

        # ── Save docx → PDF ────────────────────────────────────────────────
        ts         = now.strftime("%Y%m%d_%H%M%S")
        report_dir = str(settings.REPORT_DIR)
        os.makedirs(report_dir, exist_ok=True)
        docx_path  = os.path.join(report_dir, f"clause_1_1_3_report_{ts}.docx")
        doc.save(docx_path)

        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             docx_path, "--outdir", report_dir],
            capture_output=True, text=True,
        )
        pdf_path = docx_path.replace(".docx", ".pdf")
        if os.path.exists(pdf_path):
            os.remove(docx_path)
            return pdf_path
        return docx_path

    # ── Helpers ────────────────────────────────────────────────────────────

    def _verdict(self, tc_id: str) -> str:
        return next(
            (r.get("verdict", "N/A")
             for r in self.results if r.get("tc_id") == tc_id),
            "N/A",
        )

    @staticmethod
    def _patch_header_text(doc):
        """Replace hardcoded 'ITSAR 1.1.1' with 'ITSAR 1.1.3' in all headers."""
        try:
            for section in doc.sections:
                for para in section.header.paragraphs:
                    for run in para.runs:
                        if "1.1.1" in run.text:
                            run.text = run.text.replace(
                                "ITSAR 1.1.1", "ITSAR 1.1.3"
                            ).replace("1.1.1", "1.1.3")
        except Exception:
            pass

    def _add_front_page(self, doc, dut_name, dut_version,
                        start_time, end_time, overall):
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        spacer(doc, large=True)
        spacer(doc, large=True)

        def _centered(text, size_pt, color, bold=False):
            p   = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text)
            run.bold           = bold
            run.font.size      = Pt(size_pt)
            run.font.name      = "Arial"
            run.font.color.rgb = color
            return p

        p = _centered(
            "Role Based Access Control Compliance Test Report",
            22, PURPLE, bold=True,
        )
        _add_para_border_bottom(p, HEX_PURPLE, size=12)
        _centered(
            "ITSAR Clause 1.1.3 — Role Based Access Control",
            13, MID_GREY,
        )
        spacer(doc, large=True)

        four_col_table(doc,
            headers   =["Document No.", "Created By", "Reviewed By", "Approved By"],
            data_rows =[("2", "ICAF Framework", "Reviewer", "Approver")],
            col_widths=[2340, 2340, 2340, 2340],
        )
        spacer(doc, small=True)
        spacer(doc)

        two_col_info_table(doc,
            headers    =["Field", "Value"],
            col_widths =[3500, 5860],
            data_rows  =[
                ("DUT Details",             dut_name),
                ("DUT Host",                getattr(self.context, "ssh_ip", "N/A")),
                ("DUT Software Version",    dut_version),
                ("Type",                    "Auto Generated Validation Report"),
                ("Test Start",              start_time),
                ("Test End",                end_time),
                ("Requirement Test Result", overall),
            ]
        )
        doc.add_page_break()