"""
TC-165-002: Protecting Data and Information in Storage
TC2 — Manipulation of Sensitive System Files

Step 1 (underprivileged user 'test165user'):
  echo marker >> /etc/ssh/sshd_config  → MUST fail
  touch /boot/icaf_test                → MUST fail
  echo marker >> /var/log/messages     → MUST fail

Step 2 (root):
  echo marker >> /etc/ssh/sshd_config  → MUST succeed; revert
  touch /boot/icaf_root_test           → write-restricted; INFO if writable
  echo marker >> /var/log/messages     → MUST succeed; revert
"""

import paramiko as _pm
import time
import re

from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger

TC_ID   = "TC-165-002"
TC_NAME = "TC2 — Manipulation of Sensitive System Files"
TC_DESC = (
    "Verify that underprivileged user cannot manipulate config/firmware/logs. "
    "Root can modify config and logs; boot partition write-protected for all."
)

_UNPRIV_USER = "test165user"
_UNPRIV_PASS = "Test165@Pass"

_CONFIG_FILE = "/etc/ssh/sshd_config"
_BOOT_DIR    = "/boot"
_LOG_FILE    = "/var/log/messages"
_TEST_MARKER = "# icaf_tc2_test_marker"


def _sanitize(text):
    if not text:
        return "(no output)"
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = text.replace('\x00', '')
    return text or "(no output)"


def _open_user_ssh(host, user, password):
    client = _pm.SSHClient()
    client.set_missing_host_key_policy(_pm.AutoAddPolicy())
    client.connect(
        hostname=host, port=22,
        username=user, password=password,
        timeout=30, banner_timeout=30, auth_timeout=30,
    )
    return client


def _exec(client, command):
    _, stdout, stderr = client.exec_command(command, timeout=15)
    out  = stdout.read().decode("utf-8", errors="replace")
    err  = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return (out + err).strip(), code


def run(ssh):
    logger.info(f"[{TC_ID}] Starting")

    # Import renderer bridge
    try:
        from icaf.clauses.clause_1_6_5.clause_1_6_5_clause import mirror_to_terminal
        _mirror = mirror_to_terminal
    except Exception:
        _mirror = lambda cmd, out, user="root": None  # noqa: E731

    parts    = []
    all_pass = True
    summary  = []

    host = ssh._host or "192.168.56.102"

    # ── Setup ──────────────────────────────────────────────────────────────
    out, err, _ = ssh.run(f"/usr/sbin/adduser -D {_UNPRIV_USER} 2>&1 || true")
    parts.append(f"$ /usr/sbin/adduser -D {_UNPRIV_USER} 2>&1 || true")
    parts.append((out + err).strip() or "(ok)")

    out, err, _ = ssh.run(f"echo '{_UNPRIV_USER}:{_UNPRIV_PASS}' | chpasswd 2>&1")
    parts.append(f"$ echo '{_UNPRIV_USER}:<password>' | chpasswd 2>&1")
    parts.append((out + err).strip())

    # ── Open unpriv SSH session ────────────────────────────────────────────
    time.sleep(2.0)
    _mirror(f"ssh {_UNPRIV_USER}@{host}", f"login as '{_UNPRIV_USER}'", user="root")

    try:
        unpriv = _open_user_ssh(host, _UNPRIV_USER, _UNPRIV_PASS)
        parts.append(f"$ ssh {_UNPRIV_USER}@{host}")
        parts.append(f"Login as '{_UNPRIV_USER}': SUCCESS")
    except Exception as exc:
        parts.append(f"Login as '{_UNPRIV_USER}': FAILED — {exc}")
        all_pass = False
        _teardown(ssh, parts)
        _finish(parts, all_pass, summary)
        return

    def _run_and_mirror(command):
        """Execute via unpriv client and feed result into the terminal renderer."""
        result, code = _exec(unpriv, command)
        _mirror(command, result, user=_UNPRIV_USER)
        return result, code

    # ── STEP 1a: Config modification ──────────────────────────────────────
    result, code = _run_and_mirror(f"echo '{_TEST_MARKER}' >> {_CONFIG_FILE} 2>&1")
    parts.append(f"$ echo '{_TEST_MARKER}' >> {_CONFIG_FILE} 2>&1")
    parts.append(result if result else "(no output)")
    denied_cfg = code != 0 and "ermission denied" in result
    if not denied_cfg:
        all_pass = False
        ssh.run(f"sed -i '/{_TEST_MARKER}/d' {_CONFIG_FILE} 2>/dev/null || true")
    parts.append(f"Modification denied (expected): {denied_cfg}")
    summary.append(
        f"  Unpriv → config modification  : {'PASS (denied)' if denied_cfg else 'FAIL (allowed)'}"
    )

    # ── STEP 1b: Boot partition write ─────────────────────────────────────
    result, code = _run_and_mirror(f"touch {_BOOT_DIR}/icaf_test 2>&1")
    parts.append(f"$ touch {_BOOT_DIR}/icaf_test 2>&1")
    parts.append(result if result else "(no output)")
    denied_boot = code != 0 and "ermission denied" in result
    if not denied_boot:
        all_pass = False
        ssh.run(f"rm -f {_BOOT_DIR}/icaf_test 2>/dev/null || true")
    parts.append(f"Boot write denied (expected): {denied_boot}")
    summary.append(
        f"  Unpriv → boot dir write       : {'PASS (denied)' if denied_boot else 'FAIL (allowed)'}"
    )

    # ── STEP 1c: Log modification ─────────────────────────────────────────
    result, code = _run_and_mirror(f"echo '{_TEST_MARKER}' >> {_LOG_FILE} 2>&1")
    parts.append(f"$ echo '{_TEST_MARKER}' >> {_LOG_FILE} 2>&1")
    parts.append(result if result else "(no output)")
    denied_log = code != 0 and "ermission denied" in result
    if not denied_log:
        all_pass = False
        ssh.run(f"sed -i '/{_TEST_MARKER}/d' {_LOG_FILE} 2>/dev/null || true")
    parts.append(f"Log modification denied (expected): {denied_log}")
    summary.append(
        f"  Unpriv → log modification     : {'PASS (denied)' if denied_log else 'FAIL (allowed)'}"
    )

    unpriv.close()

    # ── STEP 2a: Root modifies config ─────────────────────────────────────
    out, err, code = ssh.run(f"echo '{_TEST_MARKER}' >> {_CONFIG_FILE} 2>&1")
    result = (out + err).strip()
    parts.append(f"$ echo '{_TEST_MARKER}' >> {_CONFIG_FILE} 2>&1")
    parts.append(result if result else "(ok — no output means success)")
    root_cfg = code == 0
    if root_cfg:
        out2, err2, _ = ssh.run(f"tail -1 {_CONFIG_FILE}")
        parts.append(f"$ tail -1 {_CONFIG_FILE}")
        parts.append((out2 + err2).strip())
        ssh.run(f"sed -i '/{_TEST_MARKER.replace('#', '[#]')}/d' {_CONFIG_FILE} 2>/dev/null || true")
        parts.append("(reverted — test marker removed)")
    if not root_cfg:
        all_pass = False
    parts.append(f"Root modification success (expected): {root_cfg}")
    summary.append(
        f"  Root  → config modification   : {'PASS (success)' if root_cfg else 'FAIL'}"
    )

    # ── STEP 2b: Boot partition ────────────────────────────────────────────
    out, err, code = ssh.run(f"ls -la {_BOOT_DIR}/ 2>&1 | head -8")
    parts.append(f"$ ls -la {_BOOT_DIR}/ | head -8")
    parts.append((out + err).strip())

    out, err, code = ssh.run(f"touch {_BOOT_DIR}/icaf_root_test 2>&1")
    boot_write = (out + err).strip()
    parts.append(f"$ touch {_BOOT_DIR}/icaf_root_test 2>&1")
    parts.append(boot_write if boot_write else "(no output)")
    if code != 0:
        parts.append("Boot partition write-protected (expected): True")
        summary.append("  Root  → boot dir write        : PASS (restricted — as expected)")
    else:
        ssh.run(f"rm -f {_BOOT_DIR}/icaf_root_test 2>/dev/null || true")
        parts.append("Boot partition writable by root (filesystem not read-only)")
        summary.append("  Root  → boot dir write        : INFO (writable — check mount flags)")

    # ── STEP 2c: Root modifies log ────────────────────────────────────────
    out, err, code = ssh.run(f"echo '{_TEST_MARKER}' >> {_LOG_FILE} 2>&1")
    result = (out + err).strip()
    parts.append(f"$ echo '{_TEST_MARKER}' >> {_LOG_FILE} 2>&1")
    parts.append(result if result else "(ok — no output means success)")
    if code == 0:
        out2, err2, _ = ssh.run(f"tail -1 {_LOG_FILE}")
        parts.append(f"$ tail -1 {_LOG_FILE}")
        parts.append((out2 + err2).strip())
        ssh.run(f"sed -i '/{_TEST_MARKER}/d' {_LOG_FILE} 2>/dev/null || true")
        parts.append("(reverted — test marker removed)")
    root_log = code == 0
    if not root_log:
        all_pass = False
    parts.append(f"Root log modification success (expected): {root_log}")
    summary.append(
        f"  Root  → log modification      : {'PASS (success)' if root_log else 'FAIL'}"
    )

    # ── Teardown & record ─────────────────────────────────────────────────
    _teardown(ssh, parts)
    _finish(parts, all_pass, summary)
    logger.info(f"[{TC_ID}] Done — {'PASS' if all_pass else 'FAIL'}")


def _teardown(ssh, parts):
    out, err, _ = ssh.run(
        f"/usr/sbin/deluser --remove-home {_UNPRIV_USER} 2>&1 || true"
    )
    parts.append(f"$ /usr/sbin/deluser --remove-home {_UNPRIV_USER}")
    parts.append((out + err).strip())


def _finish(parts, all_pass, summary):
    verdict = "PASS" if all_pass else "FAIL"
    parts.append("\n=== Summary ===")
    parts.extend(summary)
    parts.append(f"\nVerdict: {verdict}")
    full_output = "\n".join(parts)
    input_cmd = (
        f"[as {_UNPRIV_USER}] echo >> /etc/ssh/sshd_config; touch /boot/icaf_test; "
        f"echo >> /var/log/messages; "
        f"[as root] echo >> /etc/ssh/sshd_config; ls /boot; echo >> /var/log/messages"
    )
    ev = save_evidence(TC_ID, input_cmd, full_output)
    record_result(
        TC_ID, TC_NAME, TC_DESC,
        input_cmd, full_output,
        "Unpriv denied all modifications; root succeeds for config and logs; boot restricted",
        full_output, verdict, [ev],
    )