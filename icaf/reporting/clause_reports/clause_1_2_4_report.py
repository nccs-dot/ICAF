"""
icaf/reporting/clause_reports/clause_1_2_4_report.py
─────────────────────────────────────────────────────────────────────────────
Report generator for ITSAR 1.2.4 — Password Policy Compliance.

Report FORMAT and APPEARANCE  → icaf's helpers / build_doc_with_header_footer
Report CONTENT (test data)    → your password-policy test results (raw dicts)

The raw_results list comes from  context.scan_results["password_policy"]
which is populated by Clause_1_2_4.run().
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import datetime
import subprocess

from icaf.reporting.helpers import (
    PURPLE, LIGHT_PURPLE, DARK_GREY, MID_GREY,
    TABLE_HEADER_BG, TABLE_ALT_BG, PASS_GREEN, FAIL_RED, WHITE,
    NOT_RUN_COLOR, NOT_RUN_BG,
    HEX_PURPLE, HEX_PASS_GREEN, HEX_FAIL_RED,
    ERROR_ORANGE,
    _style_cell, _para_in_cell, _set_table_width, _set_col_widths,
    section_heading, sub_heading, tc_heading,
    body_para, label_value_para, bullet_item,
    spacer, terminal_block, add_screenshot, status_result_table,
    two_col_info_table, four_col_table,
    build_doc_with_header_footer,
)
from icaf.config.settings import settings


class Clause124Report:
    """
    Generates a .docx (then PDF) compliance report for ITSAR clause 1.2.4.

    Receives:
        context  — icaf RuntimeContext  (has .ssh_ip, .dut_name, etc.)
        results  — list of icaf TestCase objects  (each has .raw_result dict)
    """

    def __init__(self, context, tc_objects: list):
        self.context    = context
        self.tc_objects = tc_objects
        # Unwrap the flat result dicts your testcases produced
        self.results: list[dict] = [
            getattr(tc, "raw_result", {}) for tc in tc_objects
        ]

    # ── Public entry point ────────────────────────────────────────────────────

    def generate(self) -> str:
        results = self.results
        ctx     = self.context
        now     = datetime.datetime.now()

        passed  = sum(1 for r in results if r.get("verdict") == "PASS")
        failed  = sum(1 for r in results if r.get("verdict") == "FAIL")
        errors  = sum(1 for r in results if r.get("verdict") == "ERROR")
        total   = len(results)
        overall = "PASS" if failed == 0 and errors == 0 else "FAIL"

        dut_name    = getattr(ctx, "dut_name",    None) or ctx.ssh_ip or "DUT"
        dut_version = getattr(ctx, "dut_version", None) or "Alpine Linux"
        start_time  = ctx.start_time.strftime("%Y-%m-%d %H:%M:%S") \
                      if hasattr(ctx, "start_time") else now.strftime("%Y-%m-%d %H:%M:%S")

        # ── Build doc with icaf header/footer ─────────────────────────────
        doc = build_doc_with_header_footer(dut_name, dut_version)

        # ── Front page ────────────────────────────────────────────────────
        self._add_front_page(doc, dut_name, dut_version, start_time,
                             now.strftime("%Y-%m-%d %H:%M:%S"), overall)

        # ── Section 1: Requirement Description ───────────────────────────
        section_heading(doc, "1. Requirement Description")
        bullet_item(doc,
            "(i) Absolute minimum password length of 8 characters — passwords "
            "shorter than 8 characters shall be rejected by the system.")
        bullet_item(doc,
            "(ii) At least 3 of the following 4 character categories must be "
            "present: uppercase letters (A-Z), lowercase letters (a-z), "
            "digits (0-9), and special characters.")
        spacer(doc, small=True)

        # ── Section 2: DUT Configuration ─────────────────────────────────
        section_heading(doc, "2. DUT Configuration")
        sub_heading(doc, "2.1 Verification of Supported Password Policy")
        body_para(doc,
            "SSH inspection was performed to identify the password policy "
            "configuration on the DUT. The following configurations were "
            "applied on the Alpine Linux DUT:")
        for b in [
            "/etc/pam.d/passwd configured with pam_cracklib.so retry=3 minlen=8 "
            "lcredit=-1 ucredit=-1 dcredit=-1 ocredit=-1",
            "/etc/security/pwquality.conf configured with minlen=8 and minclass=3",
            "Root SSH login enabled (PermitRootLogin yes) on port 22",
            "Test user 'testpwduser' created and deleted automatically by the framework",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "2.2 SSH Host Key Configuration")
        body_para(doc,
            f"The tester system connected to the DUT ({ctx.ssh_ip}) via SSH. "
            "The DUT host key was stored in the known_hosts file ensuring mutual "
            "authentication during SSH session establishment.")
        spacer(doc, small=True)

        # ── Section 3: Preconditions ──────────────────────────────────────
        section_heading(doc, "3. Preconditions")
        for b in [
            f"DUT must be running and reachable at {ctx.ssh_ip} on port 22.",
            "PAM configuration on DUT must include pam_cracklib with minlen=8.",
            "Python 3 with paramiko, python-docx, and Pillow installed on tester system.",
            "SSH access with root credentials must be available on the DUT.",
            "Network connectivity between tester and DUT verified.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 4: Test Objective ─────────────────────────────────────
        section_heading(doc, "4. Test Objective")
        body_para(doc,
            "To verify that the Device Under Test (DUT) correctly enforces the "
            "mandatory password complexity policy as prescribed in ITSAR clause 1.2.4. "
            "The test verifies that:")
        for b in [
            "Passwords shorter than 8 characters are rejected.",
            "At least 3 character categories are required.",
            "The policy is enforced at the OS level via PAM.",
            "Passwords are stored as cryptographic hashes, not plain text.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 5: Test Scenario ──────────────────────────────────────
        section_heading(doc, "5. Test Scenario")
        sub_heading(doc, "5.1 Number of Test Scenarios")
        body_para(doc, f"Total of {total} test cases were executed.")
        spacer(doc, small=True)

        two_col_info_table(doc,
            headers    =["Component", "Details"],
            col_widths =[3500, 5860],
            data_rows  =[
                ("Tester System",  f"Ubuntu Linux — {getattr(ctx, 'tester_ip', 'tester')}"),
                ("DUT",            f"Alpine Linux — {ctx.ssh_ip}"),
                ("Protocol",       "SSH Port 22"),
                ("Framework",      "ICAF — ITSAR Compliance Automation Framework"),
            ]
        )
        spacer(doc, small=True)

        sub_heading(doc, "5.2 Tools Required")
        for b in [
            "Python 3 + Paramiko — SSH automation and command execution",
            "python-docx — ITSAR-format Word report generation",
            "Pillow — Terminal screenshot rendering for evidence",
            "tmux + gnome-terminal — Visible terminal session management",
            "OpenSSH — SSH client on tester system",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "5.3 Test Execution Steps")
        for b in [
            "The tester system establishes an SSH connection to the DUT using Paramiko.",
            "Each test case executes specific commands on the DUT via SSH and captures output.",
            "PAM configuration files are inspected to verify minlen=8 and minclass=3.",
            "Password change attempts are made with various passwords to verify enforcement.",
            "The shadow file is inspected to confirm passwords are stored as cryptographic hashes.",
            "Results are recorded per test case and a Word report is generated automatically.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 6: Expected Results ───────────────────────────────────
        section_heading(doc, "6. Expected Results for Pass")
        body_para(doc,
            "The DUT shall correctly reject passwords shorter than 8 characters "
            "and passwords that do not meet the minimum character category requirement. "
            "The PAM configuration shall confirm minlen=8 and minclass=3 are enforced. "
            "Passwords shall be stored as SHA-512 cryptographic hashes (prefixed with $6$) "
            "in the shadow file with no plain text passwords found in any system file.")
        spacer(doc, small=True)

        doc.add_page_break()

        # ── Section 7: Test Execution ─────────────────────────────────────
        section_heading(doc, "7. Test Execution")

        for r in results:
            tc_id   = r.get("tc_id", "")
            tc_name = r.get("tc_name", "")
            verdict = r.get("verdict", "FAIL")
            vc = (PASS_GREEN if verdict == "PASS"
                  else FAIL_RED if verdict == "FAIL"
                  else ERROR_ORANGE)

            tc_heading(doc, f"Test Case: {tc_id}")
            label_value_para(doc, "a) Test Case Name",        tc_id)
            label_value_para(doc, "b) Test Case Description", r.get("description", tc_name))
            spacer(doc, small=True)

            body_para(doc, "c) Input Command:", bold=True)
            terminal_block(doc, [r.get("input_cmd", "(none)")])
            spacer(doc, small=True)

            label_value_para(doc, "d) Expected Result", r.get("expected", ""))
            label_value_para(doc, "e) Actual Result",
                             r.get("actual_status", verdict), value_color=vc)
            spacer(doc, small=True)

            body_para(doc, "f) Command Output:", bold=True)
            output_lines = str(r.get("output", "")).split("\n")[:40]
            terminal_block(doc, output_lines)
            spacer(doc, small=True)

            status_result_table(doc, verdict,
                                label=f"{tc_id} — {tc_name[:60]}")
            spacer(doc, small=True)

            # Screenshots
            for ef in (r.get("evidence_files") or []):
                if ef and ef.endswith(".png") and os.path.exists(ef):
                    body_para(doc, "Terminal Screenshot (Evidence):", bold=True)
                    add_screenshot(doc, ef, width_inches=5.5)

            spacer(doc)

        doc.add_page_break()

        # ── Section 8: Test Observation ───────────────────────────────────
        section_heading(doc, "8. Test Observation for Password Policy")
        if overall == "PASS":
            body_para(doc,
                "It was observed that the Device Under Test (DUT) complies with "
                "the prescribed password complexity requirements. All test cases "
                "related to minimum password length enforcement, character category "
                "requirements, PAM policy configuration, and cryptographic password "
                "storage have successfully passed.")
        else:
            failed_ids = [r["tc_id"] for r in results if r.get("verdict") != "PASS"]
            body_para(doc,
                f"It was observed that the Device Under Test (DUT) does not fully "
                f"comply with the prescribed password complexity requirements. "
                f"The failure was identified in: {', '.join(failed_ids)}. "
                f"This indicates that the DUT may permit weak passwords or insecure "
                f"password storage, weakening the overall security posture.")
        spacer(doc, small=True)

        # ── Section 9: Test Case Results Table ───────────────────────────
        section_heading(doc, "9. Test Case Result for Password Policy")
        four_col_table(doc,
            headers    =["SL. No", "TEST CASE NAME", "PASS/FAIL", "Remarks"],
            col_widths =[700, 4500, 1500, 2660],
            data_rows  =[
                (str(i + 1),
                 f"{r.get('tc_id','')} — {r.get('tc_name','')[:45]}",
                 r.get("verdict", "FAIL"),
                 r.get("actual_status", "")[:60])
                for i, r in enumerate(results)
            ]
        )
        spacer(doc)

        status_result_table(doc, overall,
                            label=f"Overall Result — {passed}/{total} passed")
        spacer(doc)

        # ── Section 10: Compliance Analysis ──────────────────────────────
        section_heading(doc, "10. Compliance Analysis")
        two_col_info_table(doc,
            headers    =["Clause Requirement", "Result"],
            col_widths =[7200, 2160],
            data_rows  =[
                ("(i) Accept password of exactly 8 characters (TC1)",
                 self._verdict("TC1")),
                ("(i) Accept password longer than 8 characters (TC2)",
                 self._verdict("TC2")),
                ("(i) Min length cannot be set below 8 (TC3)",
                 self._verdict("TC3")),
                ("OS-level PAM policy active (TC6)",
                 self._verdict("TC4")),
                ("Reject passwords shorter than minimum length (TC5)",
                 self._verdict("TC5")),
                ("Passwords stored hashed not plain text (TC6)",
                 self._verdict("TC4")),
            ]
        )
        spacer(doc)

        # ── Section 11: Conclusion ────────────────────────────────────────
        section_heading(doc, "11. Conclusion")
        if overall == "PASS":
            body_para(doc,
                f"All {total} test cases passed. The DUT correctly enforces the "
                "mandatory password complexity policy. Passwords shorter than 8 "
                "characters are rejected, at least 3 character categories are "
                "required, PAM is active with the correct configuration, and all "
                "passwords are stored as SHA-512 cryptographic hashes.")
        else:
            body_para(doc,
                f"The test run identified {failed} failing test case(s) and "
                f"{errors} error(s). The DUT does NOT fully comply with the "
                "password complexity clause. Remediation is required before "
                "the DUT can be considered compliant.")
        spacer(doc, small=True)
        body_para(doc, "Recommendations:", bold=True)
        for b in [
            "Ensure pam_cracklib or pam_pwquality is installed and active on the DUT.",
            "Set minlen=8 and minclass=3 in /etc/security/pwquality.conf.",
            "Validate PAM stack in /etc/pam.d/passwd includes the pwquality/cracklib module.",
            "Confirm /etc/shadow stores passwords with $6$ (SHA-512) prefix.",
            "Re-run this test suite after any configuration change to verify compliance.",
        ]:
            bullet_item(doc, b)

        # ── Save docx → PDF ───────────────────────────────────────────────
        ts        = now.strftime("%Y%m%d_%H%M%S")
        report_dir = str(settings.REPORT_DIR)
        os.makedirs(report_dir, exist_ok=True)
        docx_path = os.path.join(report_dir, f"clause_1_2_4_report_{ts}.docx")
        doc.save(docx_path)

        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             docx_path, "--outdir", report_dir],
            capture_output=True, text=True
        )
        pdf_path = docx_path.replace(".docx", ".pdf")
        if os.path.exists(pdf_path):
            os.remove(docx_path)
            return pdf_path
        return docx_path

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _verdict(self, tc_id: str) -> str:
        return next(
            (r.get("verdict", "N/A") for r in self.results if r.get("tc_id") == tc_id),
            "N/A",
        )

    def _add_front_page(self, doc, dut_name, dut_version,
                        start_time, end_time, overall):
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from icaf.reporting.helpers import (
            PURPLE, MID_GREY, HEX_PURPLE, WHITE,
            spacer, four_col_table, two_col_info_table,
            _add_para_border_bottom,
        )

        spacer(doc, large=True)
        spacer(doc, large=True)

        def _centered(text, size_pt, color, bold=False):
            p   = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text)
            run.bold = bold
            run.font.size = Pt(size_pt)
            run.font.name = "Arial"
            run.font.color.rgb = color
            return p

        p = _centered("Password Policy Compliance Test Report", 22, PURPLE, bold=True)
        _add_para_border_bottom(p, HEX_PURPLE, size=12)
        _centered("ITSAR Clause 1.2.4 — Password Complexity", 13, MID_GREY)
        spacer(doc, large=True)

        four_col_table(doc,
            headers   =["Document No.", "Created By", "Reviewed By", "Approved By"],
            data_rows =[("1", "ICAF Framework", "Reviewer", "Approver")],
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
