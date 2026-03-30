"""Terminal-based REPL interface with readline support."""

from __future__ import annotations


class ReadlineUI:
    """Interactive terminal UI with history and tab completion.

    Implements the UserInterface protocol for real terminal interaction.
    """

    _COMMANDS: list[str] = [
        ":reduce", ":step", ":trace",
        ":free", ":bound", ":binding",
        ":random", ":let", ":list",
        ":help", ":quit",
    ]

    def __init__(self) -> None:
        try:
            import readline

            def completer(text: str, state: int) -> str | None:
                matches = [c for c in self._COMMANDS if c.startswith(text)]
                return matches[state] if state < len(matches) else None

            readline.set_completer(completer)
            readline.parse_and_bind("tab: complete")
        except ImportError:
            pass

    def read_input(self) -> str | None:
        """Read one line from the user.

        Returns:
            The input string, or None on EOF / KeyboardInterrupt.
        """
        try:
            return input("λ> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    def display(self, text: str) -> None:
        """Print output to stdout."""
        print(text)

    def display_error(self, text: str) -> None:
        """Print an error message to stdout."""
        print(f"Error: {text}")
