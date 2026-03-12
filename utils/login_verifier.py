from selenium.webdriver.common.by import By


class LoginVerifier:

    ERROR_KEYWORDS = [
        "invalid",
        "incorrect",
        "login failed",
        "authentication failed",
        "wrong password",
        "access denied"
    ]

    @staticmethod
    def capture_state(driver):

        return {
            "url": driver.current_url,
            "cookies": driver.get_cookies(),
            "title": driver.title,
            "dom": len(driver.page_source)
        }

    @staticmethod
    def verify(driver, before):

        page = driver.page_source.lower()

        # 1. Detect explicit login errors
        for keyword in LoginVerifier.ERROR_KEYWORDS:
            if keyword in page:
                return False

        # 2. If password field disappeared → success
        password_fields = driver.find_elements(By.XPATH, "//input[@type='password']")
        if len(password_fields) == 0:
            return True

        # 3. URL changed → success
        if driver.current_url != before["url"]:
            return True

        # 4. Cookies increased → success
        if len(driver.get_cookies()) > len(before["cookies"]):
            return True

        # 5. Page title changed → success
        if driver.title != before["title"]:
            return True

        # 6. DOM changed significantly → success
        if abs(len(driver.page_source) - before["dom"]) > 150:
            return True

        # If no failure indicators detected, assume success
        return True