"""
TC-165-001: Protecting Data and Information in Storage
TC1 — Read Access Rights for Sensitive Files

Step 1 (underprivileged user 'test165user'):
  cat /etc/shadow                           → MUST fail (Permission denied)
  head -c 4 /boot/vmlinuz-lts > /dev/null  → MUST fail (Permission denied)
  cat /var/log/messages                     → MUST fail (Permission denied)

Step 2 (root):
  cat /etc/shadow          → MUST succeed
  ls -la /boot/vmlinuz*    → MUST succeed
  tail -5 /var/log/messages → MUST succeed
"""

import paramiko as _pm
import time
import re

from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger

TC_ID   = "TC-165-001"
TC_NAME = "TC1 — Read Access Rights for Sensitive Files"
TC_DESC = (
    "Verify read access rights of sensitive files (config, firmware, logs). "
    "Underprivileged user must be denied; highest privileged user must succeed."
)

_UNPRIV_USER = "test165user"
_UNPRIV_PASS = "Test165@Pass"

_CONFIG_FILE   = "/etc/shadow"
_FIRMWARE_FILE = "/boot/vmlinuz-lts"
_LOG_FILE      = "/var/log/messages"


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

    # Import renderer bridge — allows unpriv commands to appear in screenshots
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

    # Show the SSH login in the renderer
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
        """
        Execute via the unpriv paramiko client AND feed the result into the
        terminal renderer so it appears in the screenshot.
        """
        result, code = _exec(unpriv, command)
        _mirror(command, result, user=_UNPRIV_USER)
        return result, code

    # ── STEP 1a: Config file ───────────────────────────────────────────────
    result, code = _run_and_mirror(f"cat {_CONFIG_FILE} 2>&1")
    result = _sanitize(result)
    parts.append(f"$ cat {_CONFIG_FILE}")
    parts.append(result)
    denied_config = code != 0 and "ermission denied" in result
    if not denied_config:
        all_pass = False
    parts.append(f"Access denied (expected): {denied_config}")
    summary.append(
        f"  Unpriv → config file read     : {'PASS (denied)' if denied_config else 'FAIL (allowed)'}"
    )

    # ── STEP 1b: Firmware image ────────────────────────────────────────────
    # Test actual read access with head; stdout redirected to /dev/null to avoid
    # binary in the report. EXIT:0 = readable (FAIL); EXIT:1 = denied (PASS).
    fw_cmd = f"head -c 4 {_FIRMWARE_FILE} > /dev/null 2>&1; echo EXIT:$?"
    result, _ = _run_and_mirror(fw_cmd)
    result = _sanitize(result)
    parts.append(f"$ head -c 4 {_FIRMWARE_FILE} > /dev/null 2>&1; echo EXIT:$?")
    parts.append(result)
    denied_fw = "EXIT:0" not in result
    if not denied_fw:
        all_pass = False
    parts.append(f"Read access denied (expected): {denied_fw}")
    summary.append(
        f"  Unpriv → firmware read        : {'PASS (denied)' if denied_fw else 'FAIL (world-readable)'}"
    )

    # ── STEP 1c: Log file ─────────────────────────────────────────────────
    result, code = _run_and_mirror(f"cat {_LOG_FILE} 2>&1")
    result = _sanitize(result)
    parts.append(f"$ cat {_LOG_FILE}")
    parts.append(result.splitlines()[0] if result.splitlines() else result)
    denied_log = code != 0 and "ermission denied" in result
    if not denied_log:
        all_pass = False
    parts.append(f"Access denied (expected): {denied_log}")
    summary.append(
        f"  Unpriv → log file read        : {'PASS (denied)' if denied_log else 'FAIL (allowed)'}"
    )

    unpriv.close()

    # ── STEP 2a: Root reads config ─────────────────────────────────────────
    out, err, code = ssh.run(f"cat {_CONFIG_FILE}")
    output = _sanitize((out + err).strip())
    hashed    = [l.split(":")[0] for l in output.splitlines() if "$6$" in l]
    plaintext = [
        l.split(":")[0] for l in output.splitlines()
        if ":" in l and len(l.split(":")) > 1
        and l.split(":")[1] not in ("!", "!!", "x", "*", "")
        and not l.split(":")[1].startswith("$")
    ]
    parts.append(f"$ cat {_CONFIG_FILE}")
    parts.append(f"Hashed accounts   : {hashed}")
    parts.append(f"Plaintext accounts: {plaintext}")
    root_config = code == 0 and output != "(no output)"
    if not root_config:
        all_pass = False
    parts.append(f"Root read success (expected): {root_config}")
    summary.append(
        f"  Root  → config file read      : {'PASS (success)' if root_config else 'FAIL'}"
    )

    # ── STEP 2b: Root reads firmware ──────────────────────────────────────
    out, err, code = ssh.run(
        "ls -la /boot/vmlinuz* 2>/dev/null || ls -la /boot/ 2>/dev/null | head -10"
    )
    fw_out = _sanitize((out + err).strip())
    parts.append("$ ls -la /boot/vmlinuz* 2>/dev/null || ls -la /boot/ | head -10")
    parts.append(fw_out if fw_out else "(no firmware found)")
    root_fw = code == 0 and fw_out not in ("(no output)", "(no firmware found)")
    if not root_fw:
        all_pass = False
    parts.append(f"Root read success (expected): {root_fw}")
    summary.append(
        f"  Root  → firmware image read   : {'PASS (success)' if root_fw else 'FAIL'}"
    )

    # ── STEP 2c: Root reads log ────────────────────────────────────────────
    out, err, code = ssh.run(f"tail -5 {_LOG_FILE} 2>/dev/null")
    log_out = _sanitize((out + err).strip())
    parts.append(f"$ tail -5 {_LOG_FILE}")
    parts.append(log_out if log_out not in ("", "(no output)") else "(no log output)")
    root_log = code == 0
    if not root_log:
        all_pass = False
    parts.append(f"Root read success (expected): {root_log}")
    summary.append(
        f"  Root  → log file read         : {'PASS (success)' if root_log else 'FAIL'}"
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
        f"[as {_UNPRIV_USER}] cat /etc/shadow; "
        f"head -c 4 /boot/vmlinuz-lts > /dev/null; "
        f"cat /var/log/messages; "
        f"[as root] cat /etc/shadow; ls -la /boot/vmlinuz*; tail -5 /var/log/messages"
    )
    ev = save_evidence(TC_ID, input_cmd, full_output)
    record_result(
        TC_ID, TC_NAME, TC_DESC,
        input_cmd, full_output,
        "Unpriv user denied; root succeeds for config, firmware, logs",
        full_output, verdict, [ev],
    )