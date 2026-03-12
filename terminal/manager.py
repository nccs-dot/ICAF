from utils.logger import logger
from terminal.visible_terminal import VisibleTerminal
import time


class TerminalManager:
    """
    Manages multiple terminal sessions.
    """

    def __init__(self):
        self.terminals = {}

        logger.info("Terminal Manager initialized")

    def create_terminal(self, name: str):
        """
        Create a new terminal session.
        """

        if name in self.terminals:
            logger.warning(f"Terminal already exists: {name}")
            return self.terminals[name]

        terminal = VisibleTerminal(name)

        self.terminals[name] = terminal

        return terminal

    def get_terminal(self, name: str):
        """
        Retrieve existing terminal.
        """

        return self.terminals.get(name)

    def run(self, terminal_name: str, command: str):
        """
        Execute command on specific terminal.
        """

        terminal = self.get_terminal(terminal_name)

        if not terminal:
            raise Exception(f"Terminal not found: {terminal_name}")

        return terminal.run(command)
    
    def screenshot(self, terminal_name: str):

        terminal = self.get_terminal(terminal_name)

        if not terminal:
            raise Exception("Terminal not found")

        return terminal.capture()
    
    def capture_output(self, terminal_name, stable_checks=5, interval=0.2):

        terminal = self.get_terminal(terminal_name)

        if not terminal:
            return ""

        last_output = ""

        for _ in range(stable_checks):

            current_output = terminal.capture_output()

            if current_output == last_output:
                return current_output

            last_output = current_output
            time.sleep(interval)

        return last_output