"""
icaf/terminal/visible_terminal.py
Commands now EXECUTE in the visible terminal AND mirror to the renderer.
"""

import os
import shutil
import subprocess
import time
from icaf.utils.logger import logger
from icaf.terminal.base_terminal import BaseTerminal
from icaf.terminal.terminal_renderer import terminal_renderer   # import singleton


class VisibleTerminal(BaseTerminal):
    # Alpine prompt shown in renderer
    PROMPT = "root@alpine:~#"

    # Last-resort fallback values only - used if no credentials are passed in.
    _FALLBACK_IP = "192.168.56.101"
    _FALLBACK_USER = "root"
    _FALLBACK_PASSWORD = "Root@Alpine1"

    def __init__(self, name, ssh_ip=None, ssh_user=None, ssh_password=None):
        super().__init__(name)
        self.session = f"TCAF-{name}"
        self.window_id = None

        self.ssh_ip = ssh_ip or self._FALLBACK_IP
        self.ssh_user = ssh_user or self._FALLBACK_USER
        self.ssh_password = ssh_password or self._FALLBACK_PASSWORD

        if not ssh_ip or not ssh_user or not ssh_password:
            logger.warning(
                "VisibleTerminal(%s): missing ssh_ip/ssh_user/ssh_password - "
                "falling back to hardcoded defaults (ip=%s, user=%s). "
                "Pass real credentials via TerminalManager.create_terminal().",
                name, self.ssh_ip, self.ssh_user,
            )

        self._open_session()

    def _get_active_window_id(self):
        """Safely fetch active window ID without crashing in headless/Wayland environments."""
        if not shutil.which("xdotool"):
            return None

        # Ensure DISPLAY is available
        if not os.environ.get("DISPLAY"):
            return None

        try:
            return subprocess.check_output(
                ["xdotool", "getactivewindow"],
                stderr=subprocess.DEVNULL,
                timeout=2
            ).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def _open_session(self):
        """Create the tmux session + optional gnome-terminal window and log in."""
        logger.info("Opening visible Alpine terminal...")

        # Kill old session if lingering
        subprocess.run(
            ["tmux", "kill-session", "-t", self.session],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )

        # Create tmux session detached
        subprocess.run(["tmux", "new-session", "-d", "-s", self.session])

        # Attempt to launch visible GUI terminal if DISPLAY and gnome-terminal are available
        has_display = bool(os.environ.get("DISPLAY"))
        has_gnome_term = bool(shutil.which("gnome-terminal"))

        if has_display and has_gnome_term:
            try:
                subprocess.Popen([
                    "gnome-terminal", "--title", f"TCAF Live — {self.name}",
                    "--geometry", "150x60",
                    "--", "tmux", "attach-session", "-t", self.session
                ])
                time.sleep(2.0)
                self.window_id = self._get_active_window_id()
            except Exception as e:
                logger.warning(f"[VisibleTerminal] Could not launch GUI terminal ({e}). Running detached.")
        else:
            logger.info("[VisibleTerminal] Running in headless/background tmux mode (no GUI window mapped).")

        self._auto_login()

    def _session_alive(self) -> bool:
        """Check whether the tmux session for this terminal still exists."""
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return result.returncode == 0

    def _ensure_session_alive(self):
        """Recreate the session if it died unexpectedly."""
        if not self._session_alive():
            logger.warning(
                "[VisibleTerminal] Session '%s' is dead — recreating and logging back in.",
                self.session,
            )
            self._open_session()

    def _auto_login(self):
        """Log into the target DUT using dynamic SSH parameters."""
        logger.info("Logging into Alpine DUT (%s@%s)...", self.ssh_user, self.ssh_ip)

        ssh_cmd = f"ssh -o StrictHostKeyChecking=no {self.ssh_user}@{self.ssh_ip}"

        subprocess.run([
            "tmux", "send-keys", "-t", self.session,
            ssh_cmd, "Enter"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)

        terminal_renderer.add_raw_line(ssh_cmd, color="dim")

        subprocess.run([
            "tmux", "send-keys", "-t", self.session,
            self.ssh_password, "Enter"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

        terminal_renderer.add_raw_line("(login)", color="dim")

    def run(self, command, screenshot_path=None):
        """Execute in visible terminal AND mirror to renderer."""
        self._ensure_session_alive()

        logger.info(f"[VisibleTerminal] Executing: {command}")

        # 1. Mirror command to renderer
        terminal_renderer.add_command_with_prompt(self.PROMPT, command)

        # 2. Send to tmux
        try:
            subprocess.run([
                "tmux", "send-keys", "-t", self.session, command, "Enter"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"[VisibleTerminal] send-keys failed: {e}")
            return

        # 3. Wait for execution
        time.sleep(2.0)

        # 4. Capture pane output and push to renderer
        output = self._capture_pane_output()
        if output:
            terminal_renderer.add_output(output)
            logger.info(f"[VisibleTerminal] Captured {len(output.splitlines())} output lines")
        else:
            logger.warning("[VisibleTerminal] No output captured from pane")

        # 5. Re-render the PNG
        if screenshot_path:
            terminal_renderer.render(screenshot_path)

    def _capture_pane_output(self) -> str:
        """Capture recent lines from the tmux pane."""
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", self.session, "-p", "-S", "-20"],
                capture_output=True, text=True, timeout=5
            )
            raw = result.stdout

            lines = raw.splitlines()
            while lines and not lines[-1].strip():
                lines.pop()

            # Filter prompts
            if lines and lines[-1].strip().startswith(self.PROMPT.split(":")[0]):
                lines.pop()

            lines = [
                l for l in lines
                if not (l.strip().startswith("root@") and "#" in l)
            ]

            return "\n".join(lines[-15:])
        except Exception as e:
            logger.error(f"[VisibleTerminal] pane capture failed: {e}")
            return ""

    def capture_output(self) -> str:
        """Return the current tmux pane content as a string."""
        if not self._session_alive():
            logger.warning("[VisibleTerminal] capture_output: session '%s' is dead", self.session)
            return ""

        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", self.session, "-p", "-S", "-50"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout
        except Exception as e:
            logger.error(f"[VisibleTerminal] capture_output failed: {e}")
            return ""

    def capture(self, screenshot_path):
        """Capture the visible window via scrot (if available) AND render the Pillow terminal."""
        terminal_renderer.render(screenshot_path)

        if shutil.which("scrot") and os.environ.get("DISPLAY"):
            try:
                subprocess.run(
                    ["scrot", "-u", "-o", f"{screenshot_path}.real.png"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
            except Exception:
                pass

        return screenshot_path