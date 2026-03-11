from core.testcase import TestCase
from core.step_runner import StepRunner

from steps.command_step import CommandStep
from steps.expect_one_of_step import ExpectOneOfStep
from steps.screenshot_step import ScreenshotStep
from steps.input_step import InputStep
from steps.pcap_start_step import PcapStartStep
from steps.pcap_stop_step import PcapStopStep
from steps.analyze_pcap_step import AnalyzePcapStep
from steps.wireshark_packet_screenshot_step import WiresharkPacketScreenshotStep

from utils.logger import logger


class TC1SSHFirstConnection(TestCase):

    def __init__(self):

        super().__init__(
            "TC1_MUTUAL_AUTHENTICATION",
            "SSH first connection mutual authentication"
        )

    def run(self, context):

        ssh_cmd = f"ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa {context.ssh_user}@{context.ssh_ip}"

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc1_ssh_auth.pcapng"),
            CommandStep("tester", ssh_cmd)
        ]).run(context)

        pattern, output = ExpectOneOfStep(
            "tester",
            [
                "continue connecting",
                "password",
                "connection refused"
            ]
        ).execute(context)

        # fingerprint case
        if pattern == "continue connecting":

            logger.info("SSH fingerprint prompt detected")

            StepRunner([
                InputStep("tester", "yes")
            ]).run(context)

            pattern, output = ExpectOneOfStep(
                "tester",
                ["password"]
            ).execute(context)

        # password case
        if pattern == "password":

            logger.info("Password prompt detected")

            StepRunner([
                InputStep("tester", context.ssh_password),
                PcapStopStep()
            ]).run(context)

            StepRunner([
                AnalyzePcapStep("ssh")
            ]).run(context)

            StepRunner([
                WiresharkPacketScreenshotStep()
            ]).run(context)

            ScreenshotStep("tester").execute(context)

            self.pass_test()

            return self

        # connection failure
        if pattern == "connection refused":

            logger.error("SSH connection refused")

            ScreenshotStep("tester").execute(context)

            self.fail_test()

            return self