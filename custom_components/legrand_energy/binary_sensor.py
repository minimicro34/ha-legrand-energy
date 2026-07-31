"""Binary sensors for Legrand Energy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
)

from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity, get_main_module_id
from .models import LegrandEnergyData


@dataclass(frozen=True, kw_only=True)
class LegrandBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Legrand Energy binary sensor."""

    value_fn: Callable[[LegrandEnergyData], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[LegrandBinarySensorDescription, ...] = (
    LegrandBinarySensorDescription(
        key="off_peak",
        translation_key="off_peak",
        value_fn=lambda data: (
            data.tariff.is_off_peak if data.tariff is not None else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Legrand Energy binary sensors."""
    coordinator: LegrandEnergyCoordinator = entry.runtime_data
    main_module_id = get_main_module_id(coordinator)

    if main_module_id is None:
        return

    entity_registry = er.async_get(hass)
    safe_module_id = main_module_id.replace(":", "_").replace("#", "_")
    obsolete_unique_ids = (
        f"{main_module_id}_peak",
        f"{DOMAIN}_{safe_module_id}_peak",
    )
    for unique_id in obsolete_unique_ids:
        obsolete_entity_id = entity_registry.async_get_entity_id(
            Platform.BINARY_SENSOR,
            DOMAIN,
            unique_id,
        )
        if obsolete_entity_id is not None:
            entity_registry.async_remove(obsolete_entity_id)

    async_add_entities(
        LegrandBinarySensor(
            coordinator,
            main_module_id,
            description,
        )
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class LegrandBinarySensor(LegrandEntity, BinarySensorEntity):
    """Representation of a Legrand Energy binary sensor."""

    entity_description: LegrandBinarySensorDescription

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
        description: LegrandBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, module_id)
        self.entity_description = description
        self._attr_unique_id = f"{module_id}_{description.key}"

    @property
    def available(self) -> bool:
        """Return whether the binary sensor is available."""
        return super().available and self.coordinator.data.tariff is not None

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        return self.entity_description.value_fn(self.coordinator.data)
