"""
TC4 - User Creation Without a Role: Verify the DUT never leaves a user in an
ambiguous/unbounded-privilege state when no role is specified at creation.

Clause: 1.1.3 Role Based Access Control
Test Scenario 1.1.3.4

Test case (per tracker):
  TC4 To create a user without any role.
  Expected: New user created without specifying role is automatically
  assigned the lowest privileged role. User creation without any role shall
  be unsuccessful.
  Pass: DUT assigns default role correctly, user can only perform
  default-level operations - Pass.

Two DUT behaviours are both compliant per the Expected text above, since it
describes an "either/or" outcome:
  (a) Creation succeeds AND the DUT auto-assigns the lowest-privileged
      default role, AND that user can subsequently perform only
      default-level operations.
  (b) Creation is rejected outright (DUT refuses to create a user with no
      role rather than leaving it unbounded).
The only FAIL condition is a user ending up created with no defined role,
or with elevated/unbounded privileges.

Reference DUT behaviour (from TSTP evidence for this clause):
  - Roles observed: rootsystem, netadmin, sysadmin, operator.
  - A user's assigned role is inspectable via
    "show running-config AAA user <user>" and
    "show running-config AAA authorization role <role>".
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


class TC4UserCreationWithoutRole(TestCase):
    protocol = "ssh"

    def __init__(self):
        super().__init__(
            "TC4_USER_CREATION_WITHOUT_ROLE",
            "Verify a user created without a role is either default-assigned or rejected outright",
        )

    # -- helpers --------------------------------------------------------

    def _ssh_login(self, context, role_or_user):
        """SSH into DUT as the given account and reach the privileged prompt."""
        ssh_binary = context.profile.get("ssh.binary", "ssh")
        ssh_options = context.profile.get_list("ssh.connect_options")
        login_user = context.profile.get(f"rbac.user.{role_or_user}", role_or_user)
        login_pass = context.profile.get(f"rbac.password.{role_or_user}", context.ssh_password)
        ssh_target = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=login_user,
            ip=context.ssh_ip
        )

        ssh_cmd = " ".join([ssh_binary, *ssh_options, ssh_target])

        StepRunner([CommandStep("tester", ssh_cmd)]).run(context)
        ExpectOneOfStep("tester", context.profile.get_list("ssh.password_prompt")).execute(context)
        StepRunner([InputStep("tester", login_pass)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester",
            ["#", ">", "$", "Permission denied", "Authentication failed"],
            timeout=10,
        ).execute(context)
        ScreenshotStep("tester").execute(context)

        if any(f in pattern for f in ["Permission denied", "Authentication failed"]):
            logger.error("TC4: SSH login as %s FAILED", role_or_user)
            return False

        logger.info("TC4: SSH login as %s successful", role_or_user)
        return True

    def _attempt_create_user_without_role(self, context, new_user):
        """
        Attempt to create a user with no role/privilege parameter supplied.
        Returns (outcome, output) where outcome is one of:
          "created"  - DUT accepted the creation (auto-assign path)
          "rejected" - DUT refused the creation outright (reject path)
          "unknown"  - neither a clear success nor a clear rejection pattern
        """
        cmds = context.profile.get_list("rbac.create_user_no_role_commands")
        cmds = [c.format(user=new_user) for c in cmds]

        last_pattern = ""
        for cmd in cmds:
            StepRunner([CommandStep("tester", cmd, settle_time=4)]).run(context)
            last_pattern, _ = ExpectOneOfStep(
                "tester",
                ["#", ">", "$", "successfully", "saved", "access denied",
                 "Access Denied", "already exists", "Y/N",
                 "% Incomplete command", "% Invalid input", "role required",
                 "Role is mandatory"],
                timeout=10,
            ).execute(context)

        ScreenshotStep("tester").execute(context)

        rejected_markers = [
            "% Incomplete command", "% Invalid input", "role required",
            "Role is mandatory", "access denied", "Access Denied",
        ]
        success_markers = ["successfully", "saved"]

        if any(m in last_pattern for m in rejected_markers):
            return "rejected", last_pattern
        if any(m in last_pattern for m in success_markers):
            return "created", last_pattern
        return "unknown", last_pattern

    def _get_assigned_role(self, context, new_user):
        """Read back the role the DUT assigned to <new_user>, if any."""
        cmd = context.profile.get(
            "rbac.show_user_command", "do show running-config AAA user {user}"
        ).format(user=new_user)

        StepRunner([CommandStep("tester", cmd, settle_time=3)]).run(context)
        pattern, _ = ExpectOneOfStep("tester", ["#", ">", "$"], timeout=10).execute(context)
        ScreenshotStep("tester").execute(context)

        expected_default_role = context.profile.get("rbac.expected_default_role", "operator")
        return expected_default_role if expected_default_role in pattern else None

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

    def _delete_user(self, context, user):
        cmd = context.profile.get("rbac.delete_user_command", "no AAA user {user}").format(user=user)
        StepRunner([CommandStep("tester", cmd, settle_time=3)]).run(context)
        ExpectOneOfStep("tester", ["#", ">", "$"], timeout=10).execute(context)
        ScreenshotStep("tester").execute(context)
        StepRunner([ClearTerminalStep("tester")]).run(context)

    # -- entry point ------------------------------------------------------

    def run(self, context):
        new_user = context.profile.get("rbac.no_role_user", "defuser")
        expected_default_role = context.profile.get("rbac.expected_default_role", "operator")

        admin_login_ok = self._ssh_login(context, "rootsystem")
        outcome = None
        assigned_role = None
        default_ops_ok = None
        elevated_ops_denied = None

        if admin_login_ok:
            outcome, out = self._attempt_create_user_without_role(context, new_user)
            logger.info("TC4: creation attempt without a role resulted in '%s' - %s", outcome, out)
            StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)

        if outcome == "created":
            assigned_role = self._get_assigned_role(context, new_user)
            if assigned_role:
                logger.info("TC4: DUT auto-assigned default role '%s' to '%s'",
                            assigned_role, new_user)
            else:
                logger.error("TC4: user '%s' was created but no defined default role was assigned - "
                             "unbounded privilege risk", new_user)

            user_login_ok = self._ssh_login(context, new_user)
            if user_login_ok:
                default_cmds = context.profile.get_list(f"rbac.commands.{expected_default_role}")
                elevated_cmds = context.profile.get_list("rbac.elevated_commands")

                default_ops_ok = True
                for cmd in default_cmds:
                    ok, cmd_out = self._execute_command(context, cmd)
                    if not ok:
                        logger.error("TC4: default-role user FAILED default-level command '%s' - %s",
                                     cmd, cmd_out)
                        default_ops_ok = False

                elevated_ops_denied = True
                for cmd in elevated_cmds:
                    ok, cmd_out = self._execute_command(context, cmd)
                    if ok:
                        logger.error(
                            "TC4: default-role user executed elevated command '%s' - RBAC violation",
                            cmd,
                        )
                        elevated_ops_denied = False

                StepRunner([ClearTerminalStep("tester")]).run(context)
                StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)
            else:
                logger.warning("TC4: skipping privilege checks - login as %s failed", new_user)

            # clean up
            self._ssh_login(context, "rootsystem")
            self._delete_user(context, new_user)

        elif outcome == "rejected":
            logger.info("TC4: DUT correctly refused to create a user without a role")

        # -- verdict --------------------------------------------------------
        auto_assign_path_ok = (
            outcome == "created"
            and assigned_role == expected_default_role
            and default_ops_ok
            and elevated_ops_denied
        )
        rejection_path_ok = (outcome == "rejected")

        if admin_login_ok and (auto_assign_path_ok or rejection_path_ok):
            self.pass_test()
        else:
            logger.warning(
                "TC4 breakdown - outcome=%s assigned_role=%s default_ops=%s elevated_denied=%s",
                outcome, assigned_role, default_ops_ok, elevated_ops_denied,
            )
            self.fail_test()

        return self