from core.testcase import TestCase
from core.step_runner import StepRunner
from steps.open_url_step import OpenURLStep
from steps.browser_screenshot_step import BrowserScreenshotStep
from steps.fill_input_step import FillInputStep
from steps.click_step import ClickStep

class TC5HTTPSValidLogin(TestCase):

    def __init__(self):

        super().__init__(
            "TC5_HTTPS_VALID_LOGIN",
            "Valid HTTPS credentials should allow login"
        )

    def run(self, context):

        url = f"https://{context.ssh_ip}/dvwa/login.php"

        StepRunner([
            OpenURLStep(url),
            FillInputStep("username", context.ssh_user),
            FillInputStep("password", context.ssh_password),
            ClickStep("Login"),
            BrowserScreenshotStep("https_valid_login.png")
        ]).run(context)

        self.pass_test()

        return self