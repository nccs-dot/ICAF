from core.testcase import TestCase
from core.step_runner import StepRunner

from steps.command_step import CommandStep
from steps.expect_one_of_step import ExpectOneOfStep
from steps.screenshot_step import ScreenshotStep
from steps.input_step import InputStep
from steps.session_reset_step import SessionResetStep
from steps.clear_terminal_step import ClearTerminalStep

from utils.logger import logger


class TC3SSHInvalidCredentials(TestCase):

    def __init__(self):

        super().__init__(
            "TC3_SSH_INVALID_CREDENTIALS",
            "Tester should not connect with invalid SSH credentials"
        )

    def run(self, context):

        ssh_cmd = f"ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa {context.ssh_user}@{context.ssh_ip}"

        try:

            StepRunner([
                CommandStep("tester", ssh_cmd)
            ]).run(context)

            pattern, _ = ExpectOneOfStep(
                "tester",
                [
                    "password",
                    "continue connecting",
                    "connection refused"
                ]
            ).execute(context)

            if pattern == "continue connecting":

                StepRunner([
                    InputStep("tester", "yes")
                ]).run(context)

                pattern, _ = ExpectOneOfStep(
                    "tester",
                    ["password"]
                ).execute(context)

            if pattern == "connection refused":

                logger.error("SSH connection refused")

                ScreenshotStep("tester").execute(context)

                self.fail_test()
                return self

            # Attempt wrong password multiple times (synchronized)
            for attempt in range(3):

                StepRunner([
                    InputStep("tester", "wrongpassword")
                ]).run(context)

                pattern, output = ExpectOneOfStep(
                    "tester",
                    [
                        "Permission denied",
                        "password",
                        "Connection closed",
                        "$",
                        "#"
                    ]
                ).execute(context)

                # If shell prompt appears, login succeeded unexpectedly
                if pattern in ["$", "#"]:

                    logger.error("SSH login succeeded with invalid credentials")

                    ScreenshotStep("tester").execute(context)

                    self.fail_test()

                    return self

                # If SSH closes connection after failures
                if pattern == "Connection closed":

                    break

            ScreenshotStep("tester").execute(context)

            logger.info("Invalid SSH credentials correctly rejected")

            self.pass_test()

        finally:

            StepRunner([
                ClearTerminalStep("tester")
            ]).run(context)

        return self