from core.testcase import TestCase
from core.step_runner import StepRunner

from steps.command_step import CommandStep
from steps.expect_one_of_step import ExpectOneOfStep
from steps.screenshot_step import ScreenshotStep
from steps.input_step import InputStep
from steps.session_reset_step import SessionResetStep

from utils.logger import logger


class TC2SSHValidCredentials(TestCase):

    def __init__(self):
        super().__init__(
            "TC2_SSH_VALID_CREDENTIALS",
            "Tester connects to DUT via SSH with valid credentials"
        )

    def run(self, context):

        ssh_cmd = f"ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa {context.ssh_user}@{context.ssh_ip}"

        try:

            # Start SSH connection
            StepRunner([
                CommandStep("tester", ssh_cmd)
            ]).run(context)

            # Wait for SSH prompts
            pattern, _ = ExpectOneOfStep(
                "tester",
                [
                    "password",
                    "continue connecting",
                    "connection refused"
                ]
            ).execute(context)

            # Handle first-time SSH host verification
            if pattern == "continue connecting":

                StepRunner([
                    InputStep("tester", "yes")
                ]).run(context)

                pattern, _ = ExpectOneOfStep(
                    "tester",
                    ["password"]
                ).execute(context)

            # Handle connection failure
            if pattern == "connection refused":

                logger.error("SSH connection refused")

                ScreenshotStep("tester").execute(context)

                self.fail_test()
                return self

            # Send password
            StepRunner([
                InputStep("tester", context.ssh_password)
            ]).run(context)

            # Wait for successful login indicators
            pattern, _ = ExpectOneOfStep(
                "tester",
                [
                    "$",
                    "#",
                    ">",
                    "Permission denied"
                ]
            ).execute(context)

            if pattern == "Permission denied":

                logger.error("Valid SSH credentials rejected")

                ScreenshotStep("tester").execute(context)

                self.fail_test()
                return self

            # Run a command to confirm shell access
            StepRunner([
                CommandStep("tester", "whoami")
            ]).run(context)

            pattern, _ = ExpectOneOfStep(
                "tester",
                [context.ssh_user]
            ).execute(context)

            ScreenshotStep("tester").execute(context)

            logger.info("SSH login verified using command execution")

            self.pass_test()

        finally:

            StepRunner([
                SessionResetStep("tester")
            ]).run(context)

        return self