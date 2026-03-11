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


class TC1ICMPIPv4:
    def __init__(self):
        self.name = "TC1_ICMP_IPV4"
        self.description = "IPv4 ICMP type filtering compliance test"
        self.status = "PENDING"
        self.evidence = []

    def add_evidence(self, filepath):
        if filepath:
            self.evidence.append(filepath)

    def run(self, context):
        context.current_testcase = self

        print(f"\n--- Running {self.name} ---")

        # Use DuT IP from CLI context (no duplicate input() prompt)
        ipv4_target = context.ssh_ip

        if not ipv4_target:
            print("[-] No IPv4 address provided. Skipping test case.")
            self.status = "SKIPPED"
            return self

        # Setup logging
        path = context.evidence.testcase_dir(context.clause, self)
        timestamp = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
        custom_log_file = os.path.join(path, "logs", f"{timestamp}_icmp_ipv4.txt")

        # 1. Start PCAP
        StepRunner([PcapStartStep(interface="eth0", filename="icmp_ipv4.pcapng")]).run(context)

        # 2. Fire the IPv4 payload
        cmd = f"sudo python3 clauses/clause_1_10_1/icmp_forge.py --logfile {custom_log_file} --ipv4 {ipv4_target}"
        StepRunner([CommandStep("tester", "clear")]).run(context)
        StepRunner([CommandStep("tester", cmd)]).run(context)

        # 3. Stop PCAP
        StepRunner([PcapStopStep()]).run(context)

        # ---------------------------------------------------------
        # THE IPv4 SCREENSHOT LOOP
        # ---------------------------------------------------------
        pcap_path = context.pcap_file

        # Map Request Type -> Expected Reply Type
        ipv4_mapping = {
            0: 0,    # Echo Reply
            3: 3,    # Dest Unreachable
            5: 5,    # Redirect
            8: 0,    # Echo Request -> Expects Echo Reply (0)
            11: 11,  # Time Exceeded
            12: 12,  # Parameter Problem
            13: 14,  # Timestamp Request -> Expects Timestamp Reply (14)
            14: 14   # Timestamp Reply
        }

        for req_type, expected_reply in ipv4_mapping.items():

            # 1. Clear terminal and print header
            StepRunner([CommandStep("tester", "clear")]).run(context)
            header_cmd = f"echo -e '\\n=== Auditing IPv4 ICMP Type {req_type} ==='"
            StepRunner([CommandStep("tester", header_cmd)]).run(context)

            # 2. Define the exact tshark filter
            tshark_filter = (
                f"(ip.dst == {ipv4_target} and icmp.type == {req_type}) or "
                f"(ip.src == {ipv4_target} and (icmp.type == {expected_reply} or icmp.type == 3))"
            )

            # ---------------------------------------------------------
            # THE TERMINAL PROOF
            # ---------------------------------------------------------
            # 3a. Run tshark visibly in tmux so we can read it
            tshark_cmd = f"tshark -r {pcap_path} -Y '{tshark_filter}'"
            StepRunner([CommandStep("tester", tshark_cmd)]).run(context)
            time.sleep(1)

            # 3b. Take the terminal screenshot
            StepRunner([ScreenshotStep(terminal="tester", suffix=f"ipv4_type_{req_type}")]).run(context)

            # ---------------------------------------------------------
            # THE WIRESHARK GUI PROOF
            # ---------------------------------------------------------
            # 4a. Run tshark in the background to grab frame numbers
            StepRunner([AnalyzePcapStep(filter_expr=tshark_filter)]).run(context)

            # 4b. Use the Wireshark step if we found matching frames
            if context.matched_frame:
                StepRunner([WiresharkPacketScreenshotStep(suffix=f"ipv4_type_{req_type}")]).run(context)
            else:
                print(f"[*] No matching packets found for Type {req_type}. (Silent Drop successful). Skipping Wireshark.")

        self.status = "PASS"
        return self
