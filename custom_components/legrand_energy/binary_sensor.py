"""Binary sensors for Legrand Energy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity


@dataclass(frozen=True, kw_only=True)
class LegrandBinarySensorDescription(BinarySensorEntityDescription):
    """Legrand binary sensor description."""

    value_fn: Callable[[LegrandEnergyCoordinator], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[LegrandBinarySensorDescription, ...] = (
    LegrandBinarySensorDescription(
        key="bridge_online",
        translation_key="bridge_online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: bool(coordinator.data),
    ),
    LegrandBinarySensorDescription(
        key="tic_connected",
        translation_key="tic_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: _get_tic_status(coordinator),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Legrand Energy binary sensors."""
    coordinator: LegrandEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    bridge_id = next(
        (module_id for module_id, module in coordinator.data.items() if module.bridge is None),
        None,
    )

    if bridge_id is None:
        return

    async_add_entities(
        LegrandBinarySensor(coordinator, bridge_id, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class LegrandBinarySensor(LegrandEntity, BinarySensorEntity):
    """Legrand binary sensor."""

    entity_description: LegrandBinarySensorDescription

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
        description: LegrandBinarySensorDescription,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, module_id)
        self.entity_description = description
        safe_module_id = module_id.replace(":", "_").replace("#", "_")
        self._attr_unique_id = f"{DOMAIN}_{safe_module_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def is_on(self) -> bool | None:
        """Return state."""
        return self.entity_description.value_fn(self.coordinator)


def _get_tic_status(coordinator: LegrandEnergyCoordinator) -> bool | None:
    """Return TIC status if available."""
    homestatus: dict[str, Any] | None = getattr(coordinator, "homestatus", None)

    if not homestatus:
        return None

    modules = homestatus.get("body", {}).get("home", {}).get("modules", [])
    for module in modules:
        if module.get("bridge") is None and "tic_link_state" in module:
            return module.get("tic_link_state")

    return None