"""
TC4 — SSH Correct Public Key: configure and verify public key authentication.
Test Scenario 1.1.1.4
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


class TC4SSHCorrectPublicKey(TestCase, SSHMixin):

    def __init__(self):
        super().__init__(
            "TC4_SSH_CORRECT_PUBLIC_KEY",
            "Configure and verify SSH login using the correct public key",
        )

    # ── generate ECDSA key pair ────────────────────────────────────────────

    def _generate_key(self, context):
        key_path = context.profile.get("ssh.pubkey.key_path", "~/.ssh/id_ecdsaa")

        StepRunner([ClearTerminalStep("tester")]).run(context)

        StepRunner([
            CommandStep("tester", f"ssh-keygen -t ecdsa -b 256 -f {key_path} -N ''",
                        settle_time=4, capture_evidence=False),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester",
            ["Overwrite (y/n)?", "already exists", "Your public key", "SHA256"],
            timeout=10,
        ).execute(context)

        if "Overwrite" in pattern or "already exists" in pattern:
            logger.info("TC4: Key already exists, overwriting")
            StepRunner([InputStep("tester", "y", capture_evidence=True)]).run(context)
            ExpectOneOfStep("tester", ["Your public key", "SHA256"], timeout=10).execute(context)

        StepRunner([ClearTerminalStep("tester")]).run(context)

        StepRunner([CommandStep("tester", f"cat {key_path}.pub", settle_time=2)]).run(context)
        ExpectOneOfStep("tester", ["ecdsa-sha2", "ssh-"], timeout=6).execute(context)

        ScreenshotStep("tester").execute(context)

        StepRunner([ClearTerminalStep("tester")]).run(context)


        logger.info("TC4: ECDSA key pair generated")

    # ── export public key to DUT via SFTP ─────────────────────────────────

    def _export_pubkey(self, context):
        key_path      = context.profile.get("ssh.pubkey.key_path", "~/.ssh/id_ecdsaa")
        expanded_path = os.path.expanduser(f"{key_path}.pub")
        remote_path   = context.profile.get("ssh.pubkey.sftp_remote_path", "id_ecdsaa.pub")

        self.sftp_upload(context, expanded_path, remote_path)

        ScreenshotStep("tester").execute(context)

        StepRunner([ClearTerminalStep("tester")]).run(context)

        logger.info("TC4: Public key exported to DUT")

    # ── create user + configure authorized_keys in ONE SSH session ─────────

    def _setup_dut(self, context):
        """
        Open a single SSH session to the DUT, become root once, then run
        both user-creation and authorized_keys configuration commands before
        closing.  This replaces the two separate sessions that _create_user
        and _configure_dut previously opened independently.
        """
        username    = context.profile.get("ssh.pubkey.dut_user",          "Test5")
        password    = context.profile.get("ssh.pubkey.dut_user_password",  "Test@1234")
        role        = context.profile.get("ssh.pubkey.dut_user_role",      "network-operator")
        pubkey_name = context.profile.get("ssh.pubkey.dut_key_name",       "PUBBKEY")

        create_commands  = context.profile.get_list("user_mgmt.create_commands")
        config_commands  = context.profile.get_list("ssh.pubkey.configure_commands")

        self.ssh_open_session(context)
        self.ssh_become_root(context, root_password=context.ssh_password)

        # ── user creation ──────────────────────────────────────────────────
        self.ssh_run_commands(
            context,
            create_commands,
            fmt_kwargs={
                "username":     username,
                "password":     password,
                "role":         role,
                "service_type": "ssh",
            },
        )

        ScreenshotStep("tester").execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)
        logger.info("TC4: User '%s' created on DUT", username)

        # ── authorized_keys configuration (same session, still root) ───────
        self.ssh_run_formatted_commands(
            context,
            config_commands,
            fmt_kwargs={
                "dut_key_name": pubkey_name,
                "dut_user":     username,
                "ssh_user":     context.ssh_user,
            },
        )

        ScreenshotStep("tester").execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)
        logger.info("TC4: authorized_keys configured on DUT for user '%s'", username)

        # ── single close (su shell + SSH shell) ───────────────────────────
        self.ssh_close_session(context)   # exits su -
        self.ssh_close_session(context)   # exits SSH

    # ── delete the pubkey test user from the DUT ──────────────────────────

    def _teardown_dut(self, context):
        username        = context.profile.get("ssh.pubkey.dut_user", "Test5")
        delete_commands = context.profile.get_list("user_mgmt.delete_commands")

        StepRunner([ClearTerminalStep("tester")]).run(context)

        self.ssh_open_session(context)
        self.ssh_become_root(context, root_password=context.ssh_password)

        self.ssh_run_commands(
            context,
            delete_commands,
            fmt_kwargs={"username": username},
        )

        StepRunner([ClearTerminalStep("tester")]).run(context)
        ScreenshotStep("tester").execute(context)

        self.ssh_close_session(context)   # exits su -
        self.ssh_close_session(context)   # exits SSH

        logger.info("TC4: User '%s' deleted from DUT", username)

    # ── attempt login with the correct public key ──────────────────────────

    def _login_with_pubkey(self, context):
        key_path    = context.profile.get("ssh.pubkey.key_path", "~/.ssh/id_ecdsaa")
        pubkey_user = context.profile.get("ssh.pubkey.dut_user", "Test5")

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc4_ssh_pubkey_correct.pcapng"),
        ]).run(context)

        success, pattern = self.ssh_open_pubkey_session(
            context, key_path=key_path, remote_user=pubkey_user
        )

        StepRunner([PcapStopStep()]).run(context)

        ScreenshotStep("tester").execute(context)

        if success:
            logger.info("TC4: Public key login successful")
            StepRunner([
                AnalyzePcapStep("ssh"),
                WiresharkPacketScreenshotStep("ssh"),
            ]).run(context)
            CommandStep("tester", "exit", settle_time=4, capture_evidence=False)
            
            return True

        self.log_ssh_failure(context, "TC4", pattern)
        return False

    # ── entry point ────────────────────────────────────────────────────────

    def run(self, context):
        self._generate_key(context)
        self._export_pubkey(context)
        self._setup_dut(context)
        success = self._login_with_pubkey(context)

        try:
            self._teardown_dut(context)
        except Exception:
            logger.warning("TC4: Could not delete user '%s' during cleanup",
                           context.profile.get("ssh.pubkey.dut_user", "Test5"))

        StepRunner([SessionResetStep("tester", post_reset_delay=4)]).run(context)

        self.pass_test() if success else self.fail_test()
        return self