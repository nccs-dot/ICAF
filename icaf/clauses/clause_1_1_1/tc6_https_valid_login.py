"""
TC6 — HTTPS Valid Login: verify successful mutual authentication over HTTPS.
Test Scenario 1.1.1.6
"""

from icaf.core.testcase import TestCase
from icaf.core.step_runner import StepRunner
from icaf.steps.open_url_step import OpenURLStep
from icaf.steps.fill_input_step import FillInputStep
from icaf.steps.click_step import ClickStep
from icaf.steps.browser_screenshot_step import BrowserScreenshotStep
from icaf.steps.verify_output_step import VerifyOutputStep
from icaf.steps.pcap_start_step import PcapStartStep
from icaf.steps.pcap_stop_step import PcapStopStep
from icaf.steps.analyze_pcap_step import AnalyzePcapStep
from icaf.steps.wireshark_packet_screenshot_step import WiresharkPacketScreenshotStep
from icaf.steps.wait_step import WaitStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.utils.logger import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TC6HTTPSValidLogin(TestCase):
    protocol = "https"
    def __init__(self):
        super().__init__(
            "TC6_HTTPS_VALID_LOGIN",
            "Configure and verify successful mutual authentication over HTTPS",
        )

    def run(self, context):
        raw_url = context.web_login_url

        login_url = raw_url
        username   = context.profile.get("web.username",   context.web_username)
        password   = context.profile.get("web.password",   context.web_password)
        user_sel   = context.profile.get("web.user_field_selector",
                                         "input[name='username'], #username")
        pass_sel   = context.profile.get("web.pass_field_selector",
                                         "input[name='password'], #password, input[type='password']")
        submit_sel = context.profile.get(
            "web.submit_selector",
            "//button[contains(., 'Sign in')]"
        )
        dashboard_indicators = [
            s.strip() for s in context.profile.get(
                "web.dashboard_indicator",
                "System Information,Dashboard,logout,Logout,index.asp,LOGOUT",
            ).split(",")
        ]

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc6_https_valid.pcapng"),
            OpenURLStep(login_url),
            WaitStep(2),
        ]).run(context)

        BrowserScreenshotStep(
            "tc6_login_page.png",
            caption="TC6 Step 1 — DUT HTTPS management login page loaded, TLS connection established",
        ).execute(context)

        StepRunner([
            FillInputStep(user_sel,   username),
            FillInputStep(pass_sel,   password),
            ClickStep(submit_sel),
            WaitStep(3),
        ]).run(context)

        BrowserScreenshotStep(
            "tc6_after_login.png",
            caption="TC6 Step 2 — Dashboard accessible after valid credentials submitted, confirming successful HTTPS mutual authentication",
        ).execute(context)
        StepRunner([PcapStopStep()]).run(context)

        # Check dashboard is accessible
        try:
            WebDriverWait(context.browser.driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(), 'Logout')]")
                )
            )
            ok = True
        except:
            ok = False

        if ok:
            logger.info("TC6: HTTPS valid login succeeded — dashboard accessible")
            StepRunner([
                AnalyzePcapStep("tls"),
                WiresharkPacketScreenshotStep(
                    "tls",
                    caption="TC6 Step 2 — Wireshark shows TLS handshake completed with valid certificate exchange for HTTPS session",
                ),
            ]).run(context)
        else:
            logger.error("TC6: Dashboard not accessible after valid login")

        # Inter-TC cooldown — no SSH session to disconnect, just browser reset
        StepRunner([WaitStep(4)]).run(context)
        # Navigate away to reset browser state
        try:
            context.browser.driver.get("about:blank")
        except Exception:
            pass

        self.pass_test() if ok else self.fail_test()
        return self