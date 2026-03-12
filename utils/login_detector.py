from selenium.webdriver.common.by import By


class LoginDetector:

    @staticmethod
    def detect_password(driver):

        passwords = driver.find_elements(By.XPATH, "//input[@type='password']")

        if not passwords:
            raise Exception("No password field detected")

        return passwords[0]


    @staticmethod
    def detect_username(password):

        try:
            form = password.find_element(By.XPATH, "./ancestor::form")

            username = form.find_element(
                By.XPATH,
                ".//input[@type='text' or @type='email' or not(@type)]"
            )

            return username

        except:
            pass

        inputs = password.find_elements(
            By.XPATH,
            "./preceding::input[@type='text' or @type='email']"
        )

        if inputs:
            return inputs[-1]

        return None


    @staticmethod
    def detect_submit(password):

        try:
            form = password.find_element(By.XPATH, "./ancestor::form")

            submit = form.find_element(
                By.XPATH,
                ".//button[@type='submit'] | .//input[@type='submit']"
            )

            return submit

        except:
            pass

        buttons = password.find_elements(By.XPATH, "./following::button")

        if buttons:
            return buttons[0]

        raise Exception("Submit button not detected")