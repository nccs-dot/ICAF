"""
TC5 — SSH Incorrect Public Key
Test Scenario 1.1.1.5
"""

import os

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
from .ssh_mixin import SSHMixin


class TC5SSHIncorrectPublicKey(TestCase, SSHMixin):

    def __init__(self):
        super().__init__(
            "TC5_SSH_INCORRECT_PUBLIC_KEY",
            "Verify SSH login fails with unregistered public key",
        )

    # ── generate WRONG key ───────────────────────────────────────────────

    def _generate_wrong_key(self, context):
        key_path = context.profile.get("ssh.pubkey.wrong_key_path", "~/.ssh/wrong_keyy")

        StepRunner([ClearTerminalStep("tester")]).run(context)

        StepRunner([
            CommandStep("tester",
                        f"ssh-keygen -t ecdsa -b 256 -f {key_path} -N ''",
                        settle_time=4,
                        capture_evidence=False),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester",
            ["Overwrite (y/n)?", "already exists", "Your public key", "SHA256"],
            timeout=10,
        ).execute(context)

        if "Overwrite" in pattern or "already exists" in pattern:
            logger.info("TC5: Overwriting existing wrong key")
            StepRunner([InputStep("tester", "y")]).run(context)
            ExpectOneOfStep("tester", ["Your public key", "SHA256"], timeout=10).execute(context)

        ScreenshotStep("tester").execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)

        logger.info("TC5: Wrong key generated")

    # ── export WRONG key (same as TC4) ────────────────────────────────────

    def _export_wrong_key(self, context):
        key_path      = context.profile.get("ssh.pubkey.wrong_key_path", "~/.ssh/wrong_keyy")
        expanded_path = os.path.expanduser(f"{key_path}.pub")
        remote_path   = "wrong_key.pub"

        self.sftp_upload(context, expanded_path, remote_path)

        ScreenshotStep("tester").execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)

        logger.info("TC5: Wrong key exported to DUT (NOT authorized)")

    # ── setup DUT (WITHOUT adding key to authorized_keys) ────────────────

    def _setup_dut_without_authorization(self, context):
        username = context.profile.get("ssh.pubkey.dut_user", "Test5")
        password = context.profile.get("ssh.pubkey.dut_user_password", "Test@1234")
        role     = context.profile.get("ssh.pubkey.dut_user_role", "network-operator")

        create_commands = context.profile.get_list("user_mgmt.create_commands")

        self.ssh_open_session(context)
        self.ssh_become_root(context, root_password=context.ssh_password)

        # create user ONLY (no pubkey config)
        self.ssh_run_commands(
            context,
            create_commands,
            fmt_kwargs={
                "username": username,
                "password": password,
                "role": role,
                "service_type": "ssh",
            },
        )

        ScreenshotStep("tester").execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)

        logger.info("TC5: User created WITHOUT authorized_keys")

        self.ssh_close_session(context)
        self.ssh_close_session(context)

    # ── login attempt with WRONG key ─────────────────────────────────────

    def _login_with_wrong_key(self, context):
        key_path    = context.profile.get("ssh.pubkey.wrong_key_path", "~/.ssh/wrong_keyy")
        pubkey_user = context.profile.get("ssh.pubkey.dut_user", "Test5")

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc5_ssh_wrong_key.pcapng"),
        ]).run(context)

        success, pattern = self.ssh_open_pubkey_session(
            context,
            key_path=key_path,
            remote_user=pubkey_user
        )

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep("tester").execute(context)

        if success:
            logger.error("TC5: WRONG key accepted — FAIL")
            return False

        self.log_ssh_failure(context, "TC5", pattern)

        StepRunner([
            AnalyzePcapStep("ssh"),
            WiresharkPacketScreenshotStep("ssh"),
        ]).run(context)

        return True

    # ── teardown (same as TC4) ───────────────────────────────────────────

    def _teardown_dut(self, context):
        username = context.profile.get("ssh.pubkey.dut_user", "Test5")

        self.dut_delete_local_user(context, username=username)

        ScreenshotStep("tester").execute(context)
        logger.info("TC5: User '%s' deleted", username)

    # ── entry point ──────────────────────────────────────────────────────

    def run(self, context):
        self._generate_wrong_key(context)
        self._export_wrong_key(context)
        self._setup_dut_without_authorization(context)

        success = self._login_with_wrong_key(context)

        try:
            self._teardown_dut(context)
        except Exception:
            logger.warning("TC5: Cleanup failed")

        StepRunner([
            SessionResetStep("tester", post_reset_delay=4)
        ]).run(context)

        self.pass_test() if success else self.fail_test()
        return self