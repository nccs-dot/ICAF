import subprocess
import time
from icaf.utils.logger import logger
from icaf.terminal.base_terminal import BaseTerminal


class VisibleTerminal(BaseTerminal):

    def __init__(self, name):

        super().__init__(name)

        self.session = f"TCAF-{name}"

        logger.info(f"Creating tmux session: {self.session}")

        subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.session]
        )

        logger.info(f"Launching visible terminal for {self.session}")

        subprocess.Popen([
            "gnome-terminal",
            "--full-screen",
            "--",
            "tmux",
            "attach",
            "-t",
            self.session
        ])

        time.sleep(1.5)

        self.window_id = subprocess.check_output(
            ["xdotool", "getactivewindow"]
        ).decode().strip()

        logger.info(f"{self.name} window id: {self.window_id}")

    def _find_window(self):

        logger.info("Searching for terminal window...")

        for _ in range(30):

            try:

                result = subprocess.run(
                    [
                        "xdotool",
                        "search",
                        "--onlyvisible",
                        "--class",
                        "Gnome-terminal"
                    ],
                    capture_output=True,
                    text=True
                )

                ids = result.stdout.strip().split()

                if ids:
                    window_id = ids[-1]

                    logger.info(f"{self.name} window id: {window_id}")

                    return window_id

            except Exception as e:
                logger.debug(f"xdotool search failed: {e}")

            time.sleep(0.5)

        logger.error("Failed to find terminal window")

        return None

    def run(self, command):

        logger.info(f"[{self.name}] {command}")

        subprocess.run([
            "tmux",
            "send-keys",
            "-t",
            self.session,
            command,
            "Enter"
        ])

    def capture(self, screenshot_path):

        logger.info(f"Capturing screenshot: {screenshot_path}")

        if not self.window_id:
            logger.error("No window ID found for terminal")
            return None

        subprocess.run(["xdotool", "windowactivate", self.window_id])

        subprocess.run(
            [
                "scrot",
                "-u",
                "-w",
                self.window_id,
                screenshot_path
            ]
        )

        return screenshot_path
    
    def capture_output(self):

        result = subprocess.run(
            [
                "tmux",
                "capture-pane",
                "-t",
                self.session,
                "-p"
            ],
            capture_output=True,
            text=True
        )

        return result.stdout