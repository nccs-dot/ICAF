from icaf.core.result_recorder import record_result, save_evidence


def run(ssh):
    tc_id  = "TC-PWD-001"
    tc_name = "Reject password shorter than 8 characters"
    all_output = []
    verdict    = "FAIL"

    out1, _, _ = ssh.run("grep minlen /etc/pam.d/passwd 2>/dev/null")
    out2, _, _ = ssh.run("grep minlen /etc/security/pwquality.conf 2>/dev/null")
    all_output.append(f"PAM config   : {out1.strip() or '(not found)'}")
    all_output.append(f"pwquality    : {out2.strip() or '(not found)'}")
    config_ok = "minlen=8" in (out1 + out2) or "minlen = 8" in (out1 + out2)
    all_output.append(f"minlen=8     : {config_ok}")

    known = "TempValid@1"
    ssh.run(f"printf '{known}\\n{known}\\n' | passwd testpwduser 2>&1")
    all_output.append(f"Baseline password set: {known}")

    short   = "Ab1!xy"
    helper  = "/tmp/_tc1_passwd.sh"
    ssh.run(f"printf '#!/bin/sh\\nprintf \"%s\\\\n%s\\\\n%s\\\\n\" \"{known}\" \"$1\" \"$1\" | passwd\\n' > {helper} && chmod +x {helper}")

    cmd = f"su testpwduser -c '{helper} {short}' 2>&1"
    out3, err3, _ = ssh.run(cmd)
    combined = (out3 + " " + err3).strip()
    all_output.append(f"Attempt '{short}' (6 chars):")
    all_output.append(combined)

    ssh.run(f"rm -f {helper}")

    accepted = (
        any(k in combined.lower() for k in ["password changed", "changed by"])
        and "unchanged" not in combined.lower()
    )
    if config_ok and not accepted:
        verdict = "PASS"
        all_output.append(f"PASS: '{short}' rejected — passwd: password unchanged")
    else:
        all_output.append(f"FAIL: '{short}' accepted — PAM not enforced")

    evidence = save_evidence(tc_id, cmd, "\n".join(all_output))
    record_result(
        tc_id, tc_name,
        "Verify DUT rejects passwords shorter than 8 characters.",
        cmd, combined,
        "Short password rejected by PAM, minlen=8 in config",
        "Rejected" if verdict == "PASS" else "Accepted",
        verdict, [evidence]
    )
