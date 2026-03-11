import argparse
import sys
from datetime import datetime
from scapy.all import IP, ICMP, IPv6, send
from scapy.layers.inet6 import (
    ICMPv6EchoRequest, ICMPv6EchoReply, ICMPv6DestUnreach,
    ICMPv6PacketTooBig, ICMPv6TimeExceeded, ICMPv6ParamProblem,
    ICMPv6ND_RS, ICMPv6ND_RA, ICMPv6ND_NS, ICMPv6ND_NA, ICMPv6ND_Redirect
)

def main():
    parser = argparse.ArgumentParser(description="TCAF ICMP Forger for Clause 1.10.1")
    parser.add_argument("--ipv4", help="Target IPv4 Address")
    parser.add_argument("--ipv6", help="Target IPv6 Address")
    parser.add_argument("--logfile", help="Path to save the execution log")
    args = parser.parse_args()

    if not args.ipv4 and not args.ipv6:
        print("[-] Error: Must provide at least one target IP (--ipv4 or --ipv6)")
        sys.exit(1)

    ipv4_types = [0, 3, 5, 8, 11, 12, 13, 14]
    ipv6_types = {
        128: ICMPv6EchoRequest, 129: ICMPv6EchoReply, 1: ICMPv6DestUnreach,
        2: ICMPv6PacketTooBig, 3: ICMPv6TimeExceeded, 4: ICMPv6ParamProblem,
        133: ICMPv6ND_RS, 134: ICMPv6ND_RA, 135: ICMPv6ND_NS,
        136: ICMPv6ND_NA, 137: ICMPv6ND_Redirect
    }

    log = open(args.logfile, "w") if args.logfile else open("/dev/null", "w")
    log.write(f"=== ICMP Forge Execution Log ===\nExecution Time: {datetime.now()}\n\n")

    if args.ipv4:
        print(f"[*] Starting IPv4 ICMP generation to {args.ipv4}...")
        for t in ipv4_types:
            send(IP(dst=args.ipv4)/ICMP(type=t), verbose=0)
            msg = f"[{datetime.now().strftime('%H:%M:%S')}] [+] Sent IPv4 ICMP Type {t}\n"
            print(msg.strip())
            log.write(msg)

    if args.ipv6:
        print(f"\n[*] Starting IPv6 ICMP generation to {args.ipv6}...")
        for t, icmp6_class in ipv6_types.items():
            send(IPv6(dst=args.ipv6)/icmp6_class(), verbose=0)
            msg = f"[{datetime.now().strftime('%H:%M:%S')}] [+] Sent IPv6 ICMP Type {t}\n"
            print(msg.strip())
            log.write(msg)

    log.close()
    print("\n[*] ICMP generation complete.")

if __name__ == "__main__":
    main()
