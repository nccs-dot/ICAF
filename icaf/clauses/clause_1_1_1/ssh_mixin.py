"""
ssh_mixin.py — Reusable SSH/SFTP helpers for all test cases.

Any TestCase can inherit from SSHMixin (alongside TestCase) to get
profile-driven SSH and SFTP operations without duplicating code.

Usage
-----
class TC3SSHMutualAuth(TestCase, SSHMixin):
    ...
    def run(self, context):
        self.ssh_open_session(context)
        self.ssh_run_commands(context, ["display ssh server status"])
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
    Profile-driven SSH and SFTP helpers.

    All behaviour is controlled by the active profile — no values are
    hard-coded.  The helpers deliberately do NOT call ScreenshotStep so
    callers stay in full control of when screenshots are taken.
    """

    # ── internal builders ──────────────────────────────────────────────────

    def _build_ssh_cmd(self, context, *, extra_flags: list[str] | None = None) -> str:
        """
        Build the SSH command from profile keys:
            ssh.base          (default "ssh")
            ssh.connect_options (list)
            ssh.target          (template "{user}@{ip}")
        Optional *extra_flags* are inserted between the options and the target.
        """
        base  = context.profile.get("ssh.base", "ssh")
        options = context.profile.get_list("ssh.connect_options")
        target  = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=context.ssh_user, ip=context.ssh_ip
        )
        parts = [base] + options + (extra_flags or []) + [target]
        return " ".join(parts)

    def _build_sftp_cmd(self, context) -> str:
        """
        Build the SFTP command from profile keys:
            ssh.connect_options (reused — same StrictHostKeyChecking etc.)
            ssh.target          (template "{user}@{ip}")
        """
        options = context.profile.get_list("ssh.connect_options")
        target  = context.profile.get("ssh.target", "{user}@{ip}").format(
            user=context.ssh_user, ip=context.ssh_ip
        )
        return " ".join(["sftp"] + options + [target])

    def _get_shell_prompts(self, context) -> list[str]:
        """Return the DUT shell prompt list from the profile."""
        return context.profile.get_list("ssh.shell_prompt") or ["#", ">", "$"]

    def _get_password_prompts(self, context) -> list[str]:
        return context.profile.get_list("ssh.password_prompt")

    # ── session management ────────────────────────────────────────────────

    def ssh_open_session(self, context, *, settle_time: int = 4) -> None:
        """
        Open an SSH session to the DUT (password-based).

        Sends the SSH command, waits for the password prompt, submits the
        password, then waits for a shell prompt.  A single TimeoutError
        propagates to the caller if any step does not match in time.
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

    def ssh_close_session(self, context, *, post_reset_delay: int = 2) -> None:
        """Cleanly close the current SSH session via SessionResetStep."""
        StepRunner([SessionResetStep("tester", post_reset_delay=post_reset_delay)]).run(context)
        logger.debug("SSHMixin: session closed")

    def ssh_become_root(
        self,
        context,
        *,
        root_password: str,
        timeout: int = 10,
    ):
        """
        Escalate privileges using 'su -' and switch to root shell.
        """

        logger.debug("SSHMixin: escalating to root using su -")

        # Run su -
        StepRunner([CommandStep("tester", "sudo su -", capture_evidence=False)]).run(context)

        # Wait for password prompt
        ExpectOneOfStep(
            "tester",
            ["Password", "password"],
            timeout=timeout,
        ).execute(context)

        # Send root password
        StepRunner([InputStep("tester", root_password)]).run(context)
        

        # Wait for root shell OR failure
        pattern, _ = ExpectOneOfStep(
            "tester",
            self._get_shell_prompts(context) + ["Authentication failure", "su: Authentication failure"],
            timeout=timeout,
        ).execute(context)

        if "failure" in pattern.lower():
            raise Exception("Failed to escalate to root via su -")

        logger.debug("SSHMixin: now running as root")

    # ── command execution ─────────────────────────────────────────────────

    def ssh_run_commands(
        self,
        context,
        commands,
        *,
        fmt_kwargs: dict | None = None,
        settle_time: int = 2,
        timeout: int = 10,
        terminal: str = "tester",          # ← new param
    ):
        shell_p = self._get_shell_prompts(context)

        error_patterns = (
            context.profile.get("ssh.error_classification.transport", []) +
            context.profile.get("ssh.error_classification.negotiation", []) +
            context.profile.get("ssh.error_classification.authentication", []) +
            context.profile.get("ssh.error_classification.authorization", []) +
            context.profile.get("ssh.error_classification.command", []) +
            ["Error", "error", "Invalid", "Unrecognized", "Failed", "Incomplete", "command not found"]
        )

        for item in commands:
            if isinstance(item, (tuple, list)):
                cmd, expected = item
            else:
                cmd, expected = item, shell_p

            if fmt_kwargs:
                cmd = cmd.format(**fmt_kwargs)

            logger.debug(f"SSHMixin: executing → {cmd}")

            StepRunner([CommandStep(terminal, cmd, settle_time=settle_time, capture_evidence=False)]).run(context)

            patterns = expected + error_patterns

            pattern, _ = ExpectOneOfStep(
                terminal,
                patterns,
                timeout=timeout,
            ).execute(context)

            if any(err.lower() in pattern.lower() for err in error_patterns):
                logger.error(f"SSH command failed → {cmd} → {pattern}")
                raise Exception(f"Command failed on DUT: {cmd} → {pattern}")


    def ssh_run_formatted_commands(
        self,
        context,
        commands: list[str],
        fmt_kwargs: dict,
        *,
        settle_time: int = 2,
        timeout: int = 10,
        terminal: str = "tester",          # ← new param
    ) -> None:
        shell_p = self._get_shell_prompts(context)
        for cmd in commands:
            formatted = cmd.format(**fmt_kwargs)
            StepRunner([CommandStep(terminal, formatted, settle_time=settle_time)]).run(context)
            ExpectOneOfStep(
                terminal,
                shell_p + ["successfully", "overwrite", "saved", "Y/N"],
                timeout=timeout,
            ).execute(context)
    # ── pubkey SSH ────────────────────────────────────────────────────────

    def ssh_open_pubkey_session(
        self,
        context,
        *,
        key_path: str,
        remote_user: str,
        settle_time: int = 4,
        timeout: int = 15,
    ) -> tuple[bool, str]:
        """
        Attempt a public-key SSH login.
 
        Returns ``(success: bool, matched_pattern: str)``.
 
        Extra flags used::
 
            -o IdentitiesOnly=yes -i <key_path>
 
        The target is ``<remote_user>@<context.ssh_ip>`` instead of the
        default ``ssh.target`` so the caller can log in as a different user
        (e.g. the pubkey test user) while the admin credentials stay on
        context.
 
        Password-prompt fallback
        ------------------------
        Some DUTs fall back to password authentication even when a key is
        offered (misconfigured ``AuthenticationMethods``, interim firmware,
        etc.).  If the DUT issues a password prompt this method:
 
        1. Logs a warning so the anomaly is visible in the test report.
        2. Sends the context password **once** — this keeps TC4 working if
           the DUT happens to accept the key AND a password in sequence.
        3. If the DUT then reaches a shell prompt → returns ``(True, pattern)``
           but the warning stays in the log so the behaviour is not silently
           swallowed.
        4. If the DUT rejects the password after prompting → treated as an
           auth failure and returns ``(False, pattern)`` like any other
           rejection.
 
        The ``ssh.pubkey_password_fallback`` profile key (bool, default
        ``false``) can be set to ``true`` to suppress the warning for DUTs
        where this behaviour is expected and intentional.
        """
        options = context.profile.get_list("ssh.connect_options")
        extra   = ["-o", "IdentitiesOnly=yes", "-i", key_path]
        base  = context.profile.get("ssh.base", "ssh")
        ssh_cmd = " ".join([base] + options + extra + [f"{remote_user}@{context.ssh_ip}"])
 
        success_p  = context.profile.get_list("ssh.success_prompt") or ["#", "$", ">", "sys"]
        pass_p     = self._get_password_prompts(context)
        fail_p     = (
            context.profile.get("ssh.error_classification.transport",     []) +
            context.profile.get("ssh.error_classification.negotiation",   []) +
            context.profile.get("ssh.error_classification.authentication",[]) +
            context.profile.get("ssh.error_classification.authorization", [])
        )
 
        suppress_warning = context.profile.get("ssh.pubkey_password_fallback", False)
 
        StepRunner([CommandStep("tester", ssh_cmd, settle_time=settle_time)]).run(context)
 
        pattern, _ = ExpectOneOfStep(
            "tester", success_p + pass_p + fail_p, timeout=timeout
        ).execute(context)
 
        # ── unexpected password prompt ─────────────────────────────────────
        if pattern in pass_p:
            if not suppress_warning:
                logger.warning(
                    "SSHMixin: pubkey login received a password prompt — "
                    "DUT may have fallen back to password auth "
                    "(key_path=%s, user=%s). "
                    "Set ssh.pubkey_password_fallback=true in the profile to suppress.",
                    key_path, remote_user,
                )
 
            # Send the context password and wait for the final outcome
            StepRunner([InputStep("tester", context.ssh_password)]).run(context)
            pattern, _ = ExpectOneOfStep(
                "tester", success_p + fail_p, timeout=timeout
            ).execute(context)
 
        return (pattern in success_p), pattern

    # ── SFTP ──────────────────────────────────────────────────────────────

    def sftp_upload(
        self,
        context,
        local_path: str,
        remote_path: str,
        *,
        settle_time: int = 4,
        upload_timeout: int = 20,
    ) -> None:
        """
        Open an SFTP session, upload *local_path* to *remote_path*, then
        close the session.

        Reuses ssh.connect_options and ssh.target from the profile so the
        same StrictHostKeyChecking / port settings apply.
        """
        sftp_cmd = self._build_sftp_cmd(context)

        StepRunner([CommandStep("tester", sftp_cmd, settle_time=settle_time)]).run(context)
        ExpectOneOfStep(
            "tester", self._get_password_prompts(context), timeout=10
        ).execute(context)
        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        ExpectOneOfStep("tester", ["sftp>"], timeout=10).execute(context)

        StepRunner([InputStep("tester", f"put {local_path} {remote_path}")]).run(context)
        ExpectOneOfStep("tester", ["100%", "Uploading", "sftp>"], timeout=upload_timeout).execute(context)

        StepRunner([InputStep("tester", "exit")]).run(context)
        logger.debug("SSHMixin: uploaded '%s' → '%s'", local_path, remote_path)

    def sftp_upload_multiple(
        self,
        context,
        files: list[tuple[str, str]],
        *,
        settle_time: int = 4,
        upload_timeout: int = 20,
    ) -> None:
        """
        Open one SFTP session and upload multiple (local, remote) pairs.

        More efficient than calling sftp_upload() repeatedly when you
        have several files to transfer (e.g. TC8's grpc.p12 and ca.pem).
        """
        sftp_cmd = self._build_sftp_cmd(context)

        StepRunner([CommandStep("tester", sftp_cmd, settle_time=settle_time)]).run(context)
        ExpectOneOfStep(
            "tester", self._get_password_prompts(context), timeout=10
        ).execute(context)
        StepRunner([InputStep("tester", context.ssh_password)]).run(context)
        ExpectOneOfStep("tester", ["sftp>"], timeout=10).execute(context)

        for local_path, remote_path in files:
            StepRunner([InputStep("tester", f"put {local_path} {remote_path}")]).run(context)
            ExpectOneOfStep(
                "tester", ["100%", "Uploading", "sftp>"], timeout=upload_timeout
            ).execute(context)
            logger.debug("SSHMixin: uploaded '%s' → '%s'", local_path, remote_path)

        StepRunner([InputStep("tester", "exit")]).run(context)

     # ── DUT local user lifecycle ──────────────────────────────────────────
 
    def dut_create_local_user(
        self,
        context,
        *,
        username: str,
        password: str,
        role: str = "network-operator",
        service_type: str = "ssh",
    ) -> None:
        """
        Create a local user using profile-driven commands.
        """

        commands = context.profile.get_list("user_mgmt.create_commands")
        StepRunner([ClearTerminalStep("tester")]).run(context)

        self.ssh_open_session(context)

        # NEW: become root
        self.ssh_become_root(
            context,
            root_password=context.ssh_password
        )

        self.ssh_run_commands(
            context,
            commands,
            fmt_kwargs={
                "username": username,
                "password": password,
                "role": role,
                "service_type": service_type,
            },
        )

        self.ssh_close_session(context)
        self.ssh_close_session(context)

        logger.info("SSHMixin: local user '%s' created on DUT", username)


    def dut_delete_local_user(self, context, *, username: str) -> None:
        """
        Delete a local user using profile-driven commands.
        """

        commands = context.profile.get_list("user_mgmt.delete_commands")

        self.ssh_open_session(context)

        # become root
        self.ssh_become_root(
            context,
            root_password=context.ssh_password
        )

        self.ssh_run_commands(
            context,
            commands,
            fmt_kwargs={
                "username": username,
            },
        )

        self.ssh_close_session(context)
        self.ssh_close_session(context)

        logger.info("SSHMixin: local user '%s' deleted from DUT", username)

    # ── error classification ───────────────────────────────────────────────

    def classify_ssh_failure(self, context, output: str) -> str:
        """
        Map a raw SSH output string to a failure layer using the
        ``ssh.error_classification`` profile key.

        Returns one of: "transport", "negotiation", "authentication",
        "authorization", or "unknown".
        """
        classes = context.profile.get("ssh.error_classification", {})
        for layer, patterns in classes.items():
            for p in patterns:
                if p.lower() in output.lower():
                    return layer
        return "unknown"

    def log_ssh_failure(self, context, tc_label: str, pattern: str) -> None:
        """
        Classify *pattern* and emit a structured error log line.

        Example output::

            TC4 FAIL [L3]: Public key rejected — Permission denied (publickey)
        """
        layer_labels = {
            "transport":      "[L1]: Network / transport failure",
            "negotiation":    "[L2]: SSH negotiation failure",
            "authentication": "[L3]: Authentication rejected",
            "authorization":  "[L4]: Auth succeeded but no access",
            "unknown":        "[UNKNOWN]: Unclassified failure",
        }
        layer = self.classify_ssh_failure(context, pattern)
        label = layer_labels.get(layer, "[UNKNOWN]")
        logger.error("%s FAIL %s — %s", tc_label, label, pattern)