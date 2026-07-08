"""Buttons for Legrand Energy."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Legrand Energy buttons."""
    coordinator: LegrandEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    bridge_id = next(
        (module_id for module_id, module in coordinator.data.items() if module.bridge is None),
        None,
    )

    if bridge_id is not None:
        async_add_entities([LegrandRefreshButton(coordinator, bridge_id)])


class LegrandRefreshButton(LegrandEntity, ButtonEntity):
    """Refresh button."""

    _attr_translation_key = "refresh"
    _attr_icon = "mdi:refresh"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
    ) -> None:
        """Initialize refresh button."""
        super().__init__(coordinator, module_id)
        safe_module_id = module_id.replace(":", "_").replace("#", "_")
        self._attr_unique_id = f"{DOMAIN}_{safe_module_id}_refresh"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_request_refresh()