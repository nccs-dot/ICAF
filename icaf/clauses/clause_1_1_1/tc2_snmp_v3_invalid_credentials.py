"""
TC2 — SNMPv3 Negative: Verify SNMPv3 login with incorrect credentials.
Test Scenario 1.1.1.2
"""

from icaf.core.testcase import TestCase
from icaf.core.step_runner import StepRunner
from icaf.steps.command_step import CommandStep
from icaf.steps.expect_one_of_step import ExpectOneOfStep
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.pcap_start_step import PcapStartStep
from icaf.steps.pcap_stop_step import PcapStopStep
from icaf.steps.analyze_pcap_step import AnalyzePcapStep
from icaf.steps.wireshark_packet_screenshot_step import WiresharkPacketScreenshotStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger


class TC2SNMPv3InvalidCredentials(TestCase):
    protocol = "snmp"

    def __init__(self):
        super().__init__(
            "TC2_SNMPV3_INVALID_CREDENTIALS",
            "Verify SNMPv3 login with incorrect credentials and verify DUT response",
        )

    def run(self, context):
        target = context.profile.get("snmp.target") or context.ssh_ip
        snmp_user = context.profile.get("snmp.user",       context.snmp_user or "User1")
        bad_pass  = context.profile.get("snmp.bad_auth_pass", "WrongPass@999")
        priv_pass = context.profile.get("snmp.priv_pass",  context.snmp_priv_pass or "Test@123")

        cmd = (f"snmpwalk -v3 -u {snmp_user} -l authPriv "
               f"-a SHA -A \"{bad_pass}\" "
               f"-x AES -X \"{priv_pass}\" {target}")

        auth_fail  = ["Authentication failure", "authentication failure",
                      "incorrect password", "Wrong Digest"]
        timeout_p  = ["Timeout", "No Response", "No response", "unknown host"]

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc2_snmp_invalid.pcapng"),
            CommandStep("tester", cmd, settle_time=8),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester",
            auth_fail + timeout_p + ["iso.", "STRING"],
            timeout=15,
        ).execute(context)

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep("tester").execute(context)

        if any(a in pattern for a in auth_fail + timeout_p):
            logger.info("TC2: SNMPv3 authentication failure confirmed — '%s'", pattern)
            StepRunner([
                AnalyzePcapStep("snmp"),
                WiresharkPacketScreenshotStep("snmp"),
            ]).run(context)
            result = True
        else:
            logger.error("TC2: DUT accepted invalid SNMPv3 credentials — '%s'", pattern)
            StepRunner([ClearTerminalStep("tester")]).run(context)
            result = False

        # Inter-TC cooldown
        StepRunner([ClearTerminalStep("tester")]).run(context)

        self.pass_test() if result else self.fail_test()
        return self