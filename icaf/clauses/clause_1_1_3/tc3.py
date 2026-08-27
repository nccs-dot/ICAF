"""
TC3 - Allowed Operations Per Role: Verify that the DUT enforces RBAC such
that users can perform ONLY the operations permitted by their own role's
configured policy - checked for every role, against what the DUT itself
declares that role is authorized to do (not a fixed/pre-baked command list).
Clause: 1.1.3 Role Based Access Control
Test Scenario 1.1.3.3

Requirement (ITSAR 1.1.3):
The RBAC system controls how users or groups of users are allowed access to
the various domains and what type of operation (View, Modify, Execute) they
can perform. DUT enforcement must match the role policy the DUT itself
reports.

Reference DUT behaviour (from TSTP evidence for this clause):
  - A role's permitted command-group / functions are readable via
    "show running-config AAA authorization role <role>" and
    "show running-config AAA authorization role command-group".
  - Commands outside a role's declared policy are rejected by the DUT
    (command authorization failure / access denied).
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


class TC3AllowedOperationsPerRole(TestCase):
    protocol = "ssh"

    def __init__(self):
        super().__init__(
            "TC3_ALLOWED_OPERATIONS_PER_ROLE",
            "Verify DUT enforces RBAC so each role can perform only operations per its own policy",
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
            logger.error("TC3: SSH login as %s FAILED", role)
            return False

        logger.info("TC3: SSH login as %s successful", role)
        return True

    def _read_role_policy(self, context, role):
        """
        Read the DUT's own declaration of what <role> is authorized to do
        (its configured command-group / role policy), as an admin.
        Returns the raw policy text captured from the DUT.
        """
        cmd = context.profile.get(
            "rbac.show_role_policy_command",
            "do show running-config AAA authorization role {role}",
        ).format(role=role)

        StepRunner([CommandStep("tester", cmd, settle_time=3)]).run(context)
        policy_text, _ = ExpectOneOfStep(
            "tester", ["#", ">", "$"], timeout=10
        ).execute(context)
        ScreenshotStep("tester").execute(context)
        return policy_text

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

    def _verify_role_against_policy(self, context, role, policy_text):
        """
        Run the full candidate test-command pool for <role>, classify each
        command as 'in policy' or 'not in policy' using the DUT-reported
        policy text, then confirm actual DUT enforcement matches the policy:
          - in-policy commands   -> must succeed
          - not-in-policy commands -> must be denied
        Returns True only if every command's actual result matched what the
        DUT's own policy declaration said it should be.
        """
        test_pool = context.profile.get_list("rbac.test_command_pool")
        matched = True

        for cmd, keyword in test_pool:
            expected_allowed = keyword in policy_text
            actual_allowed, output = self._execute_command(context, cmd)

            if actual_allowed == expected_allowed:
                logger.info(
                    "TC3: %s - command '%s' behaved as declared by policy (allowed=%s)",
                    role, cmd, actual_allowed,
                )
            else:
                logger.error(
                    "TC3: %s - command '%s' MISMATCHED policy (policy_says_allowed=%s, "
                    "actual_allowed=%s) - %s",
                    role, cmd, expected_allowed, actual_allowed, output,
                )
                matched = False

        return matched

    # -- entry point ------------------------------------------------------

    def run(self, context):
        roles = context.profile.get_list("rbac.roles") or ["netadmin", "sysadmin", "operator"]

        # Step 1: read each role's declared policy from an admin session.
        admin_login_ok = self._ssh_login(context, "rootsystem")
        role_policies = {}

        if admin_login_ok:
            for role in roles:
                role_policies[role] = self._read_role_policy(context, role)
            StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)

        # Step 2: for each role, log in as that role and confirm every test
        # command's actual outcome matches what the DUT's own policy declared.
        enforcement_results = {}

        for role in roles:
            policy_text = role_policies.get(role)
            if not policy_text:
                logger.warning("TC3: no policy captured for %s - skipping", role)
                continue

            login_ok = self._ssh_login(context, role)
            if not login_ok:
                logger.warning("TC3: skipping enforcement check - login as %s failed", role)
                continue

            enforcement_results[role] = self._verify_role_against_policy(context, role, policy_text)

            StepRunner([ClearTerminalStep("tester")]).run(context)
            StepRunner([SessionResetStep("tester", post_reset_delay=2)]).run(context)

        # -- verdict --------------------------------------------------------
        policies_captured_ok = bool(role_policies) and all(role_policies.values())
        enforcement_ok = bool(enforcement_results) and all(enforcement_results.values())

        if admin_login_ok and policies_captured_ok and enforcement_ok:
            self.pass_test()
        else:
            logger.warning(
                "TC3 breakdown - policies_captured=%s enforcement=%s",
                {r: bool(p) for r, p in role_policies.items()}, enforcement_results,
            )
            self.fail_test()

        return self