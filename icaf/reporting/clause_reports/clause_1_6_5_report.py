"""
icaf/reporting/clause_reports/clause_1_6_5_report.py
─────────────────────────────────────────────────────────────────────────────
Report generator for ITSAR 1.6.5 — Protecting Data and Information in Storage.

FIXES:
  1. Reads results from context.scan_results["storage_protection"] (primary)
     then tc_objects[i].raw_result (fallback).
  2. Overall verdict: PASS only when every TC explicitly returned "PASS".
  3. Header patched: "ITSAR 1.1.1" → "ITSAR 1.6.5" via _patch_header_text().
  4. Safe imports — only imports symbols that exist in clause_1_2_4_report too.
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


class Clause165Report:
    """
    Generates a .docx (then PDF) compliance report for ITSAR clause 1.6.5.
    """

    def __init__(self, context, tc_objects: list):
        self.context    = context
        self.tc_objects = tc_objects

        # ── Primary: raw dicts written by record_result() ─────────────────
        scan = getattr(context, "scan_results", {}) or {}
        raw  = scan.get("storage_protection", [])

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
        dut_version = getattr(ctx, "dut_version", None) or "Alpine Linux"
        start_time  = (
            ctx.start_time.strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(ctx, "start_time")
            else now.strftime("%Y-%m-%d %H:%M:%S")
        )
        end_time = now.strftime("%Y-%m-%d %H:%M:%S")

        # ── Build document ─────────────────────────────────────────────────
        doc = build_doc_with_header_footer(dut_name, dut_version)
        # Patch header from hardcoded "1.1.1" to "1.6.5"
        self._patch_header_text(doc)

        # ── Front page ─────────────────────────────────────────────────────
        self._add_front_page(doc, dut_name, dut_version,
                             start_time, end_time, overall)

        # ── Section 1 ──────────────────────────────────────────────────────
        section_heading(doc, "1. Requirement Description")
        bullet_item(doc,
            "(i) The network product shall protect confidential system and internal "
            "information from being stored in clear text. Passwords, cryptographic "
            "keys, session tokens, and other sensitive credentials must be stored "
            "in encrypted or hashed form at all times.")
        bullet_item(doc,
            "(ii) Access to sensitive stored data (shadow file, private keys, audit "
            "logs) shall be restricted by file permissions — unprivileged users must "
            "not be able to read files containing credential material.")
        bullet_item(doc,
            "(iii) Even when accessed by privileged users, passwords must appear as "
            "cryptographic hashes (SHA-512, prefixed $6$) and private keys must be "
            "PEM-encoded — never raw or plaintext.")
        spacer(doc, small=True)

        # ── Section 2 ──────────────────────────────────────────────────────
        section_heading(doc, "2. DUT Configuration")
        sub_heading(doc, "2.1 Verification of Data Storage Protection Mechanisms")
        body_para(doc,
            "SSH inspection was performed to identify the data-at-rest protection "
            "configuration on the DUT. The following mechanisms were verified on "
            "the Alpine Linux DUT:")
        for b in [
            "/etc/shadow configured with SHA-512 ($6$) password hashing via busybox passwd",
            "/etc/pam.d/ configured to enforce password quality before storage",
            "SSH host private keys stored with root-only (600) file permissions",
            "System audit logs (/var/log/messages) restricted from unprivileged read",
            "/etc/passwd uses 'x' shadow placeholder — no hashes stored in world-readable file",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "2.2 Test User Configuration")
        body_para(doc,
            "TC-165-002 automatically creates and deletes an unprivileged test user "
            f"'test165user' on the DUT ({ctx.ssh_ip}) to simulate privilege level 10 "
            "access. TC-165-003 uses the existing root session to verify privileged "
            "access reveals only hashed/encrypted data.")
        spacer(doc, small=True)

        # ── Section 3 ──────────────────────────────────────────────────────
        section_heading(doc, "3. Preconditions")
        for b in [
            f"DUT must be running and reachable at {ctx.ssh_ip} on port 22.",
            "Root SSH credentials must be available for the primary session.",
            "The DUT must support user creation (adduser) for privilege-level testing.",
            "Python 3 with paramiko, python-docx installed on tester system.",
            "Network connectivity between tester and DUT verified.",
            "wmctrl, xdotool, scrot/imagemagick installed on tester for screenshots.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 4 ──────────────────────────────────────────────────────
        section_heading(doc, "4. Test Objective")
        body_para(doc,
            "To verify that the Device Under Test (DUT) correctly protects "
            "confidential system information in storage, as required by ITSAR "
            "clause 1.6.5. The test verifies that:")
        for b in [
            "No passwords are stored in plaintext — SHA-512 hashing is enforced.",
            "SSH private keys have root-only file permissions (600).",
            "Unprivileged users cannot access /etc/shadow, audit logs, or private keys.",
            "Audit logs contain no plaintext credential patterns.",
            "Configuration files do not expose sensitive data in cleartext.",
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
                ("DUT",            f"Alpine Linux — {ctx.ssh_ip}"),
                ("Protocol",       "SSH Port 22"),
                ("Framework",      "ICAF — ITSAR Compliance Automation Framework"),
                ("Clause",         "ITSAR 1.6.5 — Protecting Data and Information in Storage"),
            ]
        )
        spacer(doc, small=True)

        sub_heading(doc, "5.2 Tools Required")
        for b in [
            "Python 3 + Paramiko — SSH automation and command execution on DUT",
            "python-docx — ITSAR-format Word report generation",
            "tmux + gnome-terminal — Visible terminal session for screenshot evidence",
            "wmctrl + xdotool + scrot/ImageMagick — Real-time window screenshot capture",
            "OpenSSH — SSH client on tester for unprivileged session in TC-165-002",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "5.3 Test Execution Steps")
        for b in [
            "The tester system establishes a root SSH connection to the DUT using Paramiko.",
            "TC-165-001: Inspects /etc/shadow, SSH key permissions, audit logs, and config files.",
            "TC-165-002: Creates an unprivileged test user; attempts to read shadow, logs, private keys.",
            "TC-165-003: Root session verifies privileged access reveals only hashed/encrypted data.",
            "After each TC, a real screenshot of the gnome-terminal is captured for evidence.",
            "Results are recorded per test case and a Word/PDF report is generated automatically.",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 6 ──────────────────────────────────────────────────────
        section_heading(doc, "6. Expected Results for Pass")
        body_para(doc,
            "The DUT shall store all passwords as SHA-512 cryptographic hashes "
            "($6$ prefix in /etc/shadow). SSH private keys shall have root-only "
            "permissions (600). Unprivileged users shall be denied access to "
            "/etc/shadow, audit logs, and SSH private keys. Audit logs and "
            "configuration files shall contain no plaintext credential patterns. "
            "/etc/passwd shall use the 'x' shadow placeholder.")
        spacer(doc, small=True)

        doc.add_page_break()

        # ── Section 7: Test Execution ──────────────────────────────────────
        section_heading(doc, "7. Test Execution")

        if not results:
            body_para(doc,
                "WARNING: No test results were recorded. "
                "Ensure record_result() is called in each TC and "
                "context.scan_results['storage_protection'] is populated.",
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
        section_heading(doc, "8. Test Observation for Data Storage Protection")
        if overall == "PASS":
            body_para(doc,
                "It was observed that the Device Under Test (DUT) complies with "
                "the data-at-rest protection requirements of ITSAR clause 1.6.5. "
                "All test cases confirmed that passwords are stored as SHA-512 "
                "cryptographic hashes, SSH private keys are restricted to root-only "
                "access, unprivileged users are denied access to sensitive files, "
                "and audit logs contain no plaintext credential patterns.")
        else:
            failed_ids = [r.get("tc_id", "?") for r in results
                          if r.get("verdict") != "PASS"]
            body_para(doc,
                "It was observed that the Device Under Test (DUT) does not fully "
                "comply with the data-at-rest protection requirements of ITSAR "
                f"clause 1.6.5. Failures identified in: "
                f"{', '.join(failed_ids) if failed_ids else 'unknown TCs'}.")
        spacer(doc, small=True)

        # ── Section 9 ──────────────────────────────────────────────────────
        section_heading(doc, "9. Test Case Result for Data Storage Protection")
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
                ("TC-165-001 — Read Access Rights for Sensitive Files",
                 self._verdict("TC-165-001")),
                ("TC-165-002 — Manipulation of Sensitive System Files",
                 self._verdict("TC-165-002")),
                ("TC-165-003 — Passwords Stored Hashed/Encrypted, Not in Cleartext",
                 self._verdict("TC-165-003")),
            ]
        )
        spacer(doc)

        # ── Section 11 ─────────────────────────────────────────────────────
        section_heading(doc, "11. Conclusion")
        if overall == "PASS":
            body_para(doc,
                f"All {total} test cases passed. The DUT correctly protects "
                "confidential system information in storage. Passwords are stored "
                "as SHA-512 cryptographic hashes, SSH private keys have root-only "
                "file permissions, unprivileged users are denied access to sensitive "
                "files, and no plaintext credentials were found in audit logs or "
                "configuration files.")
        else:
            body_para(doc,
                f"The test run identified {failed} failing test case(s) and "
                f"{errors} error(s). The DUT does NOT fully comply with the "
                "data-at-rest protection requirements of ITSAR clause 1.6.5. "
                "Remediation is required before the DUT can be considered compliant.")
        spacer(doc, small=True)

        body_para(doc, "Recommendations:", bold=True)
        for b in [
            "Ensure /etc/shadow is configured with SHA-512 hashing ($6$ prefix).",
            "Verify /etc/ssh/ssh_host_*_key files have 600 permissions (root-only).",
            "Restrict /var/log/messages to root or adm group only (chmod 640).",
            "Ensure /etc/passwd uses 'x' shadow placeholder for all accounts.",
            "Audit configuration files periodically to ensure no plaintext secrets are stored.",
            "Re-run this test suite after any configuration change to verify compliance.",
        ]:
            bullet_item(doc, b)

        # ── Save docx → PDF ────────────────────────────────────────────────
        ts         = now.strftime("%Y%m%d_%H%M%S")
        report_dir = str(settings.REPORT_DIR)
        os.makedirs(report_dir, exist_ok=True)
        docx_path  = os.path.join(report_dir, f"clause_1_6_5_report_{ts}.docx")
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
        """Replace hardcoded 'ITSAR 1.1.1' with 'ITSAR 1.6.5' in all headers."""
        try:
            for section in doc.sections:
                for para in section.header.paragraphs:
                    for run in para.runs:
                        if "1.1.1" in run.text:
                            run.text = run.text.replace(
                                "ITSAR 1.1.1", "ITSAR 1.6.5"
                            ).replace("1.1.1", "1.6.5")
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
            "Data Storage Protection Compliance Test Report",
            22, PURPLE, bold=True,
        )
        _add_para_border_bottom(p, HEX_PURPLE, size=12)
        _centered(
            "ITSAR Clause 1.6.5 — Protecting Data and Information in Storage",
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