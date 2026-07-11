"""Binary sensors for Legrand Energy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity
from .models import LegrandEnergyData


@dataclass(frozen=True, kw_only=True)
class LegrandBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor description."""

    value_fn: Callable[[LegrandEnergyData], bool | None]


BINARY_SENSOR_DESCRIPTIONS = (
    LegrandBinarySensorDescription(
        key="off_peak",
        translation_key="off_peak",
        value_fn=lambda data: (
            data.tariff.is_off_peak if data.tariff is not None else None
        ),
    ),
    LegrandBinarySensorDescription(
        key="peak",
        translation_key="peak",
        value_fn=lambda data: (
            not data.tariff.is_off_peak if data.tariff is not None else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: LegrandEnergyCoordinator = entry.runtime_data

    bridge_id = next(
        (
            module_id
            for module_id, module in coordinator.data.modules.items()
            if module.bridge is None
        ),
        None,
    )

    if bridge_id is None:
        return

    async_add_entities(
        LegrandBinarySensor(
            coordinator,
            bridge_id,
            description,
        )
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
        """Initialize."""
        super().__init__(coordinator, module_id)
        self.entity_description = description
        self._attr_has_entity_name = True

        safe_module_id = module_id.replace(":", "_").replace("#", "_")
        self._attr_unique_id = f"{DOMAIN}_{safe_module_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.coordinator.data.tariff is not None

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        return self.entity_description.value_fn(self.coordinator.data)
