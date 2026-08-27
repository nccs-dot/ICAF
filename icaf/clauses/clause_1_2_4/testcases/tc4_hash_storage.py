from icaf.core.result_recorder import record_result, save_evidence


def run(ssh):
    tc_id  = "TC6"
    tc_name = "Passwords stored hashed not in plain text"
    all_output = []
    verdict    = "FAIL"
    pwd        = "TestHash@99"

    ssh.run(f"printf '{pwd}\\n{pwd}\\n' | passwd testpwduser 2>&1")
    all_output.append(f"Set password: {pwd}")

    out1, _, _ = ssh.run("grep testpwduser /etc/shadow 2>/dev/null")
    all_output.append(f"Shadow entry:\n{out1.strip()}")

    plain_found = pwd in out1
    hash_found  = any(p in out1 for p in ["$6$", "$5$", "$y$", "$2b$", "$1$"])

    out2, _, _ = ssh.run("grep testpwduser /etc/passwd 2>/dev/null")
    shadowed    = ":x:" in out2

    out3, _, _  = ssh.run(f"grep -rl '{pwd}' /etc/passwd /etc/shadow /etc/security/ 2>/dev/null | wc -l")
    plain_count = int(out3.strip()) if out3.strip().isdigit() else 0

    all_output += [
        f"Hash found ($6$) : {hash_found}",
        f"Shadowed (:x:)   : {shadowed}",
        f"Plain text found : {plain_found}",
        f"Plain in files   : {plain_count}",
    ]

    if hash_found and shadowed and not plain_found and plain_count == 0:
        verdict = "PASS"

    rep_cmd = "grep testpwduser /etc/shadow"
    evidence = save_evidence(tc_id, rep_cmd, "\n".join(all_output))
    record_result(
        tc_id, tc_name,
        "Verify passwords stored as SHA-512 hashes not plain text.",
        rep_cmd, "\n".join(all_output),
        "Hash confirmed, no plain text found",
        "Confirmed" if verdict == "PASS" else "Plain text detected",
        verdict, [evidence]
    )
