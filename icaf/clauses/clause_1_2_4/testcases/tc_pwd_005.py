from icaf.core.result_recorder import record_result, save_evidence


def run(ssh):
    tc_id  = "TC4"
    tc_name = "Verify OS-level PAM policy enforcement"
    all_output = []
    verdict    = "FAIL"

    out1, _, _ = ssh.run("grep -r pam_pwquality /etc/pam.d/ 2>/dev/null")
    all_output.append(f"pam_pwquality : {out1.strip() or '(not found)'}")

    out2, _, _ = ssh.run("apk list --installed 2>/dev/null | grep pwquality")
    all_output.append(f"package       : {out2.strip() or '(not installed)'}")

    out3, _, _ = ssh.run("cat /etc/pam.d/passwd 2>/dev/null")
    all_output.append(f"PAM file:\n{out3.strip()}")

    if ("pam_cracklib" in out3 or "pam_pwquality" in out3) and "minlen=8" in out3:
        verdict = "PASS"

    rep_cmd = "cat /etc/pam.d/passwd"
    evidence = save_evidence(tc_id, rep_cmd, "\n".join(all_output))
    record_result(
        tc_id, tc_name,
        "Verify OS-level PAM module is active with minlen=8.",
        rep_cmd, "\n".join(all_output),
        "PAM module active with minlen=8",
        "Confirmed" if verdict == "PASS" else "Not confirmed",
        verdict, [evidence]
    )
