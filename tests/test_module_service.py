"""Tests for the module discovery service."""

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.legrand_energy.module_service import ModuleService


@pytest.mark.asyncio
async def test_module_service_returns_discovered_modules() -> None:
    """Preserve the discovered module mapping from the API."""
    modules = {"circuit-1": Mock()}
    api = Mock()
    api.discover_modules = AsyncMock(return_value=modules)

    result = await ModuleService(api).async_get()

    assert result is modules
    api.discover_modules.assert_awaited_once_with()
