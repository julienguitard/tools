"""Concrete implementations wired at the composition root."""

from __future__ import annotations

from .memory_names import InMemoryNameRegistry
from .random_gen import RandomTermGenerator
from .readline_ui import ReadlineUI
from .script_ui import ScriptUI

__all__ = [
    "InMemoryNameRegistry",
    "RandomTermGenerator",
    "ReadlineUI",
    "ScriptUI",
]
