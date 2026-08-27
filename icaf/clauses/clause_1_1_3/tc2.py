"""
TC2 - Role Command Authorization: Verify that operations assigned to a
specific role are executed successfully, and operations NOT assigned to that
role are denied (command-group based RBAC enforcement).
Clause: 1.1.3 Role-Based access control
Test Scenario 1.1.3.2

Requirement (ITSAR 1.1.3):
The RBAC system shall control how users/groups of users are allowed access to
the various domains (FM, PM, System Admin, etc.) and what type of operation
(View, Modify, Execute) they may perform, via a specific command or command
group.

Reference DUT behaviour (from TSTP evidence for this clause):
  - Command groups and the functions bound to them are inspectable via
    "show running-config AAA authorization role command-group".
  - Access of a specific role to a specific function is inspectable via
    "show running-config AAA authorization role command-group <function>".
  - A role attempting a command outside its authorized command-group is
    rejected by the DUT (command authorization failure).
"""

from icaf.core.testcase import TestCase
from icaf.core.step_runner import StepRunner
from icaf.steps.command_step import CommandStep
from icaf.steps.expect_one_of_step import ExpectOneOfStep
from icaf.steps.input_step import InputStep
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger


class TC2RoleCommandAuthorization(TestCase):
    protocol = "ssh"

    def __init__(self):
        super().__init__(
            "TC2_ROLE_COMMAND_AUTHORIZATION",
            "Verify authorized commands succeed and unauthorized commands are denied per role",
        )

    # -- helpers --------------------------------------------------------

    def _ssh_login(self, context, role):
        """SSH into DUT as the given role account and reach the privileged prompt."""
        ssh_binary = context.profile.get("ssh.binary", "ssh")
        ssh_options = context.profile.get_list("ssh.connect_options")
        role_user = context.profile.get(f"rbac.user.{role}", role)
        role_pass = context.profile.get(f"rbac.password.{role}", context.ssh_password)
        ssh_target = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=role_user,
            ip=context.ssh_ip
        )

        ssh_cmd = " ".join([ssh_binary, *ssh_options, ssh_target])

        StepRunner([CommandStep("tester", ssh_cmd)]).run(context)
        ExpectOneOfStep("tester", context.profile.get_list("ssh.password_prompt")).execute(context)
        StepRunner([InputStep("tester", role_pass)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester",
            ["#", ">", "$", "Permission denied", "Authentication failed"],
            timeout=10,
        ).execute(context)
        ScreenshotStep("tester").execute(context)

        if any(f in pattern for f in ["Permission denied", "Authentication failed"]):
            logger.error("TC2: SSH login as %s FAILED", role)
            return False

        logger.info("TC2: SSH login as %s successful", role)
        return True

    def _list_command_group_functions(self, context):
        """Enumerate the command-group functions defined on the DUT."""
        cmd = context.profile.get(
            "rbac.list_command_groups_command",
            "do show running-config AAA authorization role command-group",
        )
        StepRunner([CommandStep("tester", cmd, settle_time=3)]).run(context)
        ExpectOneOfStep("tester", ["#", ">", "$"], timeout=10).execute(context)
        ScreenshotStep("tester").execute(context)

    def _verify_command_group_membership(self, context, role, function_name):
        """Confirm <role> is (or is not) listed against <function_name>'s command-group."""
        cmd = context.profile.get(
            "rbac.show_command_group_function_command",
            "do show running-config AAA authorization role command-group {function}",
        ).format(function=function_name)

        StepRunner([CommandStep("tester", cmd, settle_time=3)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester", ["#", ">", "$"], timeout=10
        ).execute(context)
        ScreenshotStep("tester").execute(context)
        return role in pattern

    def _execute_command(self, context, cmd):
        """Run a single operational command and classify success vs. denial."""
        StepRunner([CommandStep("tester", cmd, settle_time=4)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester",
            ["#", ">", "$", "% Invalid input", "Command authorization failed",
             "access denied", "Access Denied", "% Authorization failed"],
            timeout=10,
        ).execute(context)
        ScreenshotStep("tester").execute(context)

        denied = any(d in pattern for d in [
            "% Invalid input", "Command authorization failed",
            "access denied", "Access Denied", "% Authorization failed",
        ])
        return (not denied), pattern

    # -- entry point ------------------------------------------------------

    def run(self, context):
        roles_to_test = context.profile.get_list("rbac.roles") or ["netadmin", "sysadmin", "operator"]

        authorized_results = {}
        unauthorized_results = {}
        membership_results = {}

        # Step 0: enumerate command-group functions from an admin session
        admin_login_ok = self._ssh_login(context, "rootsystem")
        if admin_login_ok:
            self._list_command_group_functions(context)
            for role in roles_to_test:
                function_name = context.profile.get(f"rbac.function.{role}", role)
                membership_results[role] = self._verify_command_group_membership(
                    context, role, function_name
                )
            StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)

        # Step 1: for each role, run one authorized command (expect success) and
        # one command belonging to another role's command-group (expect denial).
        for role in roles_to_test:
            role_login_ok = self._ssh_login(context, role)
            if not role_login_ok:
                logger.warning("TC2: skipping command checks - login as %s failed", role)
                continue

            authorized_cmd = context.profile.get(f"rbac.authorized_command.{role}")
            unauthorized_cmd = context.profile.get(f"rbac.unauthorized_command.{role}")

            if authorized_cmd:
                ok, out = self._execute_command(context, authorized_cmd)
                authorized_results[role] = ok
                if ok:
                    logger.info("TC2: %s successfully executed authorized command '%s'",
                                role, authorized_cmd)
                else:
                    logger.error("TC2: %s FAILED to execute authorized command '%s' - %s",
                                 role, authorized_cmd, out)

            if unauthorized_cmd:
                ok, out = self._execute_command(context, unauthorized_cmd)
                # PASS for this check means the command was DENIED
                unauthorized_results[role] = not ok
                if ok:
                    logger.error(
                        "TC2: %s was able to execute unauthorized command '%s' - RBAC violation",
                        role, unauthorized_cmd,
                    )
                else:
                    logger.info("TC2: %s correctly denied unauthorized command '%s'",
                                role, unauthorized_cmd)

            StepRunner([ClearTerminalStep("tester")]).run(context)
            StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)

        # -- verdict --------------------------------------------------------
        membership_ok = bool(membership_results) and all(membership_results.values())
        authorized_ok = bool(authorized_results) and all(authorized_results.values())
        unauthorized_ok = bool(unauthorized_results) and all(unauthorized_results.values())

        if admin_login_ok and membership_ok and authorized_ok and unauthorized_ok:
            self.pass_test()
        else:
            logger.warning(
                "TC2 breakdown - membership=%s authorized=%s unauthorized=%s",
                membership_results, authorized_results, unauthorized_results,
            )
            self.fail_test()

        return self