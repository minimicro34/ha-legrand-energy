from dataclasses import dataclass


@dataclass(slots=True)
class LegrandModule:
    id: str
    name: str
    type: str
    bridge: str | None = None