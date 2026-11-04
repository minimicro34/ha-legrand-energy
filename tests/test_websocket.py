"""Tests for the cached Netatmo history WebSocket endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.legrand_energy.coordinator import LegrandEnergyCoordinator
from custom_components.legrand_energy.websocket import (
    async_cached_history,
    async_register,
)

START = "2026-11-04T00:00:00+00:00"
END = "2026-11-04T12:00:00+00:00"


def _request(**changes: object) -> dict[str, object]:
    message: dict[str, object] = {
        "id": 1,
        "type": "legrand_energy/cached_history",
        "entry_id": "entry-1",
        "start": START,
        "end": END,
    }
    message.update(changes)
    return message


@pytest.mark.asyncio
async def test_returns_cached_points_without_api_call(hass) -> None:
    connection = MagicMock()
    entry = MagicMock()
    entry.domain = "legrand_energy"
    coordinator = MagicMock(spec=LegrandEnergyCoordinator)
    coordinator.cached_energy_history.return_value = [
        {"timestamp": START, "energy_kwh": 0.5, "interval_seconds": 1500}
    ]
    entry.runtime_data = coordinator

    with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
        await async_cached_history(hass, connection, _request())

    coordinator.cached_energy_history.assert_called_once_with(
        start=datetime(2026, 11, 4, tzinfo=UTC),
        end=datetime(2026, 11, 4, 12, tzinfo=UTC),
    )
    connection.send_result.assert_called_once_with(
        1, {"points": coordinator.cached_energy_history.return_value}
    )
    connection.send_error.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("entry_domain", [None, "other_integration"])
async def test_rejects_missing_or_foreign_entry(hass, entry_domain) -> None:
    connection = MagicMock()
    entry = None if entry_domain is None else MagicMock(domain=entry_domain)
    with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
        await async_cached_history(hass, connection, _request())

    connection.send_error.assert_called_once_with(
        1, "not_found", "Legrand Energy entry not found"
    )
    connection.send_result.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("not-a-date", END),
        (START, "not-a-date"),
        ("2026-11-04T00:00:00", END),
        (END, START),
        (START, START),
        ("2025-01-01T00:00:00+00:00", END),
    ],
)
async def test_rejects_invalid_windows(hass, start: str, end: str) -> None:
    connection = MagicMock()
    entry = MagicMock()
    entry.domain = "legrand_energy"
    with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
        await async_cached_history(
            hass, connection, _request(start=start, end=end)
        )

    connection.send_error.assert_called_once_with(
        1, "invalid_range", "Invalid history date range"
    )


@pytest.mark.asyncio
async def test_rejects_unready_coordinator(hass) -> None:
    connection = MagicMock()
    entry = MagicMock()
    entry.domain = "legrand_energy"
    entry.runtime_data = None
    with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
        await async_cached_history(hass, connection, _request())

    connection.send_error.assert_called_once_with(
        1, "not_ready", "Legrand Energy is not ready"
    )


def test_registers_websocket_command(hass) -> None:
    with patch(
        "custom_components.legrand_energy.websocket.websocket_api.async_register_command"
    ) as register:
        async_register(hass)

    register.assert_called_once_with(hass, async_cached_history)
