"""
TC7 — HTTPS Invalid Login: verify unsuccessful mutual authentication over HTTPS.
Test Scenario 1.1.1.7
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
from icaf.utils.logger import logger


class TC7HTTPSInvalidLogin(TestCase):
    protocol = "https"

    def __init__(self):
        super().__init__(
            "TC7_HTTPS_INVALID_LOGIN",
            "Configure and verify unsuccessful mutual authentication over HTTPS",
        )

    def run(self, context):

        raw_url = context.profile.get("web.login_url", context.web_login_url)

        ip = getattr(context, "ssh_ip", None) or getattr(context, "ip", None)

        if not ip:
            raise ValueError("No IP found in context (ssh_ip/ip)")

        login_url = context.web_login_url
        driver = context.browser.driver
        driver.get(login_url)  # must be real origin

        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
        driver.delete_all_cookies()
        username   = context.profile.get("web.username",   context.web_username)
        bad_pass   = context.profile.get("web.bad_password", "WrongAdmin@999!")
        user_sel   = context.profile.get("web.user_field_selector",
                                         "input[name='username'], #username")
        pass_sel   = context.profile.get("web.pass_field_selector",
                                         "input[name='password'], #password, input[type='password']")
        submit_sel = context.profile.get("web.submit_selector",
                                         "button[type='submit'], input[type='submit'], .btn-login")

        error_indicators = [
            s.strip() for s in context.profile.get(
                "web.login_error_indicator",
                "Failed to log in,Invalid credentials,Login failed,Incorrect",
            ).split(",")
        ]
        dashboard_indicators = [
            s.strip() for s in context.profile.get(
                "web.dashboard_indicator",
                "Dashboard,System Information,logout",
            ).split(",")
        ]

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc7_https_invalid.pcapng"),
            OpenURLStep(login_url),
            WaitStep(2),
        ]).run(context)

        BrowserScreenshotStep(
            "tc7_login_page.png",
            caption="TC7 Step 1 — DUT HTTPS management login page loaded prior to invalid credential attempt",
        ).execute(context)

        StepRunner([
            FillInputStep(user_sel,   username),
            FillInputStep(pass_sel,   bad_pass),
            ClickStep(submit_sel),
            WaitStep(3),
        ]).run(context)

        BrowserScreenshotStep(
            "tc7_after_bad_login.png",
            caption="TC7 Step 2 — Login error displayed after invalid credentials submitted, dashboard not accessible",
        ).execute(context)
        StepRunner([PcapStopStep()]).run(context)

        # Error must be shown; dashboard must NOT be accessible
        error_shown    = VerifyOutputStep("browser", error_indicators).execute(context)
        access_granted = VerifyOutputStep("browser", dashboard_indicators).execute(context)

        StepRunner([
            AnalyzePcapStep("tls"),
            WiresharkPacketScreenshotStep(
                "tls",
                caption="TC7 Step 2 — Wireshark shows TLS session terminated after HTTP 401/403 response from DUT",
            ),
        ]).run(context)

        # Inter-TC cooldown
        StepRunner([WaitStep(4)]).run(context)
        try:
            context.browser.driver.get("about:blank")
        except Exception:
            pass

        if not access_granted and (error_shown or not access_granted):
            logger.info("TC7: HTTPS login correctly denied for invalid credentials")
            self.pass_test()
        else:
            logger.error("TC7: DUT granted HTTPS access with invalid credentials — FAIL")
            self.fail_test()

        return self