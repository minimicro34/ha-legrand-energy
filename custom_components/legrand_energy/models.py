from dataclasses import dataclass


@dataclass(slots=True)
class LegrandModule:
    id: str
    name: str
    type: str
    bridge: str | None = None
    room: str | None = None
    setup_date: int | None = None