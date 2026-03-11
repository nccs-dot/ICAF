from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.command_step import CommandStep
from steps.screenshot_step import ScreenshotStep
from steps.clear_terminal_step import ClearTerminalStep


class TC9SNMPv3AuthPriv(TestCase):

    def __init__(self):

        super().__init__(
            "TC9_SNMPV3_AUTHPRIV",
            "Verify SNMPv3 authPriv authentication works"
        )

    def run(self, context):

        cmd = (
            f"snmpwalk -v3 -u {context.snmp_user} "
            f"-l authPriv "
            f"-a SHA -A {context.snmp_auth_pass} "
            f"-x AES -X {context.snmp_priv_pass} "
            f"{context.ssh_ip}"
        )

        tm = context.terminal_manager

        StepRunner([
            ClearTerminalStep("dut"),
            CommandStep("dut", cmd)
        ]).run(context)

        output = tm.capture_output("dut")

        if "iso." in output:

            ScreenshotStep("dut").execute(context)

            self.pass_test()

            return self

        ScreenshotStep("dut").execute(context)

        self.fail_test()

        return self