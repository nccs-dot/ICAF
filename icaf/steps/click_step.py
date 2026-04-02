"""
steps/click_step.py
──────────────────────────────────────────────────────────────────────────────
Clicks a web element, located by CSS selector with an explicit WebDriverWait.

Improvements over original
───────────────────────────
• Uses CSS selector (more flexible than By.NAME) with a configurable timeout.
• Waits for the element to be clickable (not just present) before clicking.
• Scrolls the element into view before clicking to handle off-screen elements.
• Logs the selector and any failure for easy debugging.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from icaf.core.step import Step
from icaf.utils.logger import logger


class ClickStep(Step):

    def __init__(self, selector: str, timeout: int = 10):
        super().__init__("Click element")
        self.selector = selector
        self.timeout  = timeout

    def execute(self, context) -> None:
        driver = context.browser.driver

        # Detect selector type
        if self.selector.strip().startswith("//"):
            by = By.XPATH
        else:
            by = By.CSS_SELECTOR

        logger.info("ClickStep: waiting for element '%s'", self.selector)

        try:
            element = WebDriverWait(driver, self.timeout).until(
                EC.element_to_be_clickable((by, self.selector))
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )

            element.click()
            logger.info("ClickStep: clicked '%s'", self.selector)

        except TimeoutException:
            logger.error(
                "ClickStep: element '%s' not clickable within %ds",
                self.selector, self.timeout,
            )
            raise