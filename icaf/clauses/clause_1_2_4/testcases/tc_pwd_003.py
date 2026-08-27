from icaf.core.result_recorder import record_result, save_evidence


def run(ssh):
    tc_id  = "TC2"
    tc_name = "Accept password longer than 8 characters"
    pwd = "SecurePass@2024"
    cmd = f"printf '{pwd}\\n{pwd}\\n' | passwd testpwduser 2>&1"
    out, err, code = ssh.run(cmd)
    combined = (out + " " + err).strip()

    bad      = any(k in combined.lower() for k in ["bad password", "too short", "unchanged"])
    accepted = not bad and ("changed" in combined.lower() or code == 0)
    verdict  = "PASS" if accepted else "FAIL"

    evidence = save_evidence(tc_id, cmd, combined)
    record_result(
        tc_id, tc_name,
        "Verify DUT accepts a valid password longer than 8 characters.",
        cmd, combined,
        "Password accepted",
        "Accepted" if accepted else "Rejected",
        verdict, [evidence]
    )
