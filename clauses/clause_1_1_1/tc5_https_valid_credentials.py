from core.testcase import TestCase
from core.step_runner import StepRunner

from steps.open_url_step import OpenURLStep
from steps.browser_screenshot_step import BrowserScreenshotStep
from steps.auto_login_step import AutoLoginStep


class TC5HTTPSValidLogin(TestCase):

    def __init__(self):

        super().__init__(
            "TC5_HTTPS_VALID_LOGIN",
            "Valid HTTPS credentials should allow login"
        )


    def run(self, context):

        StepRunner([
            OpenURLStep(context.web_login_url),
            AutoLoginStep(),
            BrowserScreenshotStep("https_valid_login.png")
        ]).run(context)

        self.pass_test()

        return self