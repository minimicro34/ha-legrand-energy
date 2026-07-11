"""Legrand Energy debug logger."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock

LOG_PATH = Path("/config/legrand_energy.log")


class DebugLogger:
    """Simple debug logger."""

    enabled = True
    _lock = Lock()

    def _write(
        self,
        level: str,
        message: str,
        *args: object,
    ) -> None:
        """Write a log entry."""
        formatted_message = message % args if args else message

        try:
            with self._lock, LOG_PATH.open("a", encoding="utf-8") as file:
                file.write(
                    f"{datetime.now():%Y-%m-%d %H:%M:%S} "
                    f"[{level}] {formatted_message}\n"
                )
        except OSError:
            return

    def debug(self, message: str, *args: object) -> None:
        """Write a debug message."""
        self._write("DEBUG", message, *args)

    def info(self, message: str, *args: object) -> None:
        """Write an information message."""
        self._write("INFO", message, *args)

    def warning(self, message: str, *args: object) -> None:
        """Write a warning message."""
        self._write("WARNING", message, *args)

    def error(self, message: str, *args: object) -> None:
        """Write an error message."""
        self._write("ERROR", message, *args)

    def exception(self, message: str, *args: object) -> None:
        """Write an exception message."""
        self._write("EXCEPTION", message, *args)

    def critical(self, message: str, *args: object) -> None:
        """Write a critical message."""
        self._write("CRITICAL", message, *args)


debug = DebugLogger()
