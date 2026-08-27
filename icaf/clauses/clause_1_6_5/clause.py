"""
icaf/clauses/clause_1_6_5/clause.py  —  ITSAR 1.6.5
Terminal renderer receives every command + output so screenshots show real DUT activity.
Each TC gets its own separate screenshot — renderer is cleared between TCs.
"""

import os
import time
import shutil
import subprocess
from datetime import datetime

from icaf.core.clause import BaseClause
from icaf.core.testcase import TestCase
from icaf.core.result_recorder import clear_results, get_results, set_terminal_manager
from icaf.utils.logger import logger

from icaf.clauses.clause_1_6_5.testcases.tc_165_001 import run as run_tc001
from icaf.clauses.clause_1_6_5.testcases.tc_165_002 import run as run_tc002
from icaf.clauses.clause_1_6_5.testcases.tc_165_003 import run as run_tc003

from icaf.terminal.terminal_renderer import terminal_renderer

TERMINAL   = "dut"
_LIVE_PATH = "/tmp/icaf_live_terminal.png"

_TC_MANIFEST = [
    (run_tc001, "TC-165-001", "TC1 — Read Access Rights for Sensitive Files",
     "Unpriv user denied read of sensitive files; root succeeds"),
    (run_tc002, "TC-165-002", "TC2 — Manipulation of Sensitive System Files",
     "Unpriv denied modification; root succeeds for config/logs"),
    (run_tc003, "TC-165-003", "TC3 — Passwords Stored Hashed, Not in Cleartext",
     "All passwords SHA-512 hashed; no plaintext in config"),
]


# ── Public helper imported by tc files ────────────────────────────────────────

def mirror_to_terminal(command: str, output: str, user: str = "root") -> None:
    """
    Feed a command + its real output into the terminal renderer.

    Called automatically for every root command via the patched ssh.run.
    tc files must call this explicitly after every _exec() on the unpriv client
    so that unprivileged-user commands also appear in the screenshot.

    Args:
        command: The shell command that was run.
        output:  Combined stdout+stderr (already stripped).
        user:    Prompt label — "root" → root@localhost:~#, else user@localhost:~$
    """
    prompt = "root@localhost:~#" if user == "root" else f"{user}@localhost:~$"
    terminal_renderer.add_command_with_prompt(prompt, command)
    if output and output.strip():
        terminal_renderer.add_output(output.strip())


# ── Clause ────────────────────────────────────────────────────────────────────

class Clause_1_6_5(BaseClause):

    name = "1.6.5 Protecting Data and Information in Storage"

    def __init__(self, context):
        super().__init__(context)
        self._ssh      = None
        self._feh_proc = None   # single feh window, opened once

    def run(self):
        clear_results()

        tm = getattr(self.context, "terminal_manager", None)
        if tm is not None:
            set_terminal_manager(tm)

        self._ssh = self._make_ssh_session()

        # Wrap ssh.run so every root command auto-feeds the renderer
        self._patch_visual()

        # Write a blank initial PNG so feh has something to open
        terminal_renderer.clear()
        terminal_renderer.render(_LIVE_PATH)
        self._open_live_window()

        for runner_fn, tc_id, tc_name, _desc in _TC_MANIFEST:
            logger.info(f"[1.6.5] Running {tc_id}: {tc_name}")

            # ── Clear renderer and re-add login banner for each TC ─────────
            # This ensures each TC screenshot shows ONLY that TC's commands
            terminal_renderer.clear()
            self._init_terminal_view()
            terminal_renderer.add_separator(tc_id)
            
            tc_obj = TestCase(name=tc_id, description=tc_name)
            self.context.current_testcase = tc_obj

            try:
                runner_fn(self._ssh)
            except Exception as exc:
                logger.error(f"[1.6.5] {tc_id} exception: {exc}")
                self._record_error(tc_id, tc_name, _desc, str(exc))

            time.sleep(1.2)
            self._take_terminal_screenshot(tc_id)

            self.context.current_testcase = None

        raw_results = get_results()
        self.context.scan_results = {"storage_protection": raw_results}
        return self._build_testcase_objects(raw_results)

    # ── Terminal setup ────────────────────────────────────────────────────

    def _init_terminal_view(self):
        """ the SSH login banner the terminal """
        terminal_renderer.add_raw_line(
            f"ssh -o StrictHostKeyChecking=no {self.context.ssh_user}@{self.context.ssh_ip}",
            color="command",
        )
        terminal_renderer.add_raw_line(
            f"{self.context.ssh_user}@{self.context.ssh_ip}'s password:", color="dim"
        )
        terminal_renderer.add_raw_line("Welcome to Alpine Linux 3.23", color="output")
        terminal_renderer.add_raw_line("root@localhost:~#", color="prompt", newline=False)

    def _open_live_window(self):
        """
        Open a single feh window pointed at _LIVE_PATH.
        feh --reload 1 polls the file every second so the window
        updates automatically whenever we overwrite _LIVE_PATH.
        """
        try:
            self._feh_proc = subprocess.Popen(
                ["feh", "--reload", "1", "--auto-zoom",
                 "--title", "ICAF Live Terminal", _LIVE_PATH],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)
            logger.info(f"[1.6.5] Live window opened (pid {self._feh_proc.pid})")
        except FileNotFoundError:
            logger.warning("[1.6.5] feh not found — install with: sudo apt install feh")
        except Exception as exc:
            logger.warning(f"[1.6.5] Could not open live window: {exc}")

    # ── Auto-feed renderer for every root command ─────────────────────────

    def _patch_visual(self):
        """
        Wrap _SSHWrapper.run so that after every root command executes,
        the command and its combined output are automatically fed into
        the renderer AND the live window is updated.
        """
        orig = self._ssh.run

        def visual_run(command, sudo=False, input_text=None):
            result = orig(command, sudo=sudo, input_text=input_text)
            out, err, _code = result
            combined = (out + err).strip()
            mirror_to_terminal(command, combined, user="root")
            # Update the live window after every single command
            terminal_renderer.render(_LIVE_PATH)
            return result

        self._ssh.run = visual_run

    # ── Screenshot ────────────────────────────────────────────────────────

    def _take_terminal_screenshot(self, tc_id):
        try:
            try:
                clause   = getattr(self.context, "clause", "1_6_5")
                testcase = self.context.current_testcase
                path_dir = self.context.evidence.screenshot_path(clause, testcase)
            except Exception:
                path_dir = os.path.join("evidence", "clause_1_6_5", "screenshots")

            os.makedirs(path_dir, exist_ok=True)
            ts        = datetime.now().strftime("%H%M%S_%f")
            full_path = os.path.join(path_dir, f"{tc_id}_{TERMINAL}_{ts}.png")

            saved = terminal_renderer.render(full_path)

            if saved and os.path.exists(saved):
                logger.info(f"[1.6.5] Screenshot saved: {saved}")
                for r in get_results():
                    if r.get("tc_id") == tc_id:
                        r.setdefault("evidence_files", []).append(saved)
                        break
            else:
                logger.warning(f"[1.6.5] Screenshot not saved for {tc_id}")

        except Exception as exc:
            logger.error(f"[1.6.5] Screenshot error for {tc_id}: {exc}")

        # Always update the live window with the final state of this TC
        terminal_renderer.render(_LIVE_PATH)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _record_error(self, tc_id, tc_name, desc, error_msg):
        from icaf.core.result_recorder import record_result, save_evidence
        ev = save_evidence(tc_id, "N/A", error_msg)
        record_result(
            tc_id, tc_name, desc,
            "N/A", error_msg,
            "No exception expected",
            error_msg, "ERROR", [ev],
        )

    def _make_ssh_session(self, retries=4, delay=4.0):
        import paramiko as _pm
        import socket
        time.sleep(2.0)
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                client = _pm.SSHClient()
                client.set_missing_host_key_policy(_pm.AutoAddPolicy())
                client.connect(
                    hostname       = self.context.ssh_ip,
                    port           = 22,
                    username       = self.context.ssh_user,
                    password       = self.context.ssh_password,
                    timeout        = 30,
                    banner_timeout = 30,
                    auth_timeout   = 30,
                )
                logger.info(f"[1.6.5] SSH connected to {self.context.ssh_ip} (attempt {attempt})")
                return _SSHWrapper(client)
            except (
                _pm.ssh_exception.SSHException,
                ConnectionResetError, OSError, socket.error,
            ) as exc:
                last_exc = exc
                logger.warning(f"[1.6.5] SSH attempt {attempt}/{retries} failed: {exc}")
                time.sleep(delay)
        raise RuntimeError(
            f"[1.6.5] Could not connect to {self.context.ssh_ip} after {retries} attempts: {last_exc}"
        )

    @staticmethod
    def _build_testcase_objects(raw_results):
        tc_objects = []
        for r in raw_results:
            tc = TestCase(name=r["tc_id"], description=r.get("tc_name", ""))
            screenshot = next(
                (f for f in r.get("evidence_files", []) if f and f.endswith(".png")),
                None,
            )
            tc.add_evidence(
                command    = r.get("input_cmd"),
                output     = r.get("output"),
                screenshot = screenshot,
            )
            tc.status = {"PASS": "PASS", "FAIL": "FAIL", "ERROR": "FAIL"}.get(
                r.get("verdict", "FAIL"), "FAIL"
            )
            tc.raw_result = r
            tc_objects.append(tc)
        return tc_objects


# ── SSH wrapper ───────────────────────────────────────────────────────────────

class _SSHWrapper:

    def __init__(self, client):
        self._client = client

    @property
    def _host(self):
        try:
            return self._client.get_transport().getpeername()[0]
        except Exception:
            return "192.168.56.102"

    def run(self, command, sudo=False, input_text=None):
        use_pty = (
            "passwd" in command
            and "cat"  not in command
            and "grep" not in command
        )
        stdin, stdout, stderr = self._client.exec_command(
            command, timeout=30, get_pty=use_pty,
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
        try:
            self._client.close()
        except Exception:
            pass
