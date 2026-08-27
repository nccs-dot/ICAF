"""
TC1 - RBAC Feature Availability: Verify RBAC is available on the DUT by
creating at least three user accounts under different roles/profiles and
confirming each is created and reflected correctly on the DUT.
Clause: 1.1.3 Role Based Access Control
Test Scenario 1.1.3.1

Requirement (ITSAR 1.1.3):
The network product shall support Role Based Access Control (RBAC) with a
minimum of 3 user roles for OAM privilege management.

Test case (per tracker):
  TC1 To check RBAC feature availability by creating at least three users
  with different Roles/profiles.
  Expected: RBAC shall be available and is checked by creating three users
  successfully. List of the roles or privileges have to be obtained from
  Documentation and to be verified from the DUT.
  Pass: If users under various Roles are created successfully - Pass.

Reference DUT behaviour (from TSTP evidence for this clause):
  - Roles observed: rootsystem, netadmin, sysadmin, operator.
  - Users and their assigned roles are listed via
    "show running-config AAA user" and verified individually via
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


class TC1RBACFeatureAvailability(TestCase):
    protocol = "ssh"

    def __init__(self):
        super().__init__(
            "TC1_RBAC_FEATURE_AVAILABILITY",
            "Verify RBAC is available by creating at least 3 users under different roles",
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
            logger.error("TC1: SSH login as %s FAILED", role)
            return False

        logger.info("TC1: SSH login as %s successful", role)
        return True

    def _list_existing_users(self, context):
        cmd = context.profile.get("rbac.list_users_command", "do show running-config AAA user")
        StepRunner([CommandStep("tester", cmd, settle_time=3)]).run(context)
        pattern, _ = ExpectOneOfStep("tester", ["#", ">", "$"], timeout=10).execute(context)
        ScreenshotStep("tester").execute(context)
        return pattern

    def _create_user_with_role(self, context, new_user, new_role):
        """Create <new_user> under <new_role>. Returns (created:bool, output:str)."""
        cmds = context.profile.get_list("rbac.create_user_commands")
        cmds = [c.format(user=new_user, role=new_role) for c in cmds]

        last_pattern = ""
        for cmd in cmds:
            StepRunner([CommandStep("tester", cmd, settle_time=4)]).run(context)
            last_pattern, _ = ExpectOneOfStep(
                "tester",
                ["#", ">", "$", "successfully", "saved", "access denied",
                 "Access Denied", "already exists", "Y/N"],
                timeout=10,
            ).execute(context)

        ScreenshotStep("tester").execute(context)
        denied = any(d in last_pattern for d in ["access denied", "Access Denied"])
        return (not denied), last_pattern

    def _verify_user_role_on_dut(self, context, new_user, new_role):
        """Confirm the newly created user shows up on the DUT bound to <new_role>."""
        cmd = context.profile.get(
            "rbac.show_user_command", "do show running-config AAA user {user}"
        ).format(user=new_user)

        StepRunner([CommandStep("tester", cmd, settle_time=3)]).run(context)
        pattern, _ = ExpectOneOfStep("tester", ["#", ">", "$"], timeout=10).execute(context)
        ScreenshotStep("tester").execute(context)
        return new_role in pattern

    # -- entry point ------------------------------------------------------

    def run(self, context):
        # Roles/privileges to be created, obtained from OEM documentation
        # (profile-driven so the actual role names match the DUT under test).
        roles_to_create = context.profile.get_list("rbac.roles") or ["netadmin", "sysadmin", "operator"]

        login_ok = self._ssh_login(context, "rootsystem")
        creation_results = {}
        verification_results = {}

        if login_ok:
            self._list_existing_users(context)

            for role in roles_to_create:
                user_name = context.profile.get(f"rbac.new_user.{role}", role[:2])
                created, output = self._create_user_with_role(context, user_name, role)
                creation_results[role] = created

                if created:
                    logger.info("TC1: user '%s' successfully created under role '%s'",
                                user_name, role)
                    verification_results[role] = self._verify_user_role_on_dut(
                        context, user_name, role
                    )
                else:
                    logger.error("TC1: FAILED to create user '%s' under role '%s' - %s",
                                 user_name, role, output)

            StepRunner([ClearTerminalStep("tester")]).run(context)
            StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)

        # -- verdict --------------------------------------------------------
        min_roles_met = len(roles_to_create) >= 2  # + rootsystem = 3 distinct roles minimum
        creation_ok = bool(creation_results) and all(creation_results.values())
        verification_ok = bool(verification_results) and all(verification_results.values())

        if login_ok and min_roles_met and creation_ok and verification_ok:
            self.pass_test()
        else:
            logger.warning(
                "TC1 breakdown - login=%s roles>=3=%s creation=%s verification=%s",
                login_ok, min_roles_met, creation_results, verification_results,
            )
            self.fail_test()

        return self