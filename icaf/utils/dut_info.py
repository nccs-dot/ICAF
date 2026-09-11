import subprocess


def _resolve_key(profile, key, default=None):
    """Resolves dot-notation keys on dictionaries or custom profile objects."""
    if hasattr(profile, "get") and not isinstance(profile, dict):
        val = profile.get(key, default)
        return val if val is not None else default

    if isinstance(profile, dict):
        if key in profile:
            return profile[key]
        curr = profile
        for segment in key.split("."):
            if isinstance(curr, dict) and segment in curr:
                curr = curr[segment]
            else:
                return default
        return curr if curr is not None else default

    return default


def _resolve_list(profile, key, default=None):
    """Resolves list values whether get_list or standard dict is used."""
    if default is None:
        default = []

    if hasattr(profile, "get_list"):
        return profile.get_list(key, default)

    val = _resolve_key(profile, key, default)
    if isinstance(val, list):
        return val
    elif isinstance(val, str):
        return [item.strip() for item in val.split(",") if item.strip()]

    return default


def ssh_cmd(profile, user, ip, password, cmd):
    ssh_binary = _resolve_key(profile, "ssh.binary", "ssh")
    ssh_options = _resolve_list(profile, "ssh.connect_options", [])
    ssh_target = _resolve_key(profile, "ssh.target", "{user}@{ip}").format(
        user=user,
        ip=ip
    )

    cmd_args = [ssh_binary] + ssh_options + [ssh_target, cmd]

    # Prepend sshpass if password is provided
    if password:
        cmd_args = ["sshpass", "-p", str(password)] + cmd_args

    try:
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip() or "Unknown"
    except Exception:
        return "Unknown"


def get_dut_info(profile, user, ip, password):
    hostname_cmd = _resolve_key(profile, "dut_info.hostname_command", "hostname")
    os_release_cmd = _resolve_key(
        profile,
        "dut_info.os_release_command",
        "cat /etc/os-release"
    )
    os_hash_cmd = _resolve_key(
        profile,
        "dut_info.os_hash_command",
        "sha256sum /etc/os-release 2>/dev/null | awk '{print $1}'"
    )
    config_hash_cmd = _resolve_key(
        profile,
        "dut_info.config_hash_command",
        "sha256sum /etc/ssh/sshd_config 2>/dev/null | awk '{print $1}'"
    )

    hostname = ssh_cmd(profile, user, ip, password, hostname_cmd)
    os_release = ssh_cmd(profile, user, ip, password, os_release_cmd)
    os_hash = ssh_cmd(profile, user, ip, password, os_hash_cmd)
    config_hash = ssh_cmd(profile, user, ip, password, config_hash_cmd)

    version = "Unknown"
    for line in os_release.splitlines():
        if line.startswith("PRETTY_NAME="):
            version = line.split("=", 1)[1].strip().strip('"')
            break

    return {
        "dut_name": hostname if hostname else "Unknown",
        "dut_version": version,
        "os_hash": os_hash if os_hash else "Unknown",
        "config_hash": config_hash if config_hash else "Unknown"
    }