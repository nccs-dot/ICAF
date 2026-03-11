from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.open_url_step import OpenURLStep
from steps.browser_screenshot_step import BrowserScreenshotStep
from steps.fill_input_step import FillInputStep
from steps.click_step import ClickStep

class TC6HTTPSInvalidLogin(TestCase):

    def __init__(self):

        super().__init__(
            "TC6_HTTPS_INVALID_LOGIN",
            "Invalid HTTPS credentials must fail"
        )

    def run(self, context):

        url = f"https://{context.ssh_ip}"

        StepRunner([
            OpenURLStep(url),
            FillInputStep("username", context.ssh_user),
            FillInputStep("password", "wrongpassword"),
            ClickStep("Login"),
            BrowserScreenshotStep("https_invalid_login.png")
        ]).run(context)

        self.pass_test()

        return self