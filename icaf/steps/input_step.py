"""
steps/input_step.py
──────────────────────────────────────────────────────────────────────────────
Sends raw text/input to a terminal (no Enter key implied by the step itself —
the underlying tm.run() handles line endings as configured).

capture_evidence parameter
───────────────────────────
By default InputStep does NOT add evidence, preserving the original behaviour.

Set capture_evidence=True when this input completes a multi-prompt flow and
you want the *full* terminal output (command + all prompts + final result)
captured as a single evidence entry.  Classic use-case: ssh-keygen where

    CommandStep("tester", "ssh-keygen ...", capture_evidence=False)   # skip partial output
    ExpectOneOfStep(...)                                               # wait for 'Overwrite?' etc.
    InputStep("tester", "y", capture_evidence=True)                   # capture everything

The evidence entry will show:

    command : [input] y
    output  : <full terminal buffer at the moment of capture>

The command field is prefixed with "[input]" so it is clearly distinguishable
from a CommandStep entry in the report.

Parameters
──────────
terminal        : str   — terminal name registered with TerminalManager
text            : str   — text to send
capture_evidence: bool  — add output to evidence after sleeping (default False)
settle_time     : float — seconds to wait before capturing output when
                          capture_evidence=True (default 3.0, same as original
                          hard-coded sleep)
"""

import time
from icaf.core.step import Step
from icaf.utils.logger import logger


class InputStep(Step):

    def __init__(
        self,
        terminal: str,
        text: str,
        capture_evidence: bool = False,
        settle_time: float = 3.0,
    ):
        super().__init__(f"Input: {text}")
        self.terminal         = terminal
        self.text             = text
        self.capture_evidence = capture_evidence
        self.settle_time      = settle_time

    def execute(self, context):
        tm = context.terminal_manager
        tm.run(self.terminal, self.text)
        time.sleep(self.settle_time)

        if self.capture_evidence:
            output = tm.capture_output(self.terminal)

            # Log first few lines for quick triage (mirrors CommandStep behaviour)
            for line in output.splitlines()[:5]:
                logger.debug("  > %s", line)

            context.current_testcase.add_evidence(
                command=f"[input] {self.text}",
                output=output,
            )
            logger.debug(
                "InputStep: evidence captured after input '%s' (%d chars)",
                self.text,
                len(output),
            )