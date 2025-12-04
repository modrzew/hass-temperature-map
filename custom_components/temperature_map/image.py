"""Image platform for Temperature Map."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_ROTATION, CONF_SENSORS, DOMAIN
from .coordinator import TemperatureMapCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Temperature Map image platform from a config entry."""
    # Get the coordinator from hass.data
    coordinator: TemperatureMapCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Get name from config entry data
    name = config_entry.data["name"]

    # Create and add the entity
    async_add_entities([TemperatureMapImage(coordinator, name)])
    _LOGGER.info("Added Temperature Map entity for %s", name)


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

        # Set device info if needed (for grouping in UI)
        # For now, each temperature map is independent

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        # Get config from coordinator's config entry
        config = self.coordinator.config_entry.options
        return {
            "sensors": config.get(CONF_SENSORS, []),
            "rotation": config.get(CONF_ROTATION, 0),
        }

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
