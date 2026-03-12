import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.step import Step
from utils.login_executor import LoginExecutor
from utils.login_verifier import LoginVerifier


class AutoLoginStep(Step):

    def __init__(self):

        super().__init__("Automatic login")


    def execute(self, context):

        driver = context.browser.driver

        # Wait until password field appears (router UIs can be slow)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
        )

        # Capture page state before login
        before = LoginVerifier.capture_state(driver)

        executor = LoginExecutor()

        executor.execute(context)

        # Give UI time to process login
        WebDriverWait(driver, 5).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        success = LoginVerifier.verify(driver, before)

        if not success:

            path = context.evidence.screenshot_path(
                context.clause,
                context.current_testcase
            )

            file = f"{path}/login_failure_debug.png"

            driver.save_screenshot(file)

            raise Exception("Login verification failed")