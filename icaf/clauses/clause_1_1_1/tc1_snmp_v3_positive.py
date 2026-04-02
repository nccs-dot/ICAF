"""
TC1 — SNMPv3 Positive: Configure and verify SNMPv3 mutual authentication.
Test Scenario 1.1.1.1
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


class TC1SNMPv3Positive(TestCase):
    protocol = "snmp"

    def __init__(self):
        super().__init__(
            "TC1_SNMPV3_POSITIVE",
            "Configure and verify SNMPv3 protocol mutual authentication",
        )

    # ── helpers ────────────────────────────────────────────────────────────

    def _snmpget(self, version, community, target):
        oid = "1.3.6.1.2.1.1.3.0"   # sysUpTime (lightweight, always present)

        if version in ("1", "2c"):
            return f"snmpget -v{version} -c {community} {target} {oid}"

    # ── step 1: verify SNMPv1/v2c disabled ────────────────────────────────

    def _verify_legacy_disabled(self, context):
        target = context.profile.get("snmp.target") or context.ssh_ip
        community = context.profile.get("snmp.community", context.snmp_community or "User1")
        timeout_patterns = ["Timeout", "No Response", "No response"]
        ok = True

        for ver in ("1", "2c"):
            StepRunner([
                PcapStartStep(interface="eth0", filename=f"tc1_snmp_v{ver}.pcapng"),
                CommandStep("tester", self._snmpget(ver, community, target), settle_time=3),
            ]).run(context)

            pattern, _ = ExpectOneOfStep(
                "tester",
                timeout_patterns + ["iso.", "STRING"],
                timeout=12,
            ).execute(context)

            StepRunner([PcapStopStep()]).run(context)
            ScreenshotStep("tester").execute(context)
            StepRunner([ClearTerminalStep("tester")]).run(context)

            if any(t in pattern for t in timeout_patterns):
                logger.info("TC1: SNMPv%s correctly disabled — no response", ver)
                StepRunner([
                    AnalyzePcapStep(f"udp.port == 161 && ip.addr == {target}"),
                    WiresharkPacketScreenshotStep(),
                ]).run(context)
            else:
                logger.warning("TC1: SNMPv%s returned a response — may not be disabled", ver)
                ok = False

        return ok

    # ── step 2: configure SNMPv3 on DUT ───────────────────────────────────

    def _configure_snmpv3(self, context):
        
        # New profile-driven SSH command
        ssh_base = context.profile.get("ssh.base", "ssh")
        ssh_options = context.profile.get_list("ssh.connect_options")
        ssh_target = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=context.ssh_user,
            ip=context.ssh_ip
        )

        ssh_cmd = " ".join([ssh_base, *ssh_options, ssh_target])

        StepRunner([CommandStep("tester", ssh_cmd)]).run(context)
        ExpectOneOfStep("tester", context.profile.get_list("ssh.password_prompt")).execute(context)
        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        ExpectOneOfStep("tester", ["#", ">", "$"], timeout=10).execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)


        dut_cmds = context.profile.get_list("snmp.config_commands")

        for cmd in dut_cmds:
            StepRunner([CommandStep("tester", cmd, settle_time=5)]).run(context)
            ExpectOneOfStep("tester", ["#", ">", "$", "successfully", "saved", "Y/N"],
                            timeout=10).execute(context)

        ScreenshotStep("tester").execute(context)
        # Disconnect from DUT config session before running SNMP walk
        StepRunner([
            SessionResetStep("tester", post_reset_delay=2),
            SessionResetStep("tester", post_reset_delay=2)
        ]).run(context)
        logger.info("TC1: SNMPv3 configuration complete")

    # ── step 3: valid SNMPv3 walk ─────────────────────────────────────────

    def _valid_snmpv3_walk(self, context):
        target = context.profile.get("snmp.target") or context.ssh_ip
        snmp_user = context.profile.get("snmp.user",      context.snmp_user or "User1")
        auth_pass = context.profile.get("snmp.auth_pass", context.snmp_auth_pass or "Test@123")
        priv_pass = context.profile.get("snmp.priv_pass", context.snmp_priv_pass or "Test@123")

        opts = (f"-v3 -u {snmp_user} -l authPriv "
                f"-a SHA -A \"{auth_pass}\" -x AES -X \"{priv_pass}\"")
        cmd = f"snmpwalk {opts} {target} 1.3.6.1.2.1.1.3.0 | head -20"

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc1_snmpv3_valid.pcapng"),
            CommandStep("tester", cmd, settle_time=8),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester",
            ["iso.", "STRING", "INTEGER", "Timeticks", "OID", "Timeout", "Authentication failure", "Error"],
            timeout=15,
        ).execute(context)

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep("tester").execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)

        if any(f in pattern for f in ["Timeout", "Authentication failure", "Error"]):
            logger.error("TC1: valid SNMPv3 walk failed — %s", pattern)
            StepRunner([ClearTerminalStep("tester")]).run(context)
            return False

        logger.info("TC1: valid SNMPv3 walk succeeded")
        StepRunner([
            AnalyzePcapStep("snmp || udp.port == 161 || udp.port == 162"),
            WiresharkPacketScreenshotStep(),
        ]).run(context)
        return True

    # ── step 4: weak algorithm user rejected ──────────────────────────────

    def _weak_algo_rejected(self, context):
        target = context.profile.get("snmp.target") or context.ssh_ip
        auth_pass = context.profile.get("snmp.auth_pass", context.snmp_auth_pass or "Test@123")
        priv_pass = context.profile.get("snmp.priv_pass", context.snmp_priv_pass or "Test@123")

        opts = (f"-v3 -u User1 -l authPriv "
                f"-a MD5 -A \"{auth_pass}\" -x DES -X \"{priv_pass}\"")
        cmd = f"snmpwalk {opts} {target} 1.3.6.1.2.1.1.3.0 | head -20"

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc1_snmpv3_weak.pcapng"),
            CommandStep("tester", cmd, settle_time=8),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester",
            ["Timeout", "No Response", "No response", "iso.", "STRING", "unknown host", "Authentication failure"],
            timeout=15,
        ).execute(context)

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep("tester").execute(context)

        if any(s in pattern for s in ["iso.", "STRING"]):
            logger.error("TC1: DUT accepted weak-algorithm user2 — FAIL")
            StepRunner([ClearTerminalStep("tester")]).run(context)
            return False

        logger.info("TC1: weak-algorithm user2 correctly rejected")
        StepRunner([
            AnalyzePcapStep("snmp || udp.port == 161 || udp.port == 162"),
            WiresharkPacketScreenshotStep(),
        ]).run(context)
        return True

    # ── entry point ────────────────────────────────────────────────────────

    def run(self, context):
        legacy_ok  = self._verify_legacy_disabled(context)
        self._configure_snmpv3(context)
        valid_ok   = self._valid_snmpv3_walk(context)
        weak_ok    = self._weak_algo_rejected(context)

        # Inter-TC cooldown
        # StepRunner([SessionResetStep("tester", post_reset_delay=4)]).run(context)

        if legacy_ok and valid_ok and weak_ok:
            self.pass_test()
        else:
            logger.warning("TC1 breakdown — legacy=%s valid=%s weak=%s",
                           legacy_ok, valid_ok, weak_ok)
            self.fail_test()
        return self