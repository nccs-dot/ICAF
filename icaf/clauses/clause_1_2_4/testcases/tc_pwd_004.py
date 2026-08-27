from icaf.core.result_recorder import record_result, save_evidence


def run(ssh):
    tc_id  = "TC3"
    tc_name = "Verify min length cannot be set below 8 characters"
    all_output = []
    verdict    = "FAIL"

    for cmd, label in [
        ("cat /etc/pam.d/passwd 2>/dev/null",             "PAM passwd"),
        ("cat /etc/security/pwquality.conf 2>/dev/null",  "pwquality.conf"),
        ("grep PASS_MIN_LEN /etc/login.defs 2>/dev/null", "login.defs"),
        ("grep -r minlen /etc/security/ /etc/pam.d/ 2>/dev/null", "minlen grep"),
    ]:
        out, _, _ = ssh.run(cmd)
        all_output.append(f"{label}:\n{out.strip()}")

    combined = "\n".join(all_output)
    if "minlen=8" in combined or "minlen = 8" in combined:
        verdict = "PASS"

    rep_cmd = "grep -r minlen /etc/security/ /etc/pam.d/"
    evidence = save_evidence(tc_id, rep_cmd, combined)
    record_result(
        tc_id, tc_name,
        "Verify minlen=8 is hardcoded in PAM config and cannot be set below 8.",
        rep_cmd, combined,
        "minlen=8 present in config",
        "Confirmed" if verdict == "PASS" else "Not found",
        verdict, [evidence]
    )
