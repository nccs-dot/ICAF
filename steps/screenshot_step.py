import subprocess
from core.step import Step
from utils.logger import logger


class ScreenshotStep(Step):

    def __init__(self, terminal):

        super().__init__("Capture screenshot")
        self.terminal = terminal

    def execute(self, context):

        clause = context.clause
        testcase = context.current_testcase

        path = context.evidence.screenshot_path(clause, testcase)

        file = f"{path}/{self.terminal}.png"

        terminal = context.terminal_manager.get_terminal(self.terminal)

        if not terminal:
            raise Exception(f"Terminal not found: {self.terminal}")

        logger.info(f"Taking screenshot of terminal: {self.terminal}")

        context.current_testcase.add_evidence(screenshot=file)

        return terminal.capture(file)