from .login_detector import LoginDetector


class LoginExecutor:

    def execute(self, context):

        driver = context.browser.driver

        password = LoginDetector.detect_password(driver)

        username = LoginDetector.detect_username(password)

        submit = LoginDetector.detect_submit(password)

        if username:
            username.clear()
            username.send_keys(context.web_username)

        password.clear()
        password.send_keys(context.web_password)

        submit.click()