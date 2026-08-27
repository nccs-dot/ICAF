"""
icaf/clauses/clause_1_2_1/clause.py

Clause 1.2.1: User Authentication

ONE SSH connection via paramiko (opened first).
The tmux terminal types commands visually but does NOT open its own SSH —
it just echoes what paramiko sends so the tester can see activity.
scrot takes a real screenshot of that tmux window for the report.

Test Objective:
    Verify authentication enforcement and credential validation across multiple
    protocols and access methods:
    - Console login (local access)
    - SSH CLI access
    - SFTP file transfer
    - SCP secure copy
    
Test Coverage: 12 Test Cases (TC1-TC12)
    TC1-3:   Console authentication (no auth, correct, incorrect)
    TC4-6:   SSH authentication (no auth, correct, incorrect)
    TC7-9:   SFTP authentication (no auth, correct, incorrect)
    TC10-12: SCP authentication (no auth, correct, incorrect)

Expected Results:
    - Authentication must be mandatory (cannot bypass with no credentials)
    - Correct credentials must be accepted on all protocols
    - Incorrect credentials must be rejected on all protocols
"""

import subprocess
import time
import os
import datetime

from icaf.core.clause import BaseClause
from icaf.core.testcase import TestCase
from icaf.core.result_recorder import clear_results, get_results, set_terminal_manager
from icaf.core.step_runner import StepRunner
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger

from icaf.clauses.clause_1_2_1.testcases.tc_1_2_1_auth import run as run_auth_tests

try:
    from icaf.core.terminal_renderer import terminal_renderer
    HAS_TERMINAL_RENDERER = True
except ImportError:
    HAS_TERMINAL_RENDERER = False
    terminal_renderer = None

_TC_MANIFEST = [
    (run_auth_tests, "TC1-TC12", "User Authentication - All Protocols",
     "Verify authentication enforcement on Console, SSH, SFTP, and SCP"),
]

TMUX_NAME = "ICAF-DUT"
TERMINAL  = "dut"
_LIVE_PATH = "/tmp/icaf_live_terminal.png"  # Live window screenshot path


def _tmux(keys, enter=True):
    """Send keys to tmux terminal."""
    cmd = ["tmux", "send-keys", "-t", TMUX_NAME, keys]
    if enter:
        cmd.append("Enter")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Clause_1_2_1(BaseClause):
    """
    Clause 1.2.1: User Authentication
    
    Ensures all access methods (Console, SSH, SFTP, SCP) enforce
    mandatory authentication with valid credential validation.
    """

    name = "1.2.1 User Authentication"

    def __init__(self, context):
        super().__init__(context)
        self._ssh = None

    def run(self) -> list[TestCase]:
        """Execute user authentication compliance tests."""
        clear_results()

        tm = getattr(self.context, "terminal_manager", None)
        if tm is not None:
            set_terminal_manager(tm)

        # ── Step 1: open ONE paramiko SSH session ─────────────────────────
        self._ssh = self._make_ssh_session()

        # ── Step 2: open gnome-terminal showing a local prompt ────────────
        # The terminal does NOT ssh into the DUT itself — it just shows
        # the commands we type into it via tmux send-keys
        self._open_terminal()

        # ── Step 3: patch ssh.run to also type visually ───────────────────
        self._patch_visual()

        # ── Run test suite ────────────────────────────────────────────────
        for runner_fn, tc_id, tc_name, _desc in _TC_MANIFEST:
            logger.info(f"[1.2.1] Running {tc_id}")
            _tmux(f"echo '=== {tc_id}: {tc_name} ==='")
            time.sleep(0.3)

            tc_obj = TestCase(name=tc_id, description=tc_name)
            self.context.current_testcase = tc_obj

            try:
                runner_fn(self._ssh)
                
                # ── Screenshot after each test case ──────────────────
                self._take_terminal_screenshot(tc_id)
                time.sleep(0.5)
                
            except Exception as exc:
                logger.error(f"[1.2.1] {tc_id} exception: {exc}")
                from icaf.core.result_recorder import record_result, save_evidence
                self._take_terminal_screenshot(f"{tc_id}_error")
                ev = save_evidence(tc_id, "N/A", str(exc))
                record_result(tc_id, tc_name, _desc,
                              "N/A", str(exc), "No exception",
                              str(exc), "ERROR", [ev])

            self.context.current_testcase = None
            StepRunner([ClearTerminalStep(TERMINAL)]).run(self.context)
            time.sleep(0.4)

        # ── Teardown ──────────────────────────────────────────────────────
        try:
            self._ssh.close()
        except Exception:
            pass

        raw_results = get_results()
        self.context.scan_results = {"user_authentication": raw_results}
        return self._build_testcase_objects(raw_results)

    # ── Open terminal (local shell — no second SSH) ───────────────────────

    def _open_terminal(self):
        """
        Open a gnome-terminal with a tmux session showing a local shell.
        Commands are typed into it via _patch_visual so the tester sees
        activity — but there is no second SSH connection.
        We show the DUT IP in the prompt so it's clear what's being tested.
        """
        subprocess.run(["tmux", "kill-session", "-t", TMUX_NAME],
                       stderr=subprocess.DEVNULL)
        subprocess.run(["tmux", "new-session", "-d", "-s", TMUX_NAME])

        subprocess.Popen([
            "gnome-terminal",
            f"--title=ICAF — Alpine DUT ({self.context.ssh_ip})",
            "--", "tmux", "attach", "-t", TMUX_NAME,
        ])
        time.sleep(2.0)

        # Show a clear header so it's obvious what this terminal is for
        _tmux(f"echo '=== ICAF Clause 1.2.1 — DUT: {self.context.ssh_ip} ==='")
        _tmux("echo '=== User Authentication Testing (Console, SSH, SFTP, SCP) ==='")
        _tmux("echo ''")
        time.sleep(0.5)
        logger.info("[1.2.1] Terminal window opened")

    # ── Patch: type every ssh.run command visually into tmux ──────────────

    def _patch_visual(self):
        """Patch SSH run method to display commands and output in tmux."""
        orig = self._ssh.run

        def visual_run(command, sudo=False, input_text=None, timeout=30):
            # Show command being run
            _tmux(f"echo '$ {command}'")
            time.sleep(0.2)
            # Execute via paramiko and show output
            result = orig(command, sudo=sudo, input_text=input_text, timeout=timeout)
            out, err, code = result
            combined = (out + err).strip()
            if combined:
                for line in combined.splitlines()[:20]:
                    _tmux(f"echo '  {line}'")
            _tmux(f"echo '  [exit: {code}]'")
            time.sleep(0.3)
            return result

        self._ssh.run = visual_run

    # ── Screenshot Capture ───────────────────────────────────────────────

    def _take_terminal_screenshot(self, tc_id):
        """
        Capture terminal screenshot using terminal renderer (scrot).
        
        Args:
            tc_id: Test case ID for filename
        """
        if not HAS_TERMINAL_RENDERER or terminal_renderer is None:
            logger.warning(f"[1.2.1] Terminal renderer not available; skipping screenshot for {tc_id}")
            return
        
        try:
            # Attempt to use ICAF context for proper evidence path
            try:
                clause   = getattr(self.context, "clause", "1_2_1")
                testcase = self.context.current_testcase
                path_dir = self.context.evidence.screenshot_path(clause, testcase)
            except Exception:
                # Fallback to manual path construction
                path_dir = os.path.join("evidence", "clause_1_2_1", "screenshots")
            
            os.makedirs(path_dir, exist_ok=True)
            ts        = datetime.datetime.now().strftime("%H%M%S_%f")
            full_path = os.path.join(path_dir, f"{tc_id}_{TERMINAL}_{ts}.png")
            
            # Render terminal screenshot
            saved = terminal_renderer.render(full_path)
            
            if saved and os.path.exists(saved):
                logger.info(f"[1.2.1] Screenshot saved: {saved}")
                
                # Append screenshot to evidence files in test result
                for r in get_results():
                    if r.get("tc_id") == tc_id or tc_id in str(r.get("tc_id", "")):
                        r.setdefault("evidence_files", []).append(saved)
                        logger.info(f"[1.2.1] Added evidence file to {tc_id}: {saved}")
                        break
            else:
                logger.warning(f"[1.2.1] Screenshot not saved for {tc_id}")
        
        except Exception as exc:
            logger.error(f"[1.2.1] Screenshot error for {tc_id}: {exc}", exc_info=True)
        
        finally:
            # Always update the live window with the final state of this TC
            try:
                terminal_renderer.render(_LIVE_PATH)
            except Exception:
                pass

    # ── Paramiko SSH ──────────────────────────────────────────────────────

    def _make_ssh_session(self):
        """Create and establish paramiko SSH session."""
        import paramiko as _pm
        client = _pm.SSHClient()
        client.set_missing_host_key_policy(_pm.AutoAddPolicy())
        client.connect(
            hostname=self.context.ssh_ip, port=22,
            username=self.context.ssh_user,
            password=self.context.ssh_password, timeout=30,
        )
        logger.info(f"[1.2.1] SSH connected to {self.context.ssh_ip}")
        return _SSHWrapper(client)

    @staticmethod
    def _build_testcase_objects(raw_results):
        """Build TestCase objects from raw result data."""
        tc_objects = []
        for r in raw_results:
            tc = TestCase(name=r["tc_id"], description=r.get("tc_name", ""))
            screenshot = next(
                (f for f in r.get("evidence_files", []) if f.endswith(".png")),
                None,
            )
            tc.add_evidence(command=r.get("input_cmd"),
                            output=r.get("output"),
                            screenshot=screenshot)
            tc.status = {"PASS": "PASS", "FAIL": "FAIL", "ERROR": "FAIL"}.get(
                r.get("verdict", "FAIL"), "FAIL"
            )
            tc.raw_result = r
            tc_objects.append(tc)
        return tc_objects


class _SSHWrapper:
    """Wrapper around paramiko SSH client for command execution."""

    def __init__(self, client):
        self._client = client

    def run(self, command, sudo=False, input_text=None, timeout=30):
        """
        Execute command via SSH and return output.
        
        Args:
            command: Shell command to execute
            sudo: Whether to use sudo
            input_text: Text to send to stdin if needed
            timeout: Command execution timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        use_pty = (
            "passwd" in command
            and "cat" not in command
            and "grep" not in command
        )
        stdin, stdout, stderr = self._client.exec_command(
            command, timeout=timeout, get_pty=use_pty
        )
        if input_text:
            try:
                stdin.write(input_text)
                stdin.flush()
                stdin.channel.shutdown_write()
            except Exception:
                pass
        out  = stdout.read().decode("utf-8", errors="replace")
        err  = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        return out, err, code

    def close(self):
        """Close SSH connection."""
        try:
            self._client.close()
        except Exception:
            pass