from utils.logger import logger
from runtime.context import RuntimeContext
from core.clause_runner import ClauseRunner
from terminal.manager import TerminalManager
from browser.manager import BrowserManager
from reporting.report_manager import ReportManager
from utils.dut_info import get_dut_info


class Engine:

    def __init__(self, clause=None, section=None, ssh_user=None, ssh_ip=None, ssh_password=None, snmp_user=None, snmp_auth_pass=None, snmp_priv_pass=None):

        self.context = RuntimeContext(
            clause=clause,
            section=section,
            ssh_user=ssh_user,
            ssh_ip=ssh_ip,
            ssh_password=ssh_password,
            snmp_user=snmp_user,
            snmp_auth_pass=snmp_auth_pass,
            snmp_priv_pass=snmp_priv_pass
        )

        logger.info("Engine initialized")

    def start(self):

        logger.info("Starting TCAF engine")
        logger.info(f"Execution ID: {self.context.execution_id}")

        if self.context.clause:
            logger.info(f"Execution mode: Clause {self.context.clause}")

        elif self.context.section:
            logger.info(f"Execution mode: Section {self.context.section}")

        else:
            logger.info("Execution mode: Full evaluation")

        self.initialize_runtime()

        logger.info("Runtime environment ready")

        runner = ClauseRunner(self.context)

        results = runner.run()

        for tc in results:
            logger.info(f"{tc.name} → {tc.status}")

        report_manager = ReportManager()

        report_manager.generate(self.context, results)

    def initialize_runtime(self):

        logger.info("Initializing runtime environment")

        # Initialize terminal manager
        self.context.terminal_manager = TerminalManager()
        self.context.browser = BrowserManager()

        tm = self.context.terminal_manager

        # Create shared terminals
        tm.create_terminal("tester")
        tm.create_terminal("dut")

        logger.info("Terminals created")

        logger.info("Collecting DUT information")

        dut_info = get_dut_info(
            self.context.ssh_user,
            self.context.ssh_ip
        )

        self.context.dut_name = dut_info["dut_name"]
        self.context.dut_version = dut_info["dut_version"]
        self.context.os_hash = dut_info["os_hash"]
        self.context.config_hash = dut_info["config_hash"]

        logger.info(f"DUT Name: {self.context.dut_name}")
        logger.info(f"DUT Version: {self.context.dut_version}")

        logger.info("Terminal manager initialized")