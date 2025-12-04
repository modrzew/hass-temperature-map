"""The Temperature Map integration."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

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

# Platforms this integration provides
PLATFORMS: list[Platform] = [Platform.IMAGE]

# YAML configuration schema (for backwards compatibility)
WALL_SCHEMA = vol.Schema(
    {
        vol.Required("x1"): cv.positive_int,
        vol.Required("y1"): cv.positive_int,
        vol.Required("x2"): cv.positive_int,
        vol.Required("y2"): cv.positive_int,
    }
)

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required("entity"): cv.entity_id,
        vol.Required("x"): cv.positive_int,
        vol.Required("y"): cv.positive_int,
        vol.Optional("label"): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_NAME): cv.string,
                        vol.Optional(
                            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                        ): cv.positive_int,
                        vol.Optional(
                            CONF_COMFORT_MIN_TEMP, default=DEFAULT_COMFORT_MIN
                        ): vol.Coerce(float),
                        vol.Optional(
                            CONF_COMFORT_MAX_TEMP, default=DEFAULT_COMFORT_MAX
                        ): vol.Coerce(float),
                        vol.Optional(CONF_AMBIENT_TEMP, default=DEFAULT_AMBIENT_TEMP): vol.Coerce(
                            float
                        ),
                        vol.Optional(
                            CONF_SHOW_SENSOR_NAMES, default=DEFAULT_SHOW_SENSOR_NAMES
                        ): cv.boolean,
                        vol.Optional(
                            CONF_SHOW_SENSOR_TEMPERATURES, default=DEFAULT_SHOW_SENSOR_TEMPERATURES
                        ): cv.boolean,
                        vol.Optional(CONF_ROTATION, default=DEFAULT_ROTATION): vol.In(
                            [0, 90, 180, 270]
                        ),
                        vol.Required(CONF_WALLS): vol.All(cv.ensure_list, [WALL_SCHEMA]),
                        vol.Required(CONF_SENSORS): vol.All(cv.ensure_list, [SENSOR_SCHEMA]),
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def _register_frontend_resources(hass: HomeAssistant) -> None:
    """Register frontend resources for the temperature map overlay card."""
    # Get the path to the www directory in this integration
    integration_path = Path(__file__).parent
    www_path = integration_path / "www"
    js_file = www_path / "temperature-map-overlay.js"

    # Check if the file exists
    if not js_file.exists():
        _LOGGER.warning(
            "Frontend overlay file not found at %s. Clickable sensors will not be available.",
            js_file,
        )
        return

    # Register the static path for serving the JavaScript file
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=f"/{DOMAIN}",
                path=str(www_path),
                cache_headers=False,
            )
        ]
    )

    # Register the JavaScript module with the frontend
    add_extra_js_url(hass, f"/{DOMAIN}/temperature-map-overlay.js")

    _LOGGER.info(
        "Registered temperature map overlay card at /%s/temperature-map-overlay.js", DOMAIN
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Temperature Map integration from YAML."""
    hass.data.setdefault(DOMAIN, {})

    # Register frontend resources (once for all config entries)
    await _register_frontend_resources(hass)

    # Handle YAML configuration by importing to config entries
    if DOMAIN in config:
        for yaml_config in config[DOMAIN]:
            # Import each YAML config as a config entry
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "import"},
                    data=yaml_config,
                )
            )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Temperature Map from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Import coordinator here to avoid circular imports
    from .coordinator import TemperatureMapCoordinator

    # Create coordinator for this config entry
    coordinator = TemperatureMapCoordinator(hass, entry)

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Register services (only once)
    if not hass.services.has_service(DOMAIN, "refresh"):

        async def handle_refresh(call: ServiceCall) -> None:
            """Handle the refresh service call."""
            # Refresh all coordinators
            for _entry_id, coordinator in hass.data[DOMAIN].items():
                if isinstance(coordinator, TemperatureMapCoordinator):
                    await coordinator.async_request_refresh()

        hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove coordinator
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # Get the coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Notify coordinator of config update
    await coordinator.async_config_entry_updated(hass, entry)
