from icaf.core.result_recorder import record_result, save_evidence


def run(ssh):
    tc_id   = "TC5"
    tc_name = "Reject passwords shorter than minimum length"
    all_output = []
    verdict    = "FAIL"

    # ── Step 1: PAM config check ──────────────────────────────────────────
    out_pam, _, _ = ssh.run("grep minlen /etc/pam.d/passwd 2>/dev/null")
    out_pwq, _, _ = ssh.run("grep minlen /etc/security/pwquality.conf 2>/dev/null")
    all_output.append(f"PAM minlen config : {out_pam.strip() or '(not found)'}")
    all_output.append(f"pwquality minlen  : {out_pwq.strip() or '(not found)'}")
    config_ok = "minlen=8" in (out_pam + out_pwq) or "minlen = 8" in (out_pam + out_pwq)
    all_output.append(f"minlen=8 enforced : {config_ok}")

    # ── Step 2: Delete testpwduser password so su needs no old password ───
    # passwd -d removes the password → su testpwduser works without a password
    # This means passwd as the user won't prompt "Old password:" either.
    ssh.run("passwd -d testpwduser 2>&1")
    all_output.append("Cleared testpwduser password (passwd -d)")

    # ── Step 3: Attempt 4-char password AS testpwduser (non-root) ─────────
    # Running as testpwduser forces PAM minlen=8 enforcement.
    # No "Old password" prompt because password was deleted.
    # Expected: "Bad password: too short" + "passwd: password unchanged"
    short_pwd = "A1!x"
    cmd = (
        f"printf '{short_pwd}\\n{short_pwd}\\n'"
        f" | su testpwduser -c passwd 2>&1"
    )
    out, err, code = ssh.run(cmd)
    combined = (out + " " + err).strip()

    all_output.append(f"Output  : {combined}")
    all_output.append(f"Exit    : {code}")

    # ── Step 4: Verdict ───────────────────────────────────────────────────
    accepted = (
        any(k in combined.lower() for k in ["password changed", "changed by"])
        and "unchanged" not in combined.lower()
    )

    if config_ok and not accepted:
        verdict = "PASS"
        all_output.append(f"PASS: '{short_pwd}' (4 chars) rejected — passwd: password unchanged")
    elif config_ok and accepted:
        verdict = "FAIL"
        all_output.append(f"FAIL: '{short_pwd}' (4 chars) ACCEPTED — PAM minlen=8 not enforced")
    else:
        verdict = "FAIL"
        all_output.append("FAIL: minlen=8 not found in PAM config")

    # ── Step 5: Record ────────────────────────────────────────────────────
    evidence = save_evidence(tc_id, cmd, "\n".join(all_output))
    record_result(
        tc_id, tc_name,
        "Verify DUT rejects a 4-character password as testpwduser (non-root). "
        "PAM must enforce minlen=8 — password must remain UNCHANGED.",
        cmd, combined,
        "4-char password rejected — passwd: password unchanged — minlen=8 enforced",
        "Rejected — password unchanged" if verdict == "PASS"
        else "FAIL — short password accepted",
        verdict, [evidence],
    )
