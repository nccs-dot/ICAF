import subprocess
import time
from core.step import Step
from utils.logger import logger


class ScreenshotStep(Step):

    def __init__(self, terminal, suffix=""):
        super().__init__("Capture screenshot")
        self.terminal = terminal
        self.suffix = f"_{suffix}" if suffix else ""

    def execute(self, context):
        clause = context.clause
        testcase = context.current_testcase
        path = context.evidence.screenshot_path(clause, testcase)

        base_name = f"{self.terminal}{self.suffix}.png"
        timestamped_name = context.evidence.get_timestamped_filename(base_name)
        screenshot_file = f"{path}/{timestamped_name}"

        terminal = context.terminal_manager.get_terminal(self.terminal)
        if not terminal:
            raise Exception(f"Terminal not found: {self.terminal}")

        # Get window ID from the terminal object
        window_id = terminal.window_id

        logger.info(f"Maximizing terminal {self.terminal} for screenshot")
        subprocess.run(["xdotool", "windowactivate", str(window_id)])
        subprocess.run(["xdotool", "key", "F11"])
        time.sleep(0.5)

        logger.info(f"Capturing screenshot: {screenshot_file}")
        subprocess.run(["scrot", screenshot_file])

        # Restore original window size
        subprocess.run(["xdotool", "key", "F11"])
        time.sleep(0.3)

        logger.info(f"Screenshot saved: {screenshot_file}")
        return screenshot_file
