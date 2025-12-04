"""DataUpdateCoordinator for Temperature Map."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TemperatureMapCoordinator(DataUpdateCoordinator[bytes]):
    """Coordinator to manage temperature map updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        config: dict[str, Any],
        update_interval_minutes: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{name}",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.config = config
        self._cached_image: bytes | None = None

    async def _async_update_data(self) -> bytes:
        """Fetch sensor data and render heatmap."""
        try:
            # Gather sensor temperatures from Home Assistant states
            sensor_data = []
            for sensor_config in self.config["sensors"]:
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
                _LOGGER.error(
                    "No valid sensor data available for temperature map. "
                    "Check that your temperature sensors exist and have valid numeric values."
                )
                raise UpdateFailed("No valid sensor data available")

            _LOGGER.debug("Rendering heatmap with %d sensors", len(sensor_data))

            # Run image generation in executor (blocking I/O)
            image_bytes = await self.hass.async_add_executor_job(self._render_heatmap, sensor_data)

            _LOGGER.debug("Successfully rendered heatmap (%d bytes)", len(image_bytes))

            self._cached_image = image_bytes
            return image_bytes

        except Exception as err:
            _LOGGER.exception("Error rendering heatmap")
            raise UpdateFailed(f"Error rendering heatmap: {err}") from err

    def _render_heatmap(self, sensor_data: list[dict]) -> bytes:
        """Render the heatmap image (runs in executor thread)."""
        # Import here to avoid blocking the event loop on startup
        from .heatmap.renderer import render_heatmap_image

        return render_heatmap_image(
            walls=self.config["walls"],
            sensors=sensor_data,
            comfort_min=self.config.get("comfort_min_temp", 20),
            comfort_max=self.config.get("comfort_max_temp", 26),
            ambient_temp=self.config.get("ambient_temp", 22),
            show_names=self.config.get("show_sensor_names", True),
            show_temps=self.config.get("show_sensor_temperatures", True),
            rotation=self.config.get("rotation", 0),
        )
