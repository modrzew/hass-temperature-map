"""Image platform for Temperature Map."""

from __future__ import annotations

import logging

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

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
        _LOGGER.warning("Temperature Map config not found in hass.data")
        return

    entities = []
    coordinators = []

    for map_config in hass.data[DOMAIN]["config"]:
        name = map_config["name"]
        update_interval = map_config.get(CONF_UPDATE_INTERVAL, 15)

        _LOGGER.info("Setting up Temperature Map: %s", name)

        coordinator = TemperatureMapCoordinator(hass, name, map_config, update_interval)

        # Store coordinator for service calls
        coordinators.append(coordinator)

        # Fetch initial data - now that we fixed the boundary caching,
        # this should complete in 1-2 seconds instead of 60+
        try:
            _LOGGER.debug("Fetching initial data for %s...", name)
            await coordinator.async_refresh()
            _LOGGER.info("Successfully fetched initial data for %s", name)
        except Exception as err:
            _LOGGER.error("Failed to fetch initial data for %s: %s", name, err)
            # Continue anyway - coordinator will retry based on update_interval

        entities.append(TemperatureMapImage(coordinator, name))

    # Store coordinators for the refresh service
    hass.data[DOMAIN]["coordinators"] = coordinators

    async_add_entities(entities)
    _LOGGER.info("Added %d Temperature Map entities", len(entities))


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

        # Don't set image_last_updated until we have actual data
        # Let the coordinator update handle it

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Only update timestamp if we have actual image data
        if self.coordinator.data is not None:
            self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        if self.coordinator.data is None:
            _LOGGER.debug("No image data available yet for %s", self._attr_name)
            return None
        return self.coordinator.data
