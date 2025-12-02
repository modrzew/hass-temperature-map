# Home Assistant Custom Integration Code Guide

This document explains how to write Home Assistant custom integration code. Use this as a reference when implementing the temperature map integration.

## Directory Structure

```
custom_components/your_integration/
├── __init__.py      # Required: Integration setup
├── manifest.json    # Required: Integration metadata
├── const.py         # Constants (DOMAIN, defaults)
├── coordinator.py   # DataUpdateCoordinator for polling
├── image.py         # Platform file for image entities
└── services.yaml    # Optional: Service definitions
```

## manifest.json

```json
{
  "domain": "temperature_map",
  "name": "Temperature Map",
  "version": "1.0.0",
  "documentation": "https://github.com/...",
  "dependencies": [],
  "codeowners": ["@yourusername"],
  "iot_class": "local_polling",
  "requirements": ["Pillow>=10.0.0"]
}
```

**Important fields:**
- `domain`: Must match directory name and DOMAIN constant
- `version`: Required for custom integrations (not for core)
- `iot_class`: Use `"local_polling"` for integrations that poll local sensors
- `requirements`: Python packages to install (use sparingly, prefer stdlib)

## __init__.py - Integration Setup

```python
"""The Temperature Map integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_WALLS, CONF_SENSORS, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Platforms this integration provides
PLATFORMS: list[Platform] = [Platform.IMAGE]

# YAML configuration schema
WALL_SCHEMA = vol.Schema({
    vol.Required("x1"): cv.positive_int,
    vol.Required("y1"): cv.positive_int,
    vol.Required("x2"): cv.positive_int,
    vol.Required("y2"): cv.positive_int,
})

SENSOR_SCHEMA = vol.Schema({
    vol.Required("entity"): cv.entity_id,
    vol.Required("x"): cv.positive_int,
    vol.Required("y"): cv.positive_int,
    vol.Optional("label"): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Schema({
        vol.Required(CONF_NAME): cv.string,
        vol.Optional("update_interval", default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
        vol.Optional("comfort_min_temp", default=20): vol.Coerce(float),
        vol.Optional("comfort_max_temp", default=26): vol.Coerce(float),
        vol.Optional("ambient_temp", default=22): vol.Coerce(float),
        vol.Optional("show_sensor_names", default=True): cv.boolean,
        vol.Optional("show_sensor_temperatures", default=True): cv.boolean,
        vol.Optional("rotation", default=0): vol.In([0, 90, 180, 270]),
        vol.Required(CONF_WALLS): vol.All(cv.ensure_list, [WALL_SCHEMA]),
        vol.Required(CONF_SENSORS): vol.All(cv.ensure_list, [SENSOR_SCHEMA]),
    })])
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Temperature Map integration from YAML."""
    if DOMAIN not in config:
        return True

    hass.data.setdefault(DOMAIN, {})

    # Store config for platform setup
    hass.data[DOMAIN]["config"] = config[DOMAIN]

    # Forward setup to platforms
    await hass.helpers.discovery.async_load_platform(
        hass, Platform.IMAGE, DOMAIN, {}, config
    )

    return True
```

## const.py - Constants

```python
"""Constants for the Temperature Map integration."""

DOMAIN = "temperature_map"

# Config keys
CONF_WALLS = "walls"
CONF_SENSORS = "sensors"
CONF_UPDATE_INTERVAL = "update_interval"

# Defaults
DEFAULT_UPDATE_INTERVAL = 15  # minutes
DEFAULT_COMFORT_MIN = 20
DEFAULT_COMFORT_MAX = 26
DEFAULT_AMBIENT_TEMP = 22
```

## coordinator.py - DataUpdateCoordinator

Use `DataUpdateCoordinator` for periodic updates. It handles:
- Scheduling updates at intervals
- Error handling and retry logic
- Notifying entities when data changes

```python
"""DataUpdateCoordinator for Temperature Map."""
from __future__ import annotations

from datetime import timedelta
import logging
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
                if state is None or state.state in ("unknown", "unavailable"):
                    continue
                try:
                    temp = float(state.state)
                    sensor_data.append({
                        "x": sensor_config["x"],
                        "y": sensor_config["y"],
                        "temp": temp,
                        "label": sensor_config.get("label", state.attributes.get("friendly_name", entity_id)),
                    })
                except ValueError:
                    _LOGGER.warning("Invalid temperature value for %s: %s", entity_id, state.state)

            if not sensor_data:
                raise UpdateFailed("No valid sensor data available")

            # Run image generation in executor (blocking I/O)
            image_bytes = await self.hass.async_add_executor_job(
                self._render_heatmap, sensor_data
            )

            self._cached_image = image_bytes
            return image_bytes

        except Exception as err:
            raise UpdateFailed(f"Error rendering heatmap: {err}") from err

    def _render_heatmap(self, sensor_data: list[dict]) -> bytes:
        """Render the heatmap image (runs in executor thread)."""
        # Import here to avoid blocking the event loop on startup
        from .heatmap import render_heatmap_image

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
```

## image.py - ImageEntity Platform

```python
"""Image platform for Temperature Map."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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
    for map_config in hass.data[DOMAIN]["config"]:
        name = map_config["name"]
        update_interval = map_config.get("update_interval", 15)

        coordinator = TemperatureMapCoordinator(
            hass, name, map_config, update_interval
        )

        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()

        entities.append(TemperatureMapImage(coordinator, name))

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
        super().__init__(coordinator)
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
```

## Key Patterns

### 1. Use `async_add_executor_job` for blocking operations

Image rendering with Pillow is CPU-bound. Always run it in the executor:

```python
result = await hass.async_add_executor_job(blocking_function, arg1, arg2)
```

### 2. Use logging properly

```python
_LOGGER = logging.getLogger(__name__)
_LOGGER.debug("Detailed info for debugging")
_LOGGER.info("General information")
_LOGGER.warning("Something unexpected but handled")
_LOGGER.error("Something failed")
```

### 3. Handle entity states safely

```python
state = hass.states.get(entity_id)
if state is None:
    # Entity doesn't exist
    return
if state.state in ("unknown", "unavailable"):
    # Entity exists but has no valid value
    return
# Now safe to use state.state
```

### 4. Use voluptuous for config validation

```python
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

# cv provides pre-built validators:
cv.entity_id        # Validates "domain.entity_id" format
cv.string           # Validates string
cv.positive_int     # Validates positive integer
cv.boolean          # Validates boolean
cv.ensure_list      # Wraps single item in list
```

### 5. CoordinatorEntity pattern

When using `DataUpdateCoordinator`, entities should inherit from `CoordinatorEntity`:
- Automatically subscribes to coordinator updates
- Implements `should_poll = False` (coordinator handles polling)
- Provides `self.coordinator.data` access

## Common Mistakes to Avoid

1. **Don't block the event loop** - Use `async_add_executor_job` for I/O or CPU-heavy work
2. **Don't import heavy libraries at module level** - Import inside functions if they're slow to load
3. **Don't forget `_attr_unique_id`** - Required for entity registry
4. **Don't use bare `except:`** - Always catch specific exceptions
5. **Don't store mutable state in class attributes** - Use instance attributes (`self._attr_*`)

## Testing

For lightweight testing, focus on pure functions (the heatmap algorithm):

```python
# tests/test_heatmap.py
import pytest
from custom_components.temperature_map.heatmap.geometry import line_intersection

def test_line_intersection_basic():
    # Two crossing lines
    result = line_intersection(0, 0, 10, 10, 0, 10, 10, 0)
    assert result is not None
    assert abs(result["x"] - 5) < 0.001
    assert abs(result["y"] - 5) < 0.001

def test_line_intersection_parallel():
    # Parallel lines don't intersect
    result = line_intersection(0, 0, 10, 0, 0, 5, 10, 5)
    assert result is None
```

Run with: `pytest tests/ -v`
