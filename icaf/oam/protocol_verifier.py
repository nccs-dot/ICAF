import subprocess


def run_tcp_scan(ip):
    cmd = ["nmap", "-sV", "-Pn", ip]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.lower()

def run_udp_scan(ip):
    # Target SNMP specifically to keep it fast
    cmd = ["nmap", "-sU", "-p", "161", "-Pn", ip]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.lower()

def parse_services(nmap_output):
    services = set()

    for line in nmap_output.splitlines():
        if ("tcp" in line or "udp" in line) and "open" in line:
            parts = line.split()

            if len(parts) >= 3:
                service = parts[2]
                services.add(service.lower())

    return services

SERVICE_TO_PROTOCOL = {
    "ssh": "ssh",
    "telnet": "telnet",
    "snmp": "snmp",
    "http": "http",
    "https": "https",
    "ssl/http": "https",
    "http-proxy": "http",
    "grpc": "grpc",
    "unknown": None
}

def verify_protocols(ip, expected_protocols):

    tcp_output = run_tcp_scan(ip)
    udp_output = run_udp_scan(ip)

    tcp_services = parse_services(tcp_output)
    udp_services = parse_services(udp_output)

    all_services = tcp_services.union(udp_services)

    SERVICE_TO_PROTOCOL = {
        "ssh": "ssh",
        "telnet": "telnet",
        "snmp": "snmp",
        "http": "http",
        "https": "https",
        "ssl/http": "https",
        "http-proxy": "http",
        "grpc": "grpc",
    }

    detected_protocols = set()

    for service in all_services:
        proto = SERVICE_TO_PROTOCOL.get(service)
        if proto:
            detected_protocols.add(proto)

    verified = [
        proto for proto in expected_protocols
        if proto in detected_protocols
    ]

    return verified