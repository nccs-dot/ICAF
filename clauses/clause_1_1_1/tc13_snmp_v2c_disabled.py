from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.command_step import CommandStep
from steps.screenshot_step import ScreenshotStep
from steps.clear_terminal_step import ClearTerminalStep

class TC8SNMPv2Disabled(TestCase):

    def __init__(self):

        super().__init__(
            "TC8_SNMPV2_DISABLED",
            "Verify SNMPv2c is not supported"
        )

    def run(self, context):

        cmd = f"snmpwalk -v2c -c public {context.ssh_ip}"

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