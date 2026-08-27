"""
icaf/terminal/terminal_renderer.py

Pillow-based terminal renderer.
Receives commands and their real outputs via add_command_with_prompt() /
add_output() and renders a realistic dark terminal PNG.
"""

import os
from PIL import Image, ImageDraw, ImageFont

from icaf.utils.logger import logger

# ── Colour palette ────────────────────────────────────────────────────────────
_BG          = (15,  15,  25)     # near-black background
_C_PROMPT    = (80,  220, 120)    # green prompt (root@localhost:~#)
_C_COMMAND   = (220, 220, 255)    # white-ish command text
_C_OUTPUT    = (180, 210, 230)    # light-blue output text
_C_DIM       = (110, 120, 140)    # password prompt / dim lines
_C_SEPARATOR = (60,  80,  110)    # faint blue separator
_C_CURSOR    = (80,  220, 120)    # blinking-cursor colour
_LINE_H      = 22                 # pixels per text line
_PADDING     = 40                 # left/top/bottom margin
_WIDTH       = 1280               # image width


class TerminalRenderer:
    """
    Accumulates terminal lines and renders them as a PNG image.

    Line types stored internally:
        ("prompt",  text)   — prompt + command on one line
        ("output",  text)   — command output line
        ("raw",     text, color_key)  — pre-coloured raw line
        ("sep",     text)   — faint separator between test cases
    """

    MAX_LINES = 80  # keep the most recent N lines

    def __init__(self):
        self._lines: list = []
        self._font = self._load_font(16)
        self._font_bold = self._load_font(16, bold=True)

    # ── Public API ────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Reset the line buffer (call between test cases if needed)."""
        self._lines.clear()

    def add_command_with_prompt(self, prompt: str, command: str) -> None:
        """
        Add a prompt + command line, e.g.:
            root@localhost:~# cat /etc/shadow
        """
        self._push(("prompt", prompt, command))

    def add_output(self, output: str) -> None:
        """Add one or more output lines (splits on newlines automatically)."""
        for line in str(output).splitlines():
            self._push(("output", line))

    def add_raw_line(self, text: str, color: str = "output", newline: bool = True) -> None:
        """
        Add a pre-coloured line (for login banners, etc.).
        color: "prompt" | "command" | "output" | "dim" | "separator"
        """
        self._push(("raw", text, color, newline))

    def add_separator(self, label: str = "") -> None:
        """Add a faint separator line between test cases."""
        sep = f"─── {label} " + "─" * max(0, 60 - len(label))
        self._push(("sep", sep))

    def render(self, filepath: str) -> str:
        """
        Render the current line buffer to a PNG file.
        Returns the filepath on success, empty string on failure.
        """
        try:
            visible = self._lines[-self.MAX_LINES:]
            height  = _PADDING + len(visible) * _LINE_H + _PADDING + _LINE_H  # +cursor row
            img     = Image.new("RGB", (_WIDTH, max(height, 120)), _BG)
            draw    = ImageDraw.Draw(img)

            y = _PADDING
            for entry in visible:
                y = self._draw_line(draw, entry, y)

            # Blinking cursor
            draw.text((_PADDING, y), "█", font=self._font, fill=_C_CURSOR)

            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            img.save(filepath)
            logger.info(f"[renderer] Saved: {filepath}")
            return filepath
        except Exception as exc:
            logger.error(f"[renderer] Render failed: {exc}")
            return ""

    # ── Internal helpers ──────────────────────────────────────────────────

    def _push(self, entry) -> None:
        self._lines.append(entry)
        # Trim oldest lines if over limit
        if len(self._lines) > self.MAX_LINES * 2:
            self._lines = self._lines[-self.MAX_LINES:]

    def _draw_line(self, draw: ImageDraw.ImageDraw, entry, y: int) -> int:
        kind = entry[0]

        if kind == "prompt":
            _, prompt, command = entry
            # Draw prompt in green, then command in white — same line
            pw = self._text_width(draw, prompt + " ")
            draw.text((_PADDING, y), prompt + " ", font=self._font_bold, fill=_C_PROMPT)
            draw.text((_PADDING + pw, y), command, font=self._font, fill=_C_COMMAND)

        elif kind == "output":
            _, text = entry
            draw.text((_PADDING, y), text, font=self._font, fill=_C_OUTPUT)

        elif kind == "raw":
            _, text, color = entry[0], entry[1], entry[2]
            c = {
                "prompt":    _C_PROMPT,
                "command":   _C_COMMAND,
                "output":    _C_OUTPUT,
                "dim":       _C_DIM,
                "separator": _C_SEPARATOR,
            }.get(color, _C_OUTPUT)
            draw.text((_PADDING, y), text, font=self._font, fill=c)

        elif kind == "sep":
            _, text = entry
            draw.text((_PADDING, y), text, font=self._font, fill=_C_SEPARATOR)

        return y + _LINE_H

    def _text_width(self, draw: ImageDraw.ImageDraw, text: str) -> int:
        try:
            bbox = draw.textbbox((0, 0), text, font=self._font_bold)
            return bbox[2] - bbox[0]
        except Exception:
            return len(text) * 9  # rough fallback for default font

    @staticmethod
    def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono{}.ttf".format(
                "-Bold" if bold else ""
            ),
            "/usr/share/fonts/truetype/liberation/LiberationMono{}-Regular.ttf".format(
                "" if not bold else "-Bold"
            ),
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-{}.ttf".format(
                "B" if bold else "R"
            ),
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()


# Module-level singleton imported by clause.py and tc files
terminal_renderer = TerminalRenderer()