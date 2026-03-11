from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.command_step import CommandStep
from steps.screenshot_step import ScreenshotStep
from steps.clear_terminal_step import ClearTerminalStep

class TC7SNMPv1Disabled(TestCase):

    def __init__(self):

        super().__init__(
            "TC7_SNMPV1_DISABLED",
            "Verify SNMPv1 is not supported"
        )

    def run(self, context):

        cmd = f"snmpwalk -v1 -c public {context.ssh_ip}"

        tm = context.terminal_manager

        StepRunner([
            ClearTerminalStep("dut"),
            CommandStep("dut", cmd)
        ]).run(context)

        output = tm.capture_output("dut")

        if "Timeout" in output or "No Response" in output:

            ScreenshotStep("dut").execute(context)

            self.pass_test()

            return self

        ScreenshotStep("dut").execute(context)

        self.fail_test()

        return self