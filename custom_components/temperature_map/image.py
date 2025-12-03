"""Image platform for Temperature Map."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_UPDATE_INTERVAL, DOMAIN
from .coordinator import TemperatureMapCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Temperature Map image platform."""
    if DOMAIN not in hass.data or "config" not in hass.data[DOMAIN]:
        return

    entities = []
    coordinators = []

    for map_config in hass.data[DOMAIN]["config"]:
        name = map_config["name"]
        update_interval = map_config.get(CONF_UPDATE_INTERVAL, 15)

        coordinator = TemperatureMapCoordinator(hass, name, map_config, update_interval)

        # Store coordinator for service calls
        coordinators.append(coordinator)

        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()

        entities.append(TemperatureMapImage(coordinator, name))

    # Store coordinators for the refresh service
    hass.data[DOMAIN]["coordinators"] = coordinators

    async_add_entities(entities)


class TemperatureMapImage(CoordinatorEntity[TemperatureMapCoordinator], ImageEntity):
    """Image entity for temperature map."""

    _attr_content_type = "image/png"

    def __init__(
        self,
        coordinator: TemperatureMapCoordinator,
        name: str,
    ) -> None:
        """Initialize the image entity."""
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, coordinator.hass)

        self._attr_name = f"Temperature Map {name}"
        self._attr_unique_id = f"temperature_map_{name.lower().replace(' ', '_')}"
        self._attr_image_last_updated = datetime.now()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_image_last_updated = datetime.now()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        return self.coordinator.data
