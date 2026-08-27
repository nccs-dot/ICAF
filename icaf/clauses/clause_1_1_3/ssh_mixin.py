"""
ssh_mixin.py — Reusable SSH helpers for Clause 1.1.3 (Role Based Access
Control) test cases.

Follows the same profile-driven pattern as the project's shared SSHMixin,
extended with role-aware helpers since RBAC testing needs to log in as
several different accounts (rootsystem, netadmin, sysadmin, operator, ...)
rather than a single fixed context.ssh_user, and needs to classify each
command outcome as allowed/denied for policy-enforcement checks.

Usage
-----
class TC2RoleCommandAuthorization(TestCase, SSHMixin):
    ...
    def run(self, context):
        ok, pattern = self.ssh_open_role_session(context, "netadmin")
        if not ok:
            self.fail_test()
            return self

        allowed, output = self.ssh_run_command_classify(context, "some command")
        ...
        self.ssh_close_session(context)
"""

from icaf.core.step_runner import StepRunner
from icaf.steps.command_step import CommandStep
from icaf.steps.expect_one_of_step import ExpectOneOfStep
from icaf.steps.input_step import InputStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger


class SSHMixin:
    """
    Profile-driven SSH helpers for RBAC role/command testing.

    All behaviour is controlled by the active profile — no values are
    hard-coded.  The helpers deliberately do NOT call ScreenshotStep so
    callers stay in full control of when screenshots are taken.
    """

    # Markers that indicate a command was denied by RBAC/AAA authorization.
    DENIAL_MARKERS = [
        "% Invalid input",
        "Command authorization failed",
        "access denied",
        "Access Denied",
        "% Authorization failed",
    ]

    # Markers that indicate an SSH login was rejected outright.
    LOGIN_FAILURE_MARKERS = ["Permission denied", "Authentication failed"]

    # ── internal builders ──────────────────────────────────────────────────

    def _build_ssh_cmd(self, context, *, role: str | None = None,
                        extra_flags: list[str] | None = None) -> str:
        """
        Build the SSH command from profile keys:
            ssh.binary          (default "ssh")
            ssh.connect_options (list)
            ssh.target          (template "{user}@{ip}")

        If *role* is given, the username is resolved from
        ``rbac.user.<role>`` (falling back to *role* itself) instead of
        ``context.ssh_user``. Optional *extra_flags* are inserted between
        the options and the target.
        """
        binary = context.profile.get("ssh.binary", "ssh")
        options = context.profile.get_list("ssh.connect_options")
        user = context.profile.get(f"rbac.user.{role}", role) if role else context.ssh_user
        target = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=user, ip=context.ssh_ip
        )
        parts = [binary] + options + (extra_flags or []) + [target]
        return " ".join(parts)

    def _get_role_password(self, context, role: str) -> str:
        """Resolve the password for *role* via ``rbac.password.<role>``."""
        return context.profile.get(f"rbac.password.{role}", context.ssh_password)

    def _get_shell_prompts(self, context) -> list[str]:
        """Return the DUT shell prompt list from the profile."""
        return context.profile.get_list("ssh.shell_prompt") or ["#", ">", "$"]

    def _get_password_prompts(self, context) -> list[str]:
        return context.profile.get_list("ssh.password_prompt")

    # ── session management ────────────────────────────────────────────────

    def ssh_open_session(self, context, *, settle_time: int = 4) -> None:
        """
        Open an SSH session to the DUT using the default context credentials
        (context.ssh_user / context.ssh_password).
        """
        ssh_cmd = self._build_ssh_cmd(context)

        StepRunner([CommandStep("tester", ssh_cmd, settle_time=settle_time)]).run(context)
        ExpectOneOfStep(
            "tester", self._get_password_prompts(context), timeout=10
        ).execute(context)
        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        ExpectOneOfStep(
            "tester", self._get_shell_prompts(context), timeout=10
        ).execute(context)

        logger.debug("SSHMixin: session open to %s", context.ssh_ip)

    def ssh_open_role_session(
        self, context, role: str, *, settle_time: int = 4, timeout: int = 10
    ) -> tuple[bool, str]:
        """
        Open an SSH session to the DUT logging in as *role*
        (resolved via rbac.user.<role> / rbac.password.<role>).

        Returns ``(success: bool, matched_pattern: str)``. Unlike
        ssh_open_session(), this does not raise on login failure — it
        reports the failure back to the caller so a TC can classify and
        continue (e.g. try the next role).
        """
        ssh_cmd = self._build_ssh_cmd(context, role=role)
        role_pass = self._get_role_password(context, role)

        StepRunner([CommandStep("tester", ssh_cmd, settle_time=settle_time)]).run(context)
        ExpectOneOfStep(
            "tester", self._get_password_prompts(context), timeout=timeout
        ).execute(context)
        StepRunner([InputStep("tester", role_pass)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester",
            self._get_shell_prompts(context) + self.LOGIN_FAILURE_MARKERS,
            timeout=timeout,
        ).execute(context)

        if any(f in pattern for f in self.LOGIN_FAILURE_MARKERS):
            logger.error("SSHMixin: SSH login as '%s' FAILED — %s", role, pattern)
            return False, pattern

        logger.info("SSHMixin: SSH login as '%s' successful", role)
        return True, pattern

    def ssh_close_session(self, context, *, post_reset_delay: int = 2) -> None:
        """Cleanly close the current SSH session via SessionResetStep."""
        StepRunner([SessionResetStep("tester", post_reset_delay=post_reset_delay)]).run(context)
        logger.debug("SSHMixin: session closed")

    def ssh_clear_terminal(self, context) -> None:
        StepRunner([ClearTerminalStep("tester")]).run(context)

    # ── command execution ─────────────────────────────────────────────────

    def ssh_run_commands(
        self,
        context,
        commands: list[str | tuple[str, list[str]]],
        *,
        settle_time: int = 2,
        timeout: int = 10,
    ) -> None:
        """
        Execute a list of commands on an already-open SSH session.

        Each element can be:
          • a plain string  → command; shell prompt expected after
          • a (cmd, [expected_patterns]) tuple → command with custom expected list
        """
        shell_p = self._get_shell_prompts(context)

        for item in commands:
            if isinstance(item, tuple):
                cmd, expected = item
            else:
                cmd, expected = item, shell_p

            StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
            ExpectOneOfStep("tester", expected, timeout=timeout).execute(context)

    def ssh_run_formatted_commands(
        self,
        context,
        commands: list[str],
        fmt_kwargs: dict,
        *,
        settle_time: int = 2,
        timeout: int = 10,
    ) -> None:
        """
        Like ssh_run_commands but calls str.format(**fmt_kwargs) on each
        command string before sending. Useful for profile-driven command
        lists containing placeholders such as {user} or {role}.
        """
        shell_p = self._get_shell_prompts(context)
        for cmd in commands:
            formatted = cmd.format(**fmt_kwargs)
            StepRunner([CommandStep("tester", formatted, settle_time=settle_time)]).run(context)
            ExpectOneOfStep(
                "tester",
                shell_p + ["successfully", "saved", "already exists", "Y/N"],
                timeout=timeout,
            ).execute(context)

    def ssh_run_show_command(
        self, context, cmd: str, *, settle_time: int = 3, timeout: int = 10
    ) -> str:
        """
        Run a read-only 'show'-style command and return the captured output.
        Does not classify allow/deny — just returns the raw prompt text.
        """
        StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester", self._get_shell_prompts(context), timeout=timeout
        ).execute(context)
        return pattern

    def ssh_run_command_classify(
        self,
        context,
        cmd: str,
        *,
        settle_time: int = 4,
        timeout: int = 10,
        extra_denial_markers: list[str] | None = None,
    ) -> tuple[bool, str]:
        """
        Run a single command and classify the result as allowed/denied
        based on DENIAL_MARKERS (plus any *extra_denial_markers*).

        Returns ``(allowed: bool, output: str)``.
        """
        extra_denial_markers = extra_denial_markers or []
        shell_p = self._get_shell_prompts(context)

        StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester",
            shell_p + self.DENIAL_MARKERS + extra_denial_markers,
            timeout=timeout,
        ).execute(context)

        denied = any(d in pattern for d in self.DENIAL_MARKERS + extra_denial_markers)
        return (not denied), pattern

    # ── DUT local user lifecycle ────────────────────────────────────────────

    def dut_create_user(
        self,
        context,
        *,
        username: str,
        role: str | None = None,
        settle_time: int = 4,
        timeout: int = 10,
        extra_expect: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Create a local user via profile-driven commands
        (``rbac.create_user_commands`` if *role* is given, otherwise
        ``rbac.create_user_no_role_commands``).

        Returns ``(outcome, output)`` where outcome is one of:
          "created"  — DUT accepted the creation
          "rejected" — DUT refused the creation outright
          "unknown"  — neither a clear success nor a clear rejection
        """
        extra_expect = extra_expect or []
        key = "rbac.create_user_commands" if role else "rbac.create_user_no_role_commands"
        commands = context.profile.get_list(key)
        fmt_kwargs = {"user": username, "role": role} if role else {"user": username}
        commands = [c.format(**fmt_kwargs) for c in commands]

        shell_p = self._get_shell_prompts(context)
        rejected_markers = [
            "% Incomplete command", "% Invalid input", "role required",
            "Role is mandatory", "access denied", "Access Denied",
        ]
        success_markers = ["successfully", "saved"]

        last_pattern = ""
        for cmd in commands:
            StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
            last_pattern, _ = ExpectOneOfStep(
                "tester",
                shell_p + rejected_markers + success_markers +
                ["already exists", "Y/N"] + extra_expect,
                timeout=timeout,
            ).execute(context)

        if any(m in last_pattern for m in rejected_markers):
            return "rejected", last_pattern
        if any(m in last_pattern for m in success_markers):
            return "created", last_pattern
        return "unknown", last_pattern

    def dut_delete_user(self, context, *, username: str, settle_time: int = 3,
                         timeout: int = 10) -> None:
        """Delete a local user using the profile-driven delete command."""
        cmd = context.profile.get("rbac.delete_user_command", "no AAA user {user}").format(
            user=username
        )
        StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
        ExpectOneOfStep("tester", self._get_shell_prompts(context), timeout=timeout).execute(context)
        self.ssh_clear_terminal(context)
        logger.info("SSHMixin: local user '%s' deleted from DUT", username)

    def dut_get_user_role(self, context, *, username: str, settle_time: int = 3,
                           timeout: int = 10) -> str:
        """
        Read back the role assigned to *username* via
        ``rbac.show_user_command`` (default "do show running-config AAA user {user}").
        Returns the raw output text for the caller to inspect.
        """
        cmd = context.profile.get(
            "rbac.show_user_command", "do show running-config AAA user {user}"
        ).format(user=username)
        return self.ssh_run_show_command(context, cmd, settle_time=settle_time, timeout=timeout)

    def dut_get_role_policy(self, context, *, role: str, settle_time: int = 3,
                             timeout: int = 10) -> str:
        """
        Read the DUT's own declaration of what *role* is authorized to do,
        via ``rbac.show_role_policy_command``
        (default "do show running-config AAA authorization role {role}").
        """
        cmd = context.profile.get(
            "rbac.show_role_policy_command",
            "do show running-config AAA authorization role {role}",
        ).format(role=role)
        return self.ssh_run_show_command(context, cmd, settle_time=settle_time, timeout=timeout)"""
ssh_mixin.py — Reusable SSH helpers for Clause 1.1.3 (Role Based Access
Control) test cases.

Follows the same profile-driven pattern as the project's shared SSHMixin,
extended with role-aware helpers since RBAC testing needs to log in as
several different accounts (rootsystem, netadmin, sysadmin, operator, ...)
rather than a single fixed context.ssh_user, and needs to classify each
command outcome as allowed/denied for policy-enforcement checks.

Usage
-----
class TC2RoleCommandAuthorization(TestCase, SSHMixin):
    ...
    def run(self, context):
        ok, pattern = self.ssh_open_role_session(context, "netadmin")
        if not ok:
            self.fail_test()
            return self

        allowed, output = self.ssh_run_command_classify(context, "some command")
        ...
        self.ssh_close_session(context)
"""

from icaf.core.step_runner import StepRunner
from icaf.steps.command_step import CommandStep
from icaf.steps.expect_one_of_step import ExpectOneOfStep
from icaf.steps.input_step import InputStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger


class SSHMixin:
    """
    Profile-driven SSH helpers for RBAC role/command testing.

    All behaviour is controlled by the active profile — no values are
    hard-coded.  The helpers deliberately do NOT call ScreenshotStep so
    callers stay in full control of when screenshots are taken.
    """

    # Markers that indicate a command was denied by RBAC/AAA authorization.
    DENIAL_MARKERS = [
        "% Invalid input",
        "Command authorization failed",
        "access denied",
        "Access Denied",
        "% Authorization failed",
    ]

    # Markers that indicate an SSH login was rejected outright.
    LOGIN_FAILURE_MARKERS = ["Permission denied", "Authentication failed"]

    # ── internal builders ──────────────────────────────────────────────────

    def _build_ssh_cmd(self, context, *, role: str | None = None,
                        extra_flags: list[str] | None = None) -> str:
        """
        Build the SSH command from profile keys:
            ssh.binary          (default "ssh")
            ssh.connect_options (list)
            ssh.target          (template "{user}@{ip}")

        If *role* is given, the username is resolved from
        ``rbac.user.<role>`` (falling back to *role* itself) instead of
        ``context.ssh_user``. Optional *extra_flags* are inserted between
        the options and the target.
        """
        binary = context.profile.get("ssh.binary", "ssh")
        options = context.profile.get_list("ssh.connect_options")
        user = context.profile.get(f"rbac.user.{role}", role) if role else context.ssh_user
        target = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=user, ip=context.ssh_ip
        )
        parts = [binary] + options + (extra_flags or []) + [target]
        return " ".join(parts)

    def _get_role_password(self, context, role: str) -> str:
        """Resolve the password for *role* via ``rbac.password.<role>``."""
        return context.profile.get(f"rbac.password.{role}", context.ssh_password)

    def _get_shell_prompts(self, context) -> list[str]:
        """Return the DUT shell prompt list from the profile."""
        return context.profile.get_list("ssh.shell_prompt") or ["#", ">", "$"]

    def _get_password_prompts(self, context) -> list[str]:
        return context.profile.get_list("ssh.password_prompt")

    # ── session management ────────────────────────────────────────────────

    def ssh_open_session(self, context, *, settle_time: int = 4) -> None:
        """
        Open an SSH session to the DUT using the default context credentials
        (context.ssh_user / context.ssh_password).
        """
        ssh_cmd = self._build_ssh_cmd(context)

        StepRunner([CommandStep("tester", ssh_cmd, settle_time=settle_time)]).run(context)
        ExpectOneOfStep(
            "tester", self._get_password_prompts(context), timeout=10
        ).execute(context)
        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        ExpectOneOfStep(
            "tester", self._get_shell_prompts(context), timeout=10
        ).execute(context)

        logger.debug("SSHMixin: session open to %s", context.ssh_ip)

    def ssh_open_role_session(
        self, context, role: str, *, settle_time: int = 4, timeout: int = 10
    ) -> tuple[bool, str]:
        """
        Open an SSH session to the DUT logging in as *role*
        (resolved via rbac.user.<role> / rbac.password.<role>).

        Returns ``(success: bool, matched_pattern: str)``. Unlike
        ssh_open_session(), this does not raise on login failure — it
        reports the failure back to the caller so a TC can classify and
        continue (e.g. try the next role).
        """
        ssh_cmd = self._build_ssh_cmd(context, role=role)
        role_pass = self._get_role_password(context, role)

        StepRunner([CommandStep("tester", ssh_cmd, settle_time=settle_time)]).run(context)
        ExpectOneOfStep(
            "tester", self._get_password_prompts(context), timeout=timeout
        ).execute(context)
        StepRunner([InputStep("tester", role_pass)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester",
            self._get_shell_prompts(context) + self.LOGIN_FAILURE_MARKERS,
            timeout=timeout,
        ).execute(context)

        if any(f in pattern for f in self.LOGIN_FAILURE_MARKERS):
            logger.error("SSHMixin: SSH login as '%s' FAILED — %s", role, pattern)
            return False, pattern

        logger.info("SSHMixin: SSH login as '%s' successful", role)
        return True, pattern

    def ssh_close_session(self, context, *, post_reset_delay: int = 2) -> None:
        """Cleanly close the current SSH session via SessionResetStep."""
        StepRunner([SessionResetStep("tester", post_reset_delay=post_reset_delay)]).run(context)
        logger.debug("SSHMixin: session closed")

    def ssh_clear_terminal(self, context) -> None:
        StepRunner([ClearTerminalStep("tester")]).run(context)

    # ── command execution ─────────────────────────────────────────────────

    def ssh_run_commands(
        self,
        context,
        commands: list[str | tuple[str, list[str]]],
        *,
        settle_time: int = 2,
        timeout: int = 10,
    ) -> None:
        """
        Execute a list of commands on an already-open SSH session.

        Each element can be:
          • a plain string  → command; shell prompt expected after
          • a (cmd, [expected_patterns]) tuple → command with custom expected list
        """
        shell_p = self._get_shell_prompts(context)

        for item in commands:
            if isinstance(item, tuple):
                cmd, expected = item
            else:
                cmd, expected = item, shell_p

            StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
            ExpectOneOfStep("tester", expected, timeout=timeout).execute(context)

    def ssh_run_formatted_commands(
        self,
        context,
        commands: list[str],
        fmt_kwargs: dict,
        *,
        settle_time: int = 2,
        timeout: int = 10,
    ) -> None:
        """
        Like ssh_run_commands but calls str.format(**fmt_kwargs) on each
        command string before sending. Useful for profile-driven command
        lists containing placeholders such as {user} or {role}.
        """
        shell_p = self._get_shell_prompts(context)
        for cmd in commands:
            formatted = cmd.format(**fmt_kwargs)
            StepRunner([CommandStep("tester", formatted, settle_time=settle_time)]).run(context)
            ExpectOneOfStep(
                "tester",
                shell_p + ["successfully", "saved", "already exists", "Y/N"],
                timeout=timeout,
            ).execute(context)

    def ssh_run_show_command(
        self, context, cmd: str, *, settle_time: int = 3, timeout: int = 10
    ) -> str:
        """
        Run a read-only 'show'-style command and return the captured output.
        Does not classify allow/deny — just returns the raw prompt text.
        """
        StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester", self._get_shell_prompts(context), timeout=timeout
        ).execute(context)
        return pattern

    def ssh_run_command_classify(
        self,
        context,
        cmd: str,
        *,
        settle_time: int = 4,
        timeout: int = 10,
        extra_denial_markers: list[str] | None = None,
    ) -> tuple[bool, str]:
        """
        Run a single command and classify the result as allowed/denied
        based on DENIAL_MARKERS (plus any *extra_denial_markers*).

        Returns ``(allowed: bool, output: str)``.
        """
        extra_denial_markers = extra_denial_markers or []
        shell_p = self._get_shell_prompts(context)

        StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
        pattern, _ = ExpectOneOfStep(
            "tester",
            shell_p + self.DENIAL_MARKERS + extra_denial_markers,
            timeout=timeout,
        ).execute(context)

        denied = any(d in pattern for d in self.DENIAL_MARKERS + extra_denial_markers)
        return (not denied), pattern

    # ── DUT local user lifecycle ────────────────────────────────────────────

    def dut_create_user(
        self,
        context,
        *,
        username: str,
        role: str | None = None,
        settle_time: int = 4,
        timeout: int = 10,
        extra_expect: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Create a local user via profile-driven commands
        (``rbac.create_user_commands`` if *role* is given, otherwise
        ``rbac.create_user_no_role_commands``).

        Returns ``(outcome, output)`` where outcome is one of:
          "created"  — DUT accepted the creation
          "rejected" — DUT refused the creation outright
          "unknown"  — neither a clear success nor a clear rejection
        """
        extra_expect = extra_expect or []
        key = "rbac.create_user_commands" if role else "rbac.create_user_no_role_commands"
        commands = context.profile.get_list(key)
        fmt_kwargs = {"user": username, "role": role} if role else {"user": username}
        commands = [c.format(**fmt_kwargs) for c in commands]

        shell_p = self._get_shell_prompts(context)
        rejected_markers = [
            "% Incomplete command", "% Invalid input", "role required",
            "Role is mandatory", "access denied", "Access Denied",
        ]
        success_markers = ["successfully", "saved"]

        last_pattern = ""
        for cmd in commands:
            StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
            last_pattern, _ = ExpectOneOfStep(
                "tester",
                shell_p + rejected_markers + success_markers +
                ["already exists", "Y/N"] + extra_expect,
                timeout=timeout,
            ).execute(context)

        if any(m in last_pattern for m in rejected_markers):
            return "rejected", last_pattern
        if any(m in last_pattern for m in success_markers):
            return "created", last_pattern
        return "unknown", last_pattern

    def dut_delete_user(self, context, *, username: str, settle_time: int = 3,
                         timeout: int = 10) -> None:
        """Delete a local user using the profile-driven delete command."""
        cmd = context.profile.get("rbac.delete_user_command", "no AAA user {user}").format(
            user=username
        )
        StepRunner([CommandStep("tester", cmd, settle_time=settle_time)]).run(context)
        ExpectOneOfStep("tester", self._get_shell_prompts(context), timeout=timeout).execute(context)
        self.ssh_clear_terminal(context)
        logger.info("SSHMixin: local user '%s' deleted from DUT", username)

    def dut_get_user_role(self, context, *, username: str, settle_time: int = 3,
                           timeout: int = 10) -> str:
        """
        Read back the role assigned to *username* via
        ``rbac.show_user_command`` (default "do show running-config AAA user {user}").
        Returns the raw output text for the caller to inspect.
        """
        cmd = context.profile.get(
            "rbac.show_user_command", "do show running-config AAA user {user}"
        ).format(user=username)
        return self.ssh_run_show_command(context, cmd, settle_time=settle_time, timeout=timeout)

    def dut_get_role_policy(self, context, *, role: str, settle_time: int = 3,
                             timeout: int = 10) -> str:
        """
        Read the DUT's own declaration of what *role* is authorized to do,
        via ``rbac.show_role_policy_command``
        (default "do show running-config AAA authorization role {role}").
        """
        cmd = context.profile.get(
            "rbac.show_role_policy_command",
            "do show running-config AAA authorization role {role}",
        ).format(role=role)
        return self.ssh_run_show_command(context, cmd, settle_time=settle_time, timeout=timeout)