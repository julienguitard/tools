"""Chrome tab fetcher via AppleScript."""

from __future__ import annotations

import subprocess

from ..domain import Tab


class ChromeAppleScriptSource:
    """Reads open tabs from Google Chrome using osascript."""

    _SCRIPT = """
    set output to ""
    tell application "Google Chrome"
        repeat with w in every window
            repeat with t in every tab of w
                set output to output & title of t & "||" & URL of t & linefeed
            end repeat
        end repeat
    end tell
    return output
    """

    def fetch_tabs(self) -> list[Tab]:
        result = subprocess.run(
            ["osascript", "-e", self._SCRIPT],
            capture_output=True, text=True, check=True,
        )
        tabs: list[Tab] = []
        for line in result.stdout.strip().splitlines():
            if "||" in line:
                title, url = line.split("||", 1)
                tabs.append(Tab(title=title.strip(), url=url.strip()))
        return tabs
