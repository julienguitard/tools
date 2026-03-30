"""Non-interactive UI for script file execution."""

from __future__ import annotations


class ScriptUI:
    """Reads from a list of statements, skipping comments and blanks.

    Implements the UserInterface protocol for batch script execution.
    """

    def __init__(self, lines: list[str]) -> None:
        self._lines = iter(lines)

    def read_input(self) -> str | None:
        """Return the next non-comment, non-blank line, or None at end."""
        for line in self._lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            return stripped
        return None

    def display(self, text: str) -> None:
        """Print output to stdout."""
        print(text)

    def display_error(self, text: str) -> None:
        """Print an error message to stdout."""
        print(f"Error: {text}")
