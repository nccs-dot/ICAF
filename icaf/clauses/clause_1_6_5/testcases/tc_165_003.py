"""
TC-165-003 — TC3: Passwords Stored Hashed, Not in Cleartext (Alpine Linux)

Steps:
  1. cat /etc/shadow  → all passwords must be $6$ SHA-512, no plaintext
  2. cat /etc/passwd  → all fields must be 'x' placeholder
  3. grep /etc/ssh/sshd_config → no key=value plaintext passwords
  4. ls -la + head /etc/ssh/ssh_host_rsa_key → PEM encoded, 600 perms
  5. grep /etc/ for plaintext credential values
     → exclude: empty values (''), yes/no, comment lines (#)
     → /etc/update-extlinux.conf password='' is an EMPTY field — not cleartext
"""

import re
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger

TC_ID   = "TC-165-003"
TC_NAME = "TC3 — Passwords Stored Hashed/Encrypted, Not in Cleartext"
TC_DESC = ("Verify passwords and auth attributes in config files are "
           "stored hashed/encrypted, never in cleartext.")


def _sanitize(text):
    if not text:
        return "(no output)"
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.replace('\x00', '') or "(no output)"


def run(ssh):
    logger.info(f"[{TC_ID}] Starting")
    parts, summary = [], []
    all_pass = True

    # ── whoami ────────────────────────────────────────────────────────────
    out, err, _ = ssh.run("whoami")
    parts.append("$ whoami")
    parts.append(_sanitize((out + err).strip()))

    # ── (a) /etc/shadow — hashed passwords ───────────────────────────────
    parts.append("\n$ cat /etc/shadow")
    out, err, _ = ssh.run("cat /etc/shadow")
    shadow = _sanitize((out + err).strip())
    hashed    = [l.split(":")[0] for l in shadow.splitlines() if "$6$" in l]
    plaintext = [
        l.split(":")[0] for l in shadow.splitlines()
        if ":" in l and len(l.split(":")) > 1
        and l.split(":")[1] not in ("!", "!!", "x", "*", "")
        and not l.split(":")[1].startswith("$")
    ]
    # Show one truncated hash as evidence
    first_hash = next((l for l in shadow.splitlines() if "$6$" in l), "")
    if first_hash:
        user  = first_hash.split(":")[0]
        hpart = first_hash.split(":")[1][:35]
        parts.append(f"{user}:{hpart}... (SHA-512 $6$ — truncated)")
    parts.append(f"Hashed accounts ($6$) : {hashed}")
    parts.append(f"Plaintext accounts    : {plaintext}")
    shadow_pass = len(plaintext) == 0 and len(hashed) > 0
    if not shadow_pass:
        all_pass = False
    parts.append(f"Shadow check PASS     : {shadow_pass}")
    summary.append(f"  /etc/shadow hashed (no cleartext) : {'PASS' if shadow_pass else 'FAIL'}")

    # ── (b) /etc/passwd — x placeholder ──────────────────────────────────
    parts.append("\n$ cat /etc/passwd  (first 3 lines)")
    out, err, _ = ssh.run("cat /etc/passwd")
    passwd = _sanitize((out + err).strip())
    parts.append("\n".join(passwd.splitlines()[:3]))
    passwd_safe = all(
        l.split(":")[1] == "x"
        for l in passwd.splitlines()
        if ":" in l and len(l.split(":")) > 1
    )
    parts.append(f"All 'x' placeholders  : {passwd_safe}")
    if not passwd_safe:
        all_pass = False
    summary.append(f"  /etc/passwd x-placeholder         : {'PASS' if passwd_safe else 'FAIL'}")

    # ── (c) sshd_config — no plaintext password values ───────────────────
    parts.append("\n$ grep -n -E 'password=|secret=|key=' /etc/ssh/sshd_config")
    out, err, _ = ssh.run(
        "grep -n -E 'password=|secret=|key=' /etc/ssh/sshd_config 2>/dev/null "
        "|| echo '(no matches)'"
    )
    cfg = _sanitize((out + err).strip())
    parts.append(cfg if cfg else "(no plaintext password values in sshd_config)")

    # PASS if no matches found — command returns "(no matches)" on Alpine busybox
    cfg_pass = (
        "(no matches)" in cfg
        or cfg in ("(no output)", "(no plaintext password values in sshd_config)")
    )
    if not cfg_pass:
        all_pass = False
    parts.append(f"Config plaintext PASS : {cfg_pass}")
    summary.append(f"  sshd_config no cleartext          : {'PASS' if cfg_pass else 'FAIL'}")

    # ── (d) SSH host keys — PEM + 600 perms ──────────────────────────────
    parts.append("\n$ ls -la /etc/ssh/ssh_host_*_key")
    out, err, _ = ssh.run("ls -la /etc/ssh/ssh_host_*_key 2>/dev/null")
    key_ls = _sanitize((out + err).strip())
    parts.append(key_ls)

    parts.append("\n$ head -1 /etc/ssh/ssh_host_rsa_key")
    out, err, _ = ssh.run("head -1 /etc/ssh/ssh_host_rsa_key 2>/dev/null")
    pem = _sanitize((out + err).strip())
    parts.append(pem)
    pem_pass  = "BEGIN" in pem and "PRIVATE KEY" in pem
    bad_perms = [l for l in key_ls.splitlines()
                 if l.strip() and not l.startswith("-rw-------")]
    key_pass  = pem_pass and len(bad_perms) == 0
    if not key_pass:
        all_pass = False
    parts.append(f"PEM-encoded    : {pem_pass}")
    parts.append(f"Bad permissions: {bad_perms}")
    parts.append(f"Key check PASS : {key_pass}")
    summary.append(f"  SSH keys PEM + 600 perms          : {'PASS' if key_pass else 'FAIL'}")

    # ── (e) /etc/ config scan — plaintext credential VALUES only ─────────
    parts.append("\n$ grep -rn -E '(password|secret|token)=.' /etc/ | grep -v '#' | grep -v \"=''\" | grep -v '=\"\"'")
    out, err, _ = ssh.run(
        r"""grep -rn -E '(password|secret|token)=.' /etc/ 2>/dev/null """
        r"""| grep -v '#' """
        r"""| grep -v "=''" """
        r"""| grep -v '=""' """
        r"""| grep -v -E "=(yes|no|none|any|'')$" """
        r"""| grep -v '.swp' """
        r"""| head -10"""
    )
    raw_hits = _sanitize((out + err).strip())
    # Further filter in Python — exclude empty/boolean values
    real_hits = []
    for line in raw_hits.splitlines():
        if "=" not in line:
            continue
        val = line.split("=", 1)[1].strip().strip("'\"")
        if val in ("", "yes", "no", "none", "any"):
            continue
        real_hits.append(line)

    parts.append(
        "\n".join(real_hits) if real_hits
        else "(no plaintext credential values found in /etc/)"
    )
    scan_pass = len(real_hits) == 0
    if not scan_pass:
        all_pass = False
    parts.append(f"Config scan PASS : {scan_pass}")
    summary.append(f"  /etc/ scan (no cleartext values)  : {'PASS' if scan_pass else 'FAIL'}")

    verdict = "PASS" if all_pass else "FAIL"
    parts.append("\n=== Summary ===")
    parts.extend(summary)
    parts.append(f"\nVerdict: {verdict}")

    full = "\n".join(parts)
    cmd  = ("whoami; cat /etc/shadow; cat /etc/passwd; "
            "grep ... /etc/ssh/sshd_config; ls -la /etc/ssh/ssh_host_*_key; "
            "head -1 /etc/ssh/ssh_host_rsa_key; grep -rn ... /etc/")
    ev = save_evidence(TC_ID, cmd, full)
    record_result(TC_ID, TC_NAME, TC_DESC, cmd, full,
                  "All passwords SHA-512 hashed; no plaintext in config",
                  full, verdict, [ev])
    logger.info(f"[{TC_ID}] Done — {verdict}")