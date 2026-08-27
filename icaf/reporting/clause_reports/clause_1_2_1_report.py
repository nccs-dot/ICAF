"""
icaf/reporting/clause_reports/clause_1_2_1_report.py
─────────────────────────────────────────────────────────────────────────────
Report generator for ITSAR 1.2.1 — User Authentication Compliance.

Report FORMAT and APPEARANCE  → icaf's helpers / build_doc_with_header_footer
Report CONTENT (test data)    → user authentication test results (raw dicts)

The raw_results list comes from  context.scan_results["user_authentication"]
which is populated by Clause_1_2_1.run().

Test Coverage:
    TC1-TC3:   Console Authentication (local access)
    TC4-TC6:   SSH Authentication (remote CLI)
    TC7-TC9:   SFTP Authentication (file transfer)
    TC10-TC12: SCP Authentication (secure copy)
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


class Clause121Report:
    """
    Generates a .docx (then PDF) compliance report for ITSAR clause 1.2.1.

    Receives:
        context  — icaf RuntimeContext  (has .ssh_ip, .dut_name, etc.)
        tc_objects  — list of icaf TestCase objects  (each has .raw_result dict)
    """

    def __init__(self, context, tc_objects: list):
        self.context    = context
        self.tc_objects = tc_objects
        # Unwrap flat result dicts produced by the clause test cases
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
        overall = "PASS" if total > 0 and failed == 0 and errors == 0 else "FAIL"

        dut_name    = getattr(ctx, "dut_name",    None) or ctx.ssh_ip or "DUT"
        dut_version = getattr(ctx, "dut_version", None) or "Alpine Linux / Router OS"
        start_time  = ctx.start_time.strftime("%Y-%m-%d %H:%M:%S") \
                      if hasattr(ctx, "start_time") else now.strftime("%Y-%m-%d %H:%M:%S")

        # ── Build doc with icaf header/footer ─────────────────────────────
        doc = build_doc_with_header_footer(dut_name, dut_version)
        self._set_clause_header(doc)

        # ── Front page ────────────────────────────────────────────────────
        self._add_front_page(doc, dut_name, dut_version, start_time,
                             now.strftime("%Y-%m-%d %H:%M:%S"), overall)

        # ── Section 1: Requirement Description ───────────────────────────
        section_heading(doc, "1. Requirement Description")
        bullet_item(doc,
            "(i) The DUT shall enforce mandatory user authentication for all access methods "
            "and management interfaces, including local console access, remote SSH connections, and secure file transfer protocols.")
        bullet_item(doc,
            "(ii) Authentication shall be required with at least one authentication attribute "
            "(username/password, certificate, multi-factor authentication, etc.) for:")
        for b in [
            "Local console login access (direct serial or terminal connection)",
            "Remote SSH CLI access (Secure Shell Protocol on TCP Port 22)",
            "SFTP file transfer access (SSH File Transfer Protocol)",
            "SCP secure copy access (Secure Copy Protocol)",
        ]:
            bullet_item(doc, "    • " + b)
        
        bullet_item(doc,
            "(iii) The DUT must reject unauthenticated connection attempts and enforce credential validation "
            "on all exposed management protocols without bypassing or weakening authentication requirements.")
        bullet_item(doc,
            "(iv) Access control and authentication must be enforced at the network protocol layer "
            "for remote management channels and at the system level for local access methods.")
        spacer(doc, small=True)

        # ── Section 2: DUT Configuration ─────────────────────────────────
        section_heading(doc, "2. DUT Configuration")
        sub_heading(doc, "2.1 Management Interface Configuration")
        body_para(doc,
            "The Device Under Test is configured with the following management and access interfaces:")
        for b in [
            f"DUT hostname/IP: {ctx.ssh_ip} (network reachable via administrative channels)",
            "Local Console Access: Serial/Terminal login capability enabled",
            "SSH Remote Management: SSH daemon (sshd) listening on TCP port 22 with user authentication",
            "SFTP Support: Enabled via SSH subsystem (sftp-server) for authenticated file operations",
            "SCP Support: Enabled via SSH protocol for secure file transfer between systems",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "2.2 Authentication Mechanism")
        body_para(doc,
            "The DUT implements username/password-based authentication as the primary "
            "authentication attribute across all access channels. The authentication subsystem enforces:")
        for b in [
            "Mandatory credential entry before granting any system access",
            "Centralized authentication validation (PAM — Pluggable Authentication Modules on Linux)",
            "Consistent credential requirements across all protocol implementations (console, SSH, SFTP, SCP)",
            "Rejection of empty/null credentials and unauthenticated sessions",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 3: Preconditions ──────────────────────────────────────
        section_heading(doc, "3. Preconditions")
        for b in [
            f"DUT is operational and network reachable at {ctx.ssh_ip} via SSH",
            "SSH daemon (sshd) is running and accepting connections on port 22",
            "SFTP and SCP protocol support is enabled and functional",
            "Local console interface is accessible (either directly or via SSH emulation)",
            "Test user account(s) are created on the DUT for authentication validation",
            "ICAF test harness has provisioned test credentials for authentication testing",
            "tmux session and gnome-terminal are available for visual test tracking",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 4: Test Objective ─────────────────────────────────────
        section_heading(doc, "4. Test Objective")
        body_para(doc,
            "To verify that the Device Under Test enforces mandatory user authentication across "
            "all access methods and rejects unauthenticated or incorrectly authenticated sessions. The test validates:")
        for b in [
            "Console login requires valid authentication; connections without credentials are rejected",
            "SSH remote access enforces authentication; unauthenticated connections are denied",
            "SFTP file transfer requires valid credentials; unauthorized access is blocked",
            "SCP secure copy enforces authentication; invalid credentials result in connection rejection",
            "Correct credentials are accepted uniformly across all protocols",
            "Incorrect credentials are consistently rejected, preventing unauthorized access",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        # ── Section 5: Test Scenario ──––––––––––––––––––––––––––––––––––––
        section_heading(doc, "5. Test Scenario")
        sub_heading(doc, "5.1 Number of Test Scenarios")
        body_para(doc,
            f"Total of {total} test scenario(s) executed under Clause 1.2.1. "
            "Each protocol (Console, SSH, SFTP, SCP) is tested with three authentication scenarios: "
            "no credentials, correct credentials, and incorrect credentials.")
        spacer(doc, small=True)

        two_col_info_table(doc,
            headers    =["Component", "Details"],
            col_widths =[3500, 5860],
            data_rows  =[
                ("Tester System",  f"Ubuntu Linux / ICAF Engine — {getattr(ctx, 'tester_ip', '127.0.0.1')}"),
                ("DUT",            f"{dut_name} ({dut_version}) — {ctx.ssh_ip}"),
                ("Test Type",      "User Authentication Enforcement — Multi-Protocol"),
                ("Framework",      "ICAF — ITSAR Compliance Automation Framework"),
                ("Test User",      "testuser (created during test setup)"),
            ]
        )
        spacer(doc, small=True)

        sub_heading(doc, "5.2 Tools & Technology")
        for b in [
            "Python 3 + Paramiko — SSH/SFTP/SCP client library and authentication validation",
            "gnome-terminal + tmux — Real-time visual test execution tracking and command echoing",
            "OpenSSH (ssh, sshd) — Standard SSH protocol implementation on DUT",
            "Test User Management (adduser/deluser) — Dynamic test account lifecycle",
            "Python-docx — ITSAR compliant report generation",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "5.3 Test Execution Steps")
        for b in [
            "Establish authenticated SSH session to DUT (baseline connectivity verification)",
            "Create temporary test user account with known credentials",
            "Execute TC1-TC3: Validate Console authentication enforcement and credential validation",
            "Execute TC4-TC6: Validate SSH authentication enforcement and credential validation",
            "Execute TC7-TC9: Validate SFTP authentication enforcement and credential validation",
            "Execute TC10-TC12: Validate SCP authentication enforcement and credential validation",
            "Capture output, command echoes, and evidence for each test case",
            "Clean up temporary test user account from DUT",
            "Compile results into ITSAR-compliant compliance report",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        sub_heading(doc, "5.4 Test Cases Overview")
        test_cases_data = [
            ("TC1", "Console - No Authentication", "Verify console requires credentials; reject unauthenticated access"),
            ("TC2", "Console - Correct Authentication", "Verify console accepts correct username and password"),
            ("TC3", "Console - Incorrect Authentication", "Verify console rejects incorrect password"),
            ("TC4", "SSH - No Authentication", "Verify SSH requires credentials; reject unauthenticated connections"),
            ("TC5", "SSH - Correct Authentication", "Verify SSH accepts correct username and password"),
            ("TC6", "SSH - Incorrect Authentication", "Verify SSH rejects incorrect password"),
            ("TC7", "SFTP - No Authentication", "Verify SFTP requires credentials; reject unauthenticated access"),
            ("TC8", "SFTP - Correct Authentication", "Verify SFTP accepts correct username and password"),
            ("TC9", "SFTP - Incorrect Authentication", "Verify SFTP rejects incorrect password"),
            ("TC10", "SCP - No Authentication", "Verify SCP requires credentials; reject unauthenticated access"),
            ("TC11", "SCP - Correct Authentication", "Verify SCP accepts correct username and password"),
            ("TC12", "SCP - Incorrect Authentication", "Verify SCP rejects incorrect password"),
        ]
        four_col_table(doc,
            headers    =["TC ID", "Test Case Name", "Objective", "Expected Result"],
            col_widths =[900, 2000, 2500, 2060],
            data_rows  =[(tc, name, obj, "Pass/Fail") for tc, name, obj in test_cases_data]
        )
        spacer(doc, small=True)

        # ── Section 6: Expected Results ───────────────────────────────────
        section_heading(doc, "6. Expected Results for Pass")
        body_para(doc,
            "All 12 test cases shall result in PASS verdict. Specifically:")
        for b in [
            "Console login attempts without credentials or with incorrect passwords are REJECTED",
            "Console login with correct credentials is ACCEPTED",
            "SSH connection attempts without credentials or with incorrect passwords are REJECTED",
            "SSH connection with correct credentials is ACCEPTED and remote command execution succeeds",
            "SFTP connection attempts without credentials or with incorrect passwords are REJECTED",
            "SFTP connection with correct credentials is ACCEPTED and file operations succeed",
            "SCP connection attempts without credentials or with incorrect passwords are REJECTED",
            "SCP connection with correct credentials is ACCEPTED and secure copy operations succeed",
        ]:
            bullet_item(doc, b)
        spacer(doc, small=True)

        doc.add_page_break()

        # ── Section 7: Test Execution ─────────────────────────────────────
        section_heading(doc, "7. Test Execution")

        # Group results by protocol for better readability
        protocol_groups = {
            "Console": [],
            "SSH": [],
            "SFTP": [],
            "SCP": [],
        }
        
        for r in results:
            tc_id = r.get("tc_id", "TC1")
            if "TC1" in tc_id or "TC2" in tc_id or "TC3" in tc_id:
                protocol_groups["Console"].append(r)
            elif "TC4" in tc_id or "TC5" in tc_id or "TC6" in tc_id:
                protocol_groups["SSH"].append(r)
            elif "TC7" in tc_id or "TC8" in tc_id or "TC9" in tc_id:
                protocol_groups["SFTP"].append(r)
            elif "TC10" in tc_id or "TC11" in tc_id or "TC12" in tc_id:
                protocol_groups["SCP"].append(r)

        for protocol, proto_results in protocol_groups.items():
            if not proto_results:
                continue
            
            sub_heading(doc, f"7.{list(protocol_groups.keys()).index(protocol) + 1} {protocol} Authentication Tests")
            spacer(doc, small=True)

            for r in proto_results:
                tc_id   = r.get("tc_id", "TC")
                tc_name = r.get("tc_name", "Authentication Test")
                verdict = r.get("verdict", "FAIL")
                vc = (PASS_GREEN if verdict == "PASS"
                      else FAIL_RED if verdict == "FAIL"
                      else ERROR_ORANGE)

                tc_heading(doc, f"Test Case: {tc_id}")
                label_value_para(doc, "a) Test Case Name",        tc_name)
                label_value_para(doc, "b) Test Case Description", r.get("description", tc_name))
                spacer(doc, small=True)

                body_para(doc, "c) Test Command / Authentication Method:", bold=True)
                terminal_block(doc, [r.get("input_cmd", "(none)")])
                spacer(doc, small=True)

                label_value_para(doc, "d) Expected Result", r.get("expected", "Authentication enforcement"))
                label_value_para(doc, "e) Actual Result",
                                 r.get("actual_status", verdict), value_color=vc)
                spacer(doc, small=True)

                body_para(doc, "f) Test Output & Verification:", bold=True)
                output_lines = str(r.get("output", "")).split("\n")[:30]
                terminal_block(doc, output_lines)
                spacer(doc, small=True)

                status_result_table(doc, verdict,
                                    label=f"{tc_id} — {tc_name[:60]}")
                spacer(doc, small=True)

                # Screenshots & Evidence Files
                for ef in (r.get("evidence_files") or []):
                    if ef and ef.lower().endswith(".png") and os.path.exists(ef):
                        body_para(doc, "Terminal Screenshot (Evidence):", bold=True)
                        add_screenshot(doc, ef, width_inches=5.5)

                spacer(doc)

        doc.add_page_break()

        # ── Section 8: Test Observation ───────────────────────────────────
        section_heading(doc, "8. Test Observation for User Authentication")
        if overall == "PASS":
            body_para(doc,
                "It was observed that the Device Under Test (DUT) successfully enforces mandatory user authentication "
                "across all access methods tested. The DUT consistently rejected unauthenticated connection attempts, "
                "accepted valid credentials uniformly across Console, SSH, SFTP, and SCP protocols, and properly denied "
                "access when incorrect credentials were presented. The authentication mechanism is functioning as designed "
                "and complies with ITSAR Clause 1.2.1 requirements.")
        else:
            failed_ids = [r.get("tc_id", "TC") for r in results if r.get("verdict") != "PASS"]
            body_para(doc,
                f"It was observed that the Device Under Test (DUT) does not fully comply with user authentication "
                f"requirements under ITSAR Clause 1.2.1. One or more test cases failed: {', '.join(failed_ids)}. "
                f"Defects identified include: authentication enforcement gaps, inconsistent credential validation across protocols, "
                f"or acceptance of invalid/missing credentials. These findings represent a critical security weakness "
                f"requiring immediate remediation.")
        spacer(doc, small=True)

        # ── Section 9: Test Case Results Table ───────────────────────────
        section_heading(doc, "9. Test Case Results Summary")
        four_col_table(doc,
            headers    =["SL. No", "TEST CASE NAME", "PASS/FAIL", "Protocol"],
            col_widths =[700, 3500, 1200, 2260],
            data_rows  =[
                (str(i + 1),
                 f"{r.get('tc_id','')} — {r.get('tc_name','')[:40]}",
                 r.get("verdict", "FAIL"),
                 self._extract_protocol(r.get('tc_name', '')))
                for i, r in enumerate(results)
            ]
        )
        spacer(doc)

        status_result_table(doc, overall,
                            label=f"Overall Authentication Compliance: {passed}/{total} passed")
        spacer(doc)

        # ── Section 10: Compliance Analysis ──────────────────────────────
        section_heading(doc, "10. Compliance Analysis")
        two_col_info_table(doc,
            headers    =["Clause Requirement", "Compliance Status"],
            col_widths =[7200, 2160],
            data_rows  =[
                ("Console access enforces mandatory authentication",
                 self._protocol_verdict("Console")),
                ("SSH remote access enforces mandatory authentication",
                 self._protocol_verdict("SSH")),
                ("SFTP file transfer enforces mandatory authentication",
                 self._protocol_verdict("SFTP")),
                ("SCP secure copy enforces mandatory authentication",
                 self._protocol_verdict("SCP")),
                ("Correct credentials accepted uniformly across all protocols",
                 self._correct_auth_verdict()),
                ("Incorrect credentials rejected uniformly across all protocols",
                 self._incorrect_auth_verdict()),
                ("Overall authentication mechanism compliance",
                 overall),
            ]
        )
        spacer(doc)

        # ── Section 11: Conclusion ────────────────────────────────────────
        section_heading(doc, "11. Conclusion")
        if overall == "PASS":
            body_para(doc,
                f"All {total} test case(s) passed successfully. The Device Under Test satisfies "
                "ITSAR Clause 1.2.1 User Authentication requirements. Authentication is properly enforced "
                "across all access methods (Console, SSH, SFTP, SCP), with consistent credential validation "
                "and rejection of unauthorized access attempts.")
        else:
            body_para(doc,
                f"The test execution identified {failed} failing test case(s) and {errors} error(s). "
                "The DUT does NOT currently comply with Clause 1.2.1 user authentication requirements. "
                "Authentication enforcement gaps were identified across one or more access protocols. "
                "Remediation is required before the product can achieve certification.")
        spacer(doc, small=True)

        body_para(doc, "Remediation Actions (if required):", bold=True)
        for b in [
            "Enable and enforce PAM (Pluggable Authentication Modules) across all access methods",
            "Verify SSH daemon configuration enforces key-based or password authentication",
            "Enable SFTP subsystem and ensure it uses the same authentication backend as SSH",
            "Validate console login prompt displays and requires credentials before shell access",
            "Test authentication across all protocols to ensure consistent enforcement",
            "Document authentication policy and ensure it meets organizational security standards",
            "Re-run Clause 1.2.1 test suite after remediation to verify compliance closure",
        ]:
            bullet_item(doc, b)
        
        spacer(doc, small=True)
        body_para(doc, "This test validates a critical security control. "
                       "All authentication bypass vulnerabilities must be resolved before deployment.",
                       italic=True)

        # ── Save docx → PDF ───────────────────────────────────────────────
        ts         = now.strftime("%Y%m%d_%H%M%S")
        report_dir = str(settings.REPORT_DIR)
        os.makedirs(report_dir, exist_ok=True)
        docx_path  = os.path.join(report_dir, f"clause_1_2_1_report_{ts}.docx")
        doc.save(docx_path)

        subprocess.run(
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

    def _first_verdict(self) -> str:
        if not self.results:
            return "N/A"
        return self.results[0].get("verdict", "N/A")

    def _protocol_verdict(self, protocol: str) -> str:
        """Get verdict for a specific protocol's test cases."""
        proto_results = [r for r in self.results 
                        if protocol.lower() in r.get('tc_name', '').lower()]
        if not proto_results:
            return "N/A"
        all_pass = all(r.get("verdict") == "PASS" for r in proto_results)
        return "PASS" if all_pass else "FAIL"

    def _correct_auth_verdict(self) -> str:
        """Get verdict for correct authentication test cases (TC2, TC5, TC8, TC11)."""
        correct_tcs = [r for r in self.results 
                      if any(tc_id in r.get('tc_id', '') for tc_id in ['TC2', 'TC5', 'TC8', 'TC11'])]
        if not correct_tcs:
            return "N/A"
        all_pass = all(r.get("verdict") == "PASS" for r in correct_tcs)
        return "PASS" if all_pass else "FAIL"

    def _incorrect_auth_verdict(self) -> str:
        """Get verdict for incorrect authentication test cases (TC3, TC6, TC9, TC12)."""
        incorrect_tcs = [r for r in self.results 
                        if any(tc_id in r.get('tc_id', '') for tc_id in ['TC3', 'TC6', 'TC9', 'TC12'])]
        if not incorrect_tcs:
            return "N/A"
        all_pass = all(r.get("verdict") == "PASS" for r in incorrect_tcs)
        return "PASS" if all_pass else "FAIL"

    def _extract_protocol(self, tc_name: str) -> str:
        """Extract protocol name from test case name."""
        if "Console" in tc_name:
            return "Console"
        elif "SSH" in tc_name:
            return "SSH"
        elif "SFTP" in tc_name:
            return "SFTP"
        elif "SCP" in tc_name:
            return "SCP"
        return "Unknown"

    @staticmethod
    def _set_clause_header(doc) -> None:
        """Update header to reflect clause 1.2.1."""
        try:
            for paragraph in doc.sections[0].header.paragraphs:
                for run in paragraph.runs:
                    if "1.1.1" in run.text or "1.2.4" in run.text or "1.9.3" in run.text:
                        run.text = run.text.replace("1.1.1", "1.2.1").replace("1.2.4", "1.2.1").replace("1.9.3", "1.2.1")
        except Exception:
            pass

    def _add_front_page(self, doc, dut_name, dut_version,
                        start_time, end_time, overall):
        """Add front page with compliance summary."""
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from icaf.reporting.helpers import (
            PURPLE, MID_GREY, HEX_PURPLE,
            spacer, four_col_table, two_col_info_table,
            _add_para_border_bottom,
        )

        spacer(doc, large=True)
        spacer(doc, large=True)

        def _centered(text, size_pt, color, bold=False):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text)
            run.bold = bold
            run.font.size = Pt(size_pt)
            run.font.name = "Arial"
            run.font.color.rgb = color
            return p

        p = _centered("User Authentication Test Report", 22, PURPLE, bold=True)
        _add_para_border_bottom(p, HEX_PURPLE, size=12)
        _centered("ITSAR Clause 1.2.1 — Authentication Enforcement & Validation", 13, MID_GREY)
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
                ("DUT Host / Target IP",    getattr(self.context, "ssh_ip", "N/A")),
                ("DUT Software Version",    dut_version),
                ("Test Type",               "Multi-Protocol Authentication Enforcement"),
                ("Test Protocols",          "Console, SSH, SFTP, SCP (12 test cases)"),
                ("Test Start",              start_time),
                ("Test End",                end_time),
                ("Requirement Test Result", overall),
            ]
        )
        doc.add_page_break()