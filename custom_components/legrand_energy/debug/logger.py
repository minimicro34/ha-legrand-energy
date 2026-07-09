"""Legrand Energy debug logger."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from pprint import pformat
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
        data: object | None = None,
    ) -> None:
        """Write one log entry."""

        if not self.enabled:
            return

        try:
            with self._lock:
                with LOG_PATH.open("a", encoding="utf-8") as f:
                    f.write(
                        f"{datetime.now():%Y-%m-%d %H:%M:%S} "
                        f"[{level}] "
                        f"{message}\n"
                    )

                    if data is not None:
                        f.write(pformat(data))
                        f.write("\n")

                    f.write("\n")

        except Exception:
            pass

    def debug(self, message: str, data=None):
        self._write("DEBUG", message, data)

    def info(self, message: str, data=None):
        self._write("INFO", message, data)

    def warning(self, message: str, data=None):
        self._write("WARNING", message, data)

    def error(self, message: str, data=None):
        self._write("ERROR", message, data)

    def api(self, message: str, data=None):
        self._write("API", message, data)

    def exception(self, message: str, err: Exception):
        self._write(
            "EXCEPTION",
            message,
            {
                "type": type(err).__name__,
                "message": str(err),
            },
        )


debug = DebugLogger()