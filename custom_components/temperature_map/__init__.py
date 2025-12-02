"""The Temperature Map integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_WALLS,
    CONF_SENSORS,
    CONF_UPDATE_INTERVAL,
    CONF_COMFORT_MIN_TEMP,
    CONF_COMFORT_MAX_TEMP,
    CONF_AMBIENT_TEMP,
    CONF_SHOW_SENSOR_NAMES,
    CONF_SHOW_SENSOR_TEMPERATURES,
    CONF_ROTATION,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_COMFORT_MIN,
    DEFAULT_COMFORT_MAX,
    DEFAULT_AMBIENT_TEMP,
    DEFAULT_SHOW_SENSOR_NAMES,
    DEFAULT_SHOW_SENSOR_TEMPERATURES,
    DEFAULT_ROTATION,
)

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
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
        vol.Optional(CONF_COMFORT_MIN_TEMP, default=DEFAULT_COMFORT_MIN): vol.Coerce(float),
        vol.Optional(CONF_COMFORT_MAX_TEMP, default=DEFAULT_COMFORT_MAX): vol.Coerce(float),
        vol.Optional(CONF_AMBIENT_TEMP, default=DEFAULT_AMBIENT_TEMP): vol.Coerce(float),
        vol.Optional(CONF_SHOW_SENSOR_NAMES, default=DEFAULT_SHOW_SENSOR_NAMES): cv.boolean,
        vol.Optional(CONF_SHOW_SENSOR_TEMPERATURES, default=DEFAULT_SHOW_SENSOR_TEMPERATURES): cv.boolean,
        vol.Optional(CONF_ROTATION, default=DEFAULT_ROTATION): vol.In([0, 90, 180, 270]),
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
        Platform.IMAGE, DOMAIN, {}, config
    )

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle the refresh service call."""
        # Get all coordinators and trigger refresh
        if "coordinators" in hass.data[DOMAIN]:
            for coordinator in hass.data[DOMAIN]["coordinators"]:
                await coordinator.async_request_refresh()

    # Register refresh service
    hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    return True
