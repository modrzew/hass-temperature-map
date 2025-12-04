"""DataUpdateCoordinator for Temperature Map."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_AMBIENT_TEMP,
    CONF_COMFORT_MAX_TEMP,
    CONF_COMFORT_MIN_TEMP,
    CONF_ROTATION,
    CONF_SENSORS,
    CONF_SHOW_SENSOR_NAMES,
    CONF_SHOW_SENSOR_TEMPERATURES,
    CONF_UPDATE_INTERVAL,
    CONF_WALLS,
    DEFAULT_AMBIENT_TEMP,
    DEFAULT_COMFORT_MAX,
    DEFAULT_COMFORT_MIN,
    DEFAULT_ROTATION,
    DEFAULT_SHOW_SENSOR_NAMES,
    DEFAULT_SHOW_SENSOR_TEMPERATURES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class TemperatureMapCoordinator(DataUpdateCoordinator[bytes]):
    """Coordinator to manage temperature map updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry

        # Get update interval from options
        update_interval_minutes = config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.data['name']}",
            update_interval=timedelta(minutes=update_interval_minutes),
        )

        self._cached_image: bytes | None = None

        # Cache for geometry to detect changes
        self._last_walls: list[dict] | None = None
        self._last_sensors: list[dict] | None = None

    @property
    def _config(self) -> dict[str, Any]:
        """Get the current configuration from config entry options."""
        return self.config_entry.options

    async def async_config_entry_updated(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        _LOGGER.debug("Configuration updated for %s", self.name)

        # Check if update interval changed
        new_interval_minutes = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        new_interval = timedelta(minutes=new_interval_minutes)

        if self.update_interval != new_interval:
            _LOGGER.info(
                "Update interval changed from %s to %s minutes for %s",
                self.update_interval.total_seconds() / 60,
                new_interval_minutes,
                self.name,
            )
            self.update_interval = new_interval

        # Check if geometry changed (walls or sensors)
        new_walls = entry.options.get(CONF_WALLS, [])
        new_sensors = entry.options.get(CONF_SENSORS, [])

        geometry_changed = self._last_walls != new_walls or self._last_sensors != new_sensors

        if geometry_changed:
            _LOGGER.info(
                "Geometry configuration changed for %s, will recompute distance grid", self.name
            )
            # The distance grid cache is internal to the renderer
            # We just need to trigger a refresh

        # Immediately refresh to apply new settings
        await self.async_request_refresh()

    async def _async_update_data(self) -> bytes:
        """Fetch sensor data and render heatmap."""
        try:
            # Get current configuration
            config = self._config

            # Gather sensor temperatures from Home Assistant states
            sensor_data = []
            sensor_configs = config.get(CONF_SENSORS, [])
            total_sensors = len(sensor_configs)
            _LOGGER.debug("Checking %d configured sensors", total_sensors)

            for sensor_config in sensor_configs:
                entity_id = sensor_config["entity"]
                state = self.hass.states.get(entity_id)
                if state is None:
                    _LOGGER.warning("Sensor %s not found in Home Assistant", entity_id)
                    continue
                if state.state in ("unknown", "unavailable"):
                    _LOGGER.debug(
                        "Sensor %s is unavailable (state: %s), skipping", entity_id, state.state
                    )
                    continue
                try:
                    temp = float(state.state)
                    sensor_data.append(
                        {
                            "entity": entity_id,
                            "x": sensor_config["x"],
                            "y": sensor_config["y"],
                            "temp": temp,
                            "label": sensor_config.get(
                                "label", state.attributes.get("friendly_name", entity_id)
                            ),
                        }
                    )
                except ValueError:
                    _LOGGER.warning("Invalid temperature value for %s: %s", entity_id, state.state)

            if not sensor_data:
                _LOGGER.warning(
                    "No valid sensor data available for temperature map (%d configured, 0 available). "
                    "Will render floor plan only. "
                    "Check that your temperature sensors exist and have valid numeric values.",
                    total_sensors,
                )
            else:
                _LOGGER.debug(
                    "Rendering heatmap with %d/%d sensors available",
                    len(sensor_data),
                    total_sensors,
                )

            # Run image generation in executor (blocking I/O)
            image_bytes = await self.hass.async_add_executor_job(self._render_heatmap, sensor_data)

            _LOGGER.debug("Successfully rendered heatmap (%d bytes)", len(image_bytes))

            # Update geometry cache
            self._last_walls = config.get(CONF_WALLS, [])
            self._last_sensors = config.get(CONF_SENSORS, [])

            self._cached_image = image_bytes
            return image_bytes

        except Exception as err:
            _LOGGER.exception("Error rendering heatmap")
            raise UpdateFailed(f"Error rendering heatmap: {err}") from err

    def _render_heatmap(self, sensor_data: list[dict]) -> bytes:
        """Render the heatmap image (runs in executor thread)."""
        # Import here to avoid blocking the event loop on startup
        from .heatmap.renderer import render_heatmap_image

        config = self._config

        return render_heatmap_image(
            walls=config.get(CONF_WALLS, []),
            sensors=sensor_data,
            comfort_min=config.get(CONF_COMFORT_MIN_TEMP, DEFAULT_COMFORT_MIN),
            comfort_max=config.get(CONF_COMFORT_MAX_TEMP, DEFAULT_COMFORT_MAX),
            ambient_temp=config.get(CONF_AMBIENT_TEMP, DEFAULT_AMBIENT_TEMP),
            show_names=config.get(CONF_SHOW_SENSOR_NAMES, DEFAULT_SHOW_SENSOR_NAMES),
            show_temps=config.get(CONF_SHOW_SENSOR_TEMPERATURES, DEFAULT_SHOW_SENSOR_TEMPERATURES),
            rotation=config.get(CONF_ROTATION, DEFAULT_ROTATION),
        )
