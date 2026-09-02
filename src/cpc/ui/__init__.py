"""Character Performance Capture Desktop Interface."""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    if name == "main":
        from .app import main

        return main
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["main"]
