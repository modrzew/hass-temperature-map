"""Constants for the Temperature Map integration."""

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

DOMAIN = "temperature_map"

# Config keys
CONF_WALLS = "walls"
CONF_SENSORS = "sensors"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_COMFORT_MIN_TEMP = "comfort_min_temp"
CONF_COMFORT_MAX_TEMP = "comfort_max_temp"
CONF_AMBIENT_TEMP = "ambient_temp"
CONF_SHOW_SENSOR_NAMES = "show_sensor_names"
CONF_SHOW_SENSOR_TEMPERATURES = "show_sensor_temperatures"
CONF_ROTATION = "rotation"

# Defaults
DEFAULT_UPDATE_INTERVAL = 15  # minutes
DEFAULT_COMFORT_MIN = 20
DEFAULT_COMFORT_MAX = 26
DEFAULT_AMBIENT_TEMP = 22
DEFAULT_SHOW_SENSOR_NAMES = True
DEFAULT_SHOW_SENSOR_TEMPERATURES = True
DEFAULT_ROTATION = 0

# Shared validation schemas
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
