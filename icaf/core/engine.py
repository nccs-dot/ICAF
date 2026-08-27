from icaf.utils.logger import logger
from icaf.runtime.context import RuntimeContext
from icaf.core.clause_runner import ClauseRunner
from icaf.terminal.manager import TerminalManager
from icaf.reporting.report_manager import ReportManager
from icaf.utils.dut_info import get_dut_info
from icaf.config.profile_loader import ProfileLoader

# Clauses that only need SSH — no browser, no extra terminals
_SSH_ONLY_CLAUSES = {"1.1.3", "1.2.1", "1.2.4", "1.6.5"}


class Engine:

    def __init__(
        self,
        clause=None,
        section=None,
        profile="default",
        ssh_user=None,
        ssh_ip=None,
        ssh_password=None,
        snmp_user=None,
        snmp_auth_pass=None,
        snmp_priv_pass=None,
        snmp_community=None,
        web_login_url=None,
        web_username=None,
        web_password=None,
        oam_context=None
    ):

        # Load DUT profile
        logger.info(f"Loading DUT profile: {profile}")
        self.profile = ProfileLoader(profile)

        # Create runtime context
        self.context = RuntimeContext(
            clause=clause,
            section=section,
            ssh_user=ssh_user,
            ssh_ip=ssh_ip,
            ssh_password=ssh_password,
            snmp_user=snmp_user,
            snmp_auth_pass=snmp_auth_pass,
            snmp_priv_pass=snmp_priv_pass,
            snmp_community=snmp_community,
            web_login_url=web_login_url,
            web_username=web_username,
            web_password=web_password,
            oam_context=oam_context
        )

        # Inject profile into context
        self.context.profile = self.profile

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
        report_path = report_manager.generate(self.context, results)

        # Returning these values is backward compatible with the CLI/PyQt callers
        # and gives the local web runner a stable hand-off point for artifacts.
        return {
            "report_path": report_path,
            "context": self.context,
            "results": results,
        }

    def initialize_runtime(self):

        logger.info("Initializing runtime environment")

        clause = self.context.clause
        ssh_only = clause in _SSH_ONLY_CLAUSES

        # Terminal manager — always needed
        self.context.terminal_manager = TerminalManager()

        # Browser — only for clauses that need it
        if ssh_only:
            self.context.browser = None
            logger.info(f"Clause {clause}: browser skipped (SSH-only clause)")
        else:
            from icaf.browser.manager import BrowserManager
            self.context.browser = BrowserManager()

        tm = self.context.terminal_manager

        if ssh_only:
            # Clause 1.2.4 needs the dut terminal (tmux + gnome-terminal)
            # for real scrot screenshots — same as clause 1.1.1 uses "tester"
            tm.create_terminal(
                "dut",
                ssh_ip=self.context.ssh_ip,
                ssh_user=self.context.ssh_user,
                ssh_password=self.context.ssh_password,
            )
            logger.info(f"Clause {clause}: created 'dut'  terminal (SSH-only clause)")
        else:
            tm.create_terminal(
                "tester",
                ssh_ip=self.context.ssh_ip,
                ssh_user=self.context.ssh_user,
                ssh_password=self.context.ssh_password,
            )
            tm.create_terminal(
                "dut",
                ssh_ip=self.context.ssh_ip,
                ssh_user=self.context.ssh_user,
                ssh_password=self.context.ssh_password,
            )

        logger.info("Terminals created")

        logger.info("Collecting DUT information")

        dut_info = get_dut_info(
            self.context.profile,
            self.context.ssh_user,
            self.context.ssh_ip,
            self.context.ssh_password
        )

        self.context.dut_name = dut_info["dut_name"]
        self.context.dut_version = dut_info["dut_version"]
        self.context.os_hash = dut_info["os_hash"]
        self.context.config_hash = dut_info["config_hash"]

        logger.info(f"DUT Name: {self.context.dut_name}")
        logger.info(f"DUT Version: {self.context.dut_version}")

        logger.info("Terminal manager initialized")