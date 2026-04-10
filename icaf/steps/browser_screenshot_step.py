"""
steps/browser_screenshot_step.py
──────────────────────────────────────────────────────────────────────────────
Captures a screenshot of the full browser window, including the address bar,
tabs, and all browser chrome — not just the Selenium viewport.

How it works
────────────
Selenium's save_screenshot() captures only the rendered webpage area.  To
include the address bar and OS-level window chrome we use the same
xdotool + scrot approach already used by VisibleTerminal and
WiresharkPacketScreenshotStep:

  1. Ask Selenium for the current page title.
  2. Use xdotool search --name to locate the Firefox window by that title.
  3. Raise + focus the window with xdotool windowactivate.
  4. Capture just that window with scrot --window.
  5. Re-focus the previously active window so the terminal comes back.

Fallback chain
──────────────
• If xdotool is missing  → falls back to save_screenshot() (viewport only).
• If the window is not found within the timeout
    → falls back to save_screenshot() (viewport only).
• Both fallbacks log a warning so the operator knows what happened.

Parameters
──────────
filename : str | None
    Base filename (without directory).  If None, auto-generates
    ``browser_<timestamp>.png``.
caption : str
    Optional evidence caption.
timeout : int
    Seconds to wait for the Firefox window to become findable (default 10).
"""

import shutil
import subprocess
import time

from icaf.core.step import Step
from icaf.utils.logger import logger

# How long to wait after windowactivate before the WM has actually raised it
_RAISE_SETTLE_S = 0.3
# Window-search timeout (seconds)
_DEFAULT_TIMEOUT = 10


def _find_window(title_fragment: str, timeout: int) -> str | None:
    """
    Poll xdotool until a window whose name contains *title_fragment* appears.
    Returns the window-id string, or None on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["xdotool", "search", "--name", title_fragment],
            capture_output=True,
            text=True,
        )
        ids = result.stdout.strip().splitlines()
        if ids:
            return ids[-1]   # last entry = most recently opened match
        time.sleep(0.3)
    return None


def _active_window() -> str | None:
    """Return the currently focused window id, or None."""
    try:
        return subprocess.check_output(
            ["xdotool", "getactivewindow"], text=True
        ).strip()
    except Exception:
        return None


def _focus_window(window_id: str) -> None:
    subprocess.run(
        ["xdotool", "windowactivate", "--sync", window_id],
        check=False,
    )


class BrowserScreenshotStep(Step):
    """
    Capture a screenshot of the full browser window (including address bar).

    Uses xdotool + scrot to capture the OS-level window so that the address
    bar, tabs, and browser toolbar are all included in the evidence image.
    Falls back to Selenium's save_screenshot() if xdotool/scrot are absent.
    """

    def __init__(
        self,
        filename: str | None = None,
        caption: str = "",
        timeout: int = _DEFAULT_TIMEOUT,
    ):
        super().__init__("Browser screenshot")
        self.filename = filename
        self.caption  = caption
        self.timeout  = timeout

    # ------------------------------------------------------------------
    def execute(self, context) -> None:
        clause   = context.clause
        testcase = context.current_testcase
        shot_dir = context.evidence.screenshot_path(clause, testcase)

        fname = self.filename or f"browser_{int(time.time() * 1000)}.png"
        if not fname.endswith(".png"):
            fname += ".png"
        file_path = f"{shot_dir}/{fname}"

        driver = context.browser.driver

        # ── Try full-window capture via xdotool + scrot ────────────────
        if shutil.which("xdotool") and shutil.which("scrot"):
            saved = self._capture_with_scrot(driver, file_path)
            if saved:
                logger.info("BrowserScreenshot saved (full window): %s", file_path)
                context.current_testcase.add_evidence(
                    screenshot=file_path, caption=self.caption
                )
                return

        # ── Fallback: Selenium viewport only ──────────────────────────
        logger.warning(
            "BrowserScreenshotStep: falling back to Selenium save_screenshot "
            "(address bar will NOT be visible). "
            "Install xdotool and scrot for full-window captures."
        )
        driver.save_screenshot(file_path)
        logger.info("BrowserScreenshot saved (viewport only): %s", file_path)
        context.current_testcase.add_evidence(
            screenshot=file_path, caption=self.caption
        )

    # ------------------------------------------------------------------
    def _capture_with_scrot(self, driver, file_path: str) -> bool:
        """
        Focus the Firefox window and capture it with scrot.
        Returns True on success, False if the window could not be found.
        """
        # Use the page title as the search fragment; Firefox appends
        # " — Mozilla Firefox" (or similar) so even a partial match works.
        page_title = driver.title or "Mozilla Firefox"

        # Remember what was focused so we can restore it afterwards
        prev_window_id = _active_window()

        window_id = _find_window(page_title, self.timeout)

        # Title-based search may fail if the page title is very generic
        # (e.g. an empty new-tab page). Try the class name as a fallback.
        if not window_id:
            logger.debug(
                "BrowserScreenshotStep: title search '%s' failed, "
                "trying class 'Firefox'", page_title
            )
            window_id = _find_window("Firefox", self.timeout)

        if not window_id:
            logger.warning(
                "BrowserScreenshotStep: could not locate Firefox window "
                "within %ds — falling back to Selenium screenshot.", self.timeout
            )
            return False

        logger.debug("BrowserScreenshotStep: found window id %s", window_id)

        # Raise the Firefox window so scrot can see it
        _focus_window(window_id)
        time.sleep(_RAISE_SETTLE_S)

        result = subprocess.run(
            ["scrot", "--window", window_id, file_path],
            capture_output=True,
            text=True,
        )

        # Restore the previously focused window (brings terminal back)
        if prev_window_id:
            _focus_window(prev_window_id)

        if result.returncode != 0:
            logger.warning(
                "BrowserScreenshotStep: scrot failed (rc=%d): %s",
                result.returncode, result.stderr.strip()
            )
            return False

        return True