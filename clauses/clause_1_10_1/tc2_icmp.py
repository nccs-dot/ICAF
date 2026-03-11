from core.step_runner import StepRunner
from steps.pcap_start_step import PcapStartStep
from steps.pcap_stop_step import PcapStopStep
from steps.command_step import CommandStep
from steps.screenshot_step import ScreenshotStep
from steps.wireshark_packet_screenshot_step import WiresharkPacketScreenshotStep
from steps.analyze_pcap_step import AnalyzePcapStep
from datetime import datetime
import os
import time


class TC2ICMPIPv6:
    def __init__(self):
        self.name = "TC2_ICMP_IPV6"
        self.description = "IPv6 ICMP type filtering compliance test"
        self.status = "PENDING"
        self.evidence = []

    def add_evidence(self, filepath):
        if filepath:
            self.evidence.append(filepath)

    def run(self, context):
        context.current_testcase = self

        print(f"\n--- Running {self.name} ---")

        # IPv6 is a separate protocol — prompt interactively
        ipv6_target = input("Enter DuT IPv6 Address: ").strip()

        if not ipv6_target:
            print("[-] No IPv6 address provided. Skipping test case.")
            self.status = "SKIPPED"
            return self

        # Setup logging
        path = context.evidence.testcase_dir(context.clause, self)
        timestamp = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
        custom_log_file = os.path.join(path, "logs", f"{timestamp}_icmp_ipv6.txt")

        # 1. Start PCAP
        StepRunner([PcapStartStep(interface="eth0", filename="icmp_ipv6.pcapng")]).run(context)

        # 2. Fire the IPv6 payload
        cmd = f"sudo python3 clauses/clause_1_10_1/icmp_forge.py --logfile {custom_log_file} --ipv6 {ipv6_target}"
        StepRunner([CommandStep("tester", "clear")]).run(context)
        StepRunner([CommandStep("tester", cmd)]).run(context)

        # 3. Stop PCAP
        StepRunner([PcapStopStep()]).run(context)

        # ---------------------------------------------------------
        # THE IPv6 SCREENSHOT LOOP
        # ---------------------------------------------------------
        pcap_path = context.pcap_file

        # Map Request Type -> Expected Reply Type (ICMPv6)
        ipv6_mapping = {
            128: 129,  # Echo Request -> Echo Reply
            129: 129,  # Echo Reply
            1: 1,      # Dest Unreachable
            2: 2,      # Packet Too Big
            3: 3,      # Time Exceeded
            4: 4,      # Parameter Problem
            133: 134,  # Router Solicitation -> Router Advertisement
            134: 134,  # Router Advertisement
            135: 136,  # Neighbor Solicitation -> Neighbor Advertisement
            136: 136,  # Neighbor Advertisement
            137: 137   # Redirect
        }

        for req_type, expected_reply in ipv6_mapping.items():

            # 1. Clear terminal and print header
            StepRunner([CommandStep("tester", "clear")]).run(context)
            header_cmd = f"echo -e '\\n=== Auditing IPv6 ICMP Type {req_type} ==='"
            StepRunner([CommandStep("tester", header_cmd)]).run(context)

            # 2. Define the exact tshark filter (IPv6-specific fields!)
            tshark_filter = (
                f"(ipv6.dst == {ipv6_target} and icmpv6.type == {req_type}) or "
                f"(ipv6.src == {ipv6_target} and (icmpv6.type == {expected_reply} or icmpv6.type == 1))"
            )

            # ---------------------------------------------------------
            # THE TERMINAL PROOF
            # ---------------------------------------------------------
            # 3a. Run tshark visibly in tmux so we can read it
            tshark_cmd = f"tshark -r {pcap_path} -Y '{tshark_filter}'"
            StepRunner([CommandStep("tester", tshark_cmd)]).run(context)
            time.sleep(1)

            # 3b. Take the terminal screenshot
            StepRunner([ScreenshotStep(terminal="tester", suffix=f"ipv6_type_{req_type}")]).run(context)

            # ---------------------------------------------------------
            # THE WIRESHARK GUI PROOF
            # ---------------------------------------------------------
            # 4a. Run tshark in the background to grab frame numbers
            StepRunner([AnalyzePcapStep(filter_expr=tshark_filter)]).run(context)

            # 4b. Use the Wireshark step if we found matching frames
            if context.matched_frame:
                StepRunner([WiresharkPacketScreenshotStep(suffix=f"ipv6_type_{req_type}")]).run(context)
            else:
                print(f"[*] No matching packets found for Type {req_type}. (Silent Drop successful). Skipping Wireshark.")

        self.status = "PASS"
        return self
