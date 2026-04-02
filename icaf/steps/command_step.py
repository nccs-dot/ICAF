"""
steps/command_step.py
──────────────────────────────────────────────────────────────────────────────
Sends a command to a terminal and captures the resulting output.

Improvements over original
───────────────────────────
• Accepts an optional settle_time parameter.  After sending the command,
  waits up to settle_time seconds for output to stop changing before
  capturing — eliminates the race condition where capture_output fires
  before the command has printed anything.
• Stores both command and output on the evidence object as before.
• Logs the first 5 lines of output at DEBUG level for quick triage.
• capture_evidence parameter: set to False to skip adding evidence for this
  step. Useful when a subsequent InputStep will capture the complete output
  instead (e.g. key generation where the interesting output appears only
  after the 'y' confirmation prompt is answered).
"""

import time
from icaf.core.step import Step
from icaf.utils.logger import logger

_DEFAULT_SETTLE   = 1.5   # seconds
_POLL_INTERVAL    = 0.3   # seconds between output-stability checks
_STABILITY_PASSES = 2     # how many consecutive identical reads = stable


class CommandStep(Step):
    """
    Run a command on a terminal and capture its output.

    Parameters
    ----------
    terminal : str
        Terminal name as registered with the TerminalManager.
    command : str
        Shell command to send.
    settle_time : float
        Maximum seconds to wait for output to stabilise.  Defaults to 1.5 s.
    capture_evidence : bool
        Whether to add the captured output to the test case evidence.
        Defaults to True.  Set to False when a following InputStep will
        capture the complete output (e.g. multi-prompt flows such as
        ssh-keygen where the meaningful output only appears after the user
        answers an interactive prompt).
    """

    def __init__(
        self,
        terminal: str,
        command: str,
        settle_time: float = _DEFAULT_SETTLE,
        capture_evidence: bool = True,
    ):
        super().__init__(f"Run command: {command}")
        self.terminal         = terminal
        self.command          = command
        self.settle_time      = settle_time
        self.capture_evidence = capture_evidence

    def execute(self, context) -> None:
        tm = context.terminal_manager

        # Send the command
        tm.run(self.terminal, self.command)

        # ── Wait for output to stabilise ──────────────────────────────────
        deadline      = time.time() + self.settle_time
        stable_count  = 0
        previous_out  = ""

        while time.time() < deadline:
            time.sleep(_POLL_INTERVAL)
            current_out = tm.capture_output(self.terminal)
            if current_out == previous_out:
                stable_count += 1
                if stable_count >= _STABILITY_PASSES:
                    break
            else:
                stable_count = 0
                previous_out = current_out

        output = tm.capture_output(self.terminal)

        # Log first few lines for quick triage
        preview_lines = output.splitlines()[:5]
        for line in preview_lines:
            logger.debug("  > %s", line)

        # Record evidence (skip if caller owns evidence capture downstream)
        if self.capture_evidence:
            context.current_testcase.add_evidence(
                command=self.command,
                output=output,
            )
        else:
            logger.debug(
                "CommandStep: evidence capture skipped for '%s' "
                "(capture_evidence=False — a downstream InputStep should capture)",
                self.command,
            )