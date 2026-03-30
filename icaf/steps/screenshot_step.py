import os
from datetime import datetime
from icaf.core.step import Step
from icaf.utils.logger import logger


class ScreenshotStep(Step):

    def __init__(self, terminal):
        super().__init__("Capture screenshot")
        self.terminal = terminal

    def _generate_filename(self, context):
        testcase = context.current_testcase
        tc_name = getattr(testcase, "name", "unknown_tc")

        timestamp = datetime.now().strftime("%H%M%S_%f")

        return f"{tc_name}_{self.terminal}_{timestamp}.png"

    def execute(self, context):

        clause = context.clause
        testcase = context.current_testcase

        path = context.evidence.screenshot_path(clause, testcase)

        filename = self._generate_filename(context)
        full_path = os.path.join(path, filename)

        terminal = context.terminal_manager.get_terminal(self.terminal)

        if not terminal:
            raise Exception(f"Terminal not found: {self.terminal}")

        logger.info(f"Taking screenshot: {full_path}")

        # Capture FIRST
        saved_path = terminal.capture(full_path)

        # Store ACTUAL saved path
        context.current_testcase.add_evidence(screenshot=saved_path)

        return saved_path