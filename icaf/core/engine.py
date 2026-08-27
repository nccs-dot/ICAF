import os
import yaml

from icaf.runtime.context import RuntimeContext
from icaf.core.clause_runner import ClauseRunner
from icaf.terminal.manager import TerminalManager
from icaf.reporting.report_manager import ReportManager
from icaf.utils.dut_info import get_dut_info
from icaf.config.profile_loader import ProfileLoader
from icaf.utils.logger import logger

# Clauses that only need SSH — no browser initialization needed
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
        testbed_diagram=None,
        oam_context=None,
    ):
        # 1. Resolve and load profile configuration dictionary
        if isinstance(profile, dict):
            self.profile = profile
        else:
            self.profile = self._load_profile_dict(profile)

        # 2. Instantiate RuntimeContext (without profile kwarg)
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
            testbed_diagram=testbed_diagram,
            oam_context=oam_context,
        )

        # Validate required SSH parameters
        required = {
            "SSH_USER": ssh_user,
            "SSH_IP": ssh_ip,
            "SSH_PASSWORD": ssh_password,
        }

        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

        # Inject profile into context
        self.context.profile = self.profile

        logger.info("Engine initialized")

    def _load_profile_dict(self, profile_name):
        """Loads the profile dictionary via ProfileLoader or direct YAML fallback."""
        try:
            if hasattr(ProfileLoader, "load"):
                return ProfileLoader.load(profile_name)
            elif hasattr(ProfileLoader, "load_profile"):
                return ProfileLoader.load_profile(profile_name)
            elif callable(ProfileLoader):
                loader = ProfileLoader()
                if hasattr(loader, "load"):
                    return loader.load(profile_name)
                elif hasattr(loader, "load_profile"):
                    return loader.load_profile(profile_name)
        except Exception as e:
            logger.debug(f"ProfileLoader invocation failed: {e}")

        # Direct file fallback
        possible_paths = [
            f"icaf/profile/{profile_name}.yaml",
            f"icaf/profile/{profile_name}.yml",
            f"profile/{profile_name}.yaml",
            profile_name if str(profile_name).endswith((".yaml", ".yml")) else "",
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            return data
                except Exception as e:
                    logger.warning(f"Error reading profile file {path}: {e}")

        logger.warning(f"Could not load profile config for '{profile_name}'. Using empty dict.")
        return {}

    def start(self):
        logger.info("Starting ICAF engine")
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

        logger.info("Generating compliance report")
        report_manager = ReportManager()
        report_path = report_manager.generate(self.context, results)
        logger.info(f"Report generated: {report_path}")

        return {
            "report_path": report_path,
            "context": self.context,
            "results": results,
        }

    def initialize_runtime(self):
        logger.info("Initializing runtime environment")

        clause = self.context.clause
        ssh_only = clause in _SSH_ONLY_CLAUSES

        # Terminal manager is always required
        self.context.terminal_manager = TerminalManager()

        # Browser manager — initialize only when clause requires it
        if ssh_only:
            self.context.browser = None
            logger.info(f"Clause {clause}: browser skipped (SSH-only clause)")
        else:
            from icaf.browser.manager import BrowserManager
            self.context.browser = BrowserManager()

        tm = self.context.terminal_manager

        # Always create both tester (local host) and dut (DUT session) terminals
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

        logger.info("Terminals created: tester, dut")

        logger.info("Collecting DUT information")
        dut_info = get_dut_info(
            self.context.profile,
            self.context.ssh_user,
            self.context.ssh_ip,
            self.context.ssh_password,
        )

        if isinstance(dut_info, dict):
            self.context.dut_name = dut_info.get("dut_name")
            self.context.dut_version = dut_info.get("dut_version")
            self.context.os_hash = dut_info.get("os_hash")
            self.context.config_hash = dut_info.get("config_hash")

        logger.info(f"DUT Name: {self.context.dut_name}")
        logger.info(f"DUT Version: {self.context.dut_version}")
        logger.info("Terminal manager initialized")