import shutil
import subprocess
import time
from icaf.utils.logger import logger
from icaf.terminal.base_terminal import BaseTerminal


class VisibleTerminal(BaseTerminal):

    def __init__(self, name):
        super().__init__(name)
        self.session = f"TCAF-{name}"
        self.window_id = None

        # Clean up any preexisting tmux session with the same name
        subprocess.run(
            ["tmux", "kill-session", "-t", self.session],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        logger.info(f"Creating tmux session: {self.session}")
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.session],
            check=True
        )

        # Launch GUI terminal if gnome-terminal is available
        if shutil.which("gnome-terminal"):
            logger.info(f"Launching visible terminal for {self.session}")
            try:
                subprocess.Popen([
                    "gnome-terminal",
                    "--",
                    "tmux",
                    "attach",
                    "-t",
                    self.session
                ])
                # Attempt to find the newly opened window ID
                self.window_id = self._find_window()
            except Exception as e:
                logger.warning(f"Could not open GUI terminal: {e}")
        else:
            logger.warning("gnome-terminal not found. Running headless via tmux.")

        if self.window_id:
            logger.info(f"{self.name} window id: {self.window_id}")
        else:
            logger.warning(f"{self.name} window id not detected (running headless or non-X11)")

    def _find_window(self):
        if not shutil.which("xdotool"):
            logger.warning("xdotool not installed. Window tracking disabled.")
            return None

        logger.info("Searching for terminal window...")

        for _ in range(10):
            time.sleep(0.5)
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
                    return ids[-1]
            except Exception as e:
                logger.debug(f"xdotool search failed: {e}")

        logger.warning("Failed to find terminal window via xdotool")
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

        if not self.window_id or not shutil.which("scrot"):
            logger.warning("GUI screenshot unavailable. Falling back to tmux terminal text capture.")
            return self.capture_output()

        try:
            if shutil.which("xdotool"):
                subprocess.run(
                    ["xdotool", "windowactivate", self.window_id],
                    check=False,
                    stderr=subprocess.DEVNULL
                )

            subprocess.run(
                [
                    "scrot",
                    "-u",
                    "-w",
                    self.window_id,
                    screenshot_path
                ],
                check=True
            )
            return screenshot_path
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None

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