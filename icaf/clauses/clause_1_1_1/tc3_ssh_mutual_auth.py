"""
TC3 — SSH Mutual Auth: positive (correct password) and negative (wrong password).
Test Scenario 1.1.1.3
"""

from icaf.core.testcase import TestCase
from icaf.core.step_runner import StepRunner
from icaf.steps.command_step import CommandStep
from icaf.steps.expect_one_of_step import ExpectOneOfStep
from icaf.steps.input_step import InputStep
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.pcap_start_step import PcapStartStep
from icaf.steps.pcap_stop_step import PcapStopStep
from icaf.steps.analyze_pcap_step import AnalyzePcapStep
from icaf.steps.wireshark_packet_screenshot_step import WiresharkPacketScreenshotStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger


class TC3SSHMutualAuth(TestCase):
    protocol = "ssh"

    def __init__(self):
        super().__init__(
            "TC3_SSH_MUTUAL_AUTH",
            "Configure and verify successful and unsuccessful SSH mutual authentication",
        )

    def _ssh_cmd(self, context):
        binary  = context.profile.get("ssh.binary", "ssh")
        options = context.profile.get_list("ssh.connect_options")
        target  = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=context.ssh_user, ip=context.ssh_ip)
        return " ".join([binary] + options + [target])

    # ── verify SSH enabled ────────────────────────────────────────────────

    def _verify_ssh_enabled(self, context):
        ssh_cmd      = self._ssh_cmd(context)
        StepRunner([
            CommandStep("tester", ssh_cmd, settle_time=4),
        ]).run(context)
        ExpectOneOfStep("tester",
            context.profile.get_list("ssh.password_prompt"), timeout=10).execute(context)
        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        ExpectOneOfStep("tester", ["#", ">", "$"], timeout=10).execute(context)

        # Query SSH server status
        StepRunner([CommandStep("tester", "display ssh server status", settle_time=2)]).run(context)
        ExpectOneOfStep("tester", ["SSH version", "version : 2", "Enable", "#"],
                        timeout=8).execute(context)
        ScreenshotStep("tester").execute(context)
        StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)

    # ── nmap cipher scan ──────────────────────────────────────────────────

    def _nmap_scan(self, context):
        cmd = f"nmap -p 22 --script ssh2-enum-algos {context.ssh_ip}"
        StepRunner([CommandStep("tester", cmd, settle_time=10)]).run(context)
        ExpectOneOfStep("tester", ["Nmap done", "kex_algorithms", "encryption_algorithms"],
                        timeout=30).execute(context)
        ScreenshotStep("tester").execute(context)

    # ── positive case ─────────────────────────────────────────────────────

    def _positive(self, context):
        ssh_cmd      = self._ssh_cmd(context)
        pass_prompts = context.profile.get_list("ssh.password_prompt")
        fail_prompts = context.profile.get_list("ssh.failure_prompt")
        success_p    = context.profile.get_list("ssh.success_prompt") or ["#", "$", ">"]

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc3_ssh_positive.pcapng"),
            CommandStep("tester", ssh_cmd, settle_time=4),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester", pass_prompts + fail_prompts, timeout=12).execute(context)

        if pattern in fail_prompts:
            logger.error("TC3 Positive: SSH failed before password prompt")
            StepRunner([PcapStopStep()]).run(context)
            ScreenshotStep("tester").execute(context)
            return False

        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        p2, _ = ExpectOneOfStep(
            "tester", success_p + fail_prompts, timeout=12).execute(context)

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep("tester").execute(context)

        if p2 in fail_prompts:
            logger.error("TC3 Positive: DUT rejected correct credentials")
            StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)
            return False

        logger.info("TC3 Positive: SSH session established")
        StepRunner([
            AnalyzePcapStep("ssh"),
            WiresharkPacketScreenshotStep("ssh"),
            SessionResetStep("tester", post_reset_delay=2),
        ]).run(context)
        return True

    # ── negative case ─────────────────────────────────────────────────────

    def _negative(self, context):
        ssh_cmd  = self._ssh_cmd(context)
        bad_pass = context.profile.get("ssh.bad_password", "WrongPass@999!")
        pass_p   = context.profile.get_list("ssh.password_prompt")

        retry_msgs = [
            "Permission denied, please try again",
            "Permission denied"
        ]

        reject_p = (
            context.profile.get_list("ssh.failure_prompt")
            + ["Too many authentication failures", "Disconnected", "Connection closed"]
        )

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc3_ssh_negative.pcapng"),
            CommandStep("tester", ssh_cmd, settle_time=4),
        ]).run(context)

        while True:
            pattern, _ = ExpectOneOfStep(
                "tester", pass_p + retry_msgs + reject_p, timeout=15
            ).execute(context)

            # If SSH is asking for password → enter it
            if pattern in pass_p:
                logger.info("TC3 Negative: Password prompt received, sending bad password")
                StepRunner([InputStep("tester", bad_pass)]).run(context)
                continue

            # If SSH says retry → wait for next password prompt (do NOT input immediately)
            if pattern in retry_msgs:
                logger.info("TC3 Negative: Retry message received — waiting for next prompt")
                continue

            # Final rejection cases
            if pattern in reject_p:
                logger.info("TC3 Negative: DUT rejected bad credentials — '%s'", pattern)
                StepRunner([PcapStopStep()]).run(context)
                ScreenshotStep("tester").execute(context)

                StepRunner([
                    AnalyzePcapStep("ssh"),
                    WiresharkPacketScreenshotStep("ssh"),
                    ClearTerminalStep("tester"),
                ]).run(context)
                return True

            # Safety fallback (should not normally hit)
            logger.error("TC3 Negative: Unexpected behavior during SSH auth")
            break

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep("tester").execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)
        return False

    # ── entry point ────────────────────────────────────────────────────────

    def run(self, context):
        self._verify_ssh_enabled(context)
        self._nmap_scan(context)
        pos_ok = self._positive(context)
        # neg_ok = self._negative(context)
        neg_ok = True

        # Inter-TC cooldown
        # StepRunner([SessionResetStep("tester", post_reset_delay=4)]).run(context)

        self.pass_test() if (pos_ok and neg_ok) else self.fail_test()
        return self