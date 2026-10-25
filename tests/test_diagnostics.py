"""Regression tests for sensitive diagnostic field redaction."""

from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.mark.asyncio
async def test_diagnostics_redact_account_and_home_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never export user identity or household location to public issues."""
    diagnostics_module = types.ModuleType("homeassistant.components.diagnostics")

    def redact(data: object, keys: set[str]) -> object:
        if isinstance(data, dict):
            return {
                key: "**REDACTED**" if key in keys else redact(value, keys)
                for key, value in data.items()
            }
        if isinstance(data, list):
            return [redact(value, keys) for value in data]
        return data

    diagnostics_module.async_redact_data = redact
    monkeypatch.setitem(
        sys.modules, "homeassistant.components.diagnostics", diagnostics_module
    )

    # Reuse the real integration's coordinator import, without instantiation.
    module_name = "custom_components.legrand_energy.diagnostics"
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    module = importlib.import_module(module_name)

    payload = {
        "body": {
            "user": {"email": "private@example.com", "id": "private-user"},
            "homes": [
                {
                    "name": "My private home",
                    "coordinates": [43.3, 5.4],
                    "altitude": 100,
                    "modules": [{"type": "NLPC", "battery_percent": 80}],
                }
            ],
        }
    }
    coordinator = Mock()
    coordinator.api.homesdata = AsyncMock(return_value=payload)
    entry = Mock()
    entry.data = {"username": "private@example.com", "web_token": "secret"}
    entry.runtime_data = coordinator

    result = await module.async_get_config_entry_diagnostics(Mock(), entry)

    assert "private@example.com" not in str(result)
    assert "private-user" not in str(result)
    assert "My private home" not in str(result)
    assert "43.3" not in str(result)
    assert result["homesdata"]["body"]["homes"][0]["modules"][0]["type"] == "NLPC"
