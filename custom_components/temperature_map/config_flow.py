"""Config flow for Temperature Map integration."""

from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

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


def validate_wall(wall: dict) -> dict:
    """Validate a wall configuration."""
    schema = vol.Schema(
        {
            vol.Required("x1"): cv.positive_int,
            vol.Required("y1"): cv.positive_int,
            vol.Required("x2"): cv.positive_int,
            vol.Required("y2"): cv.positive_int,
        }
    )
    return schema(wall)


def validate_sensor(sensor: dict) -> dict:
    """Validate a sensor configuration."""
    schema = vol.Schema(
        {
            vol.Required("entity"): cv.entity_id,
            vol.Required("x"): cv.positive_int,
            vol.Required("y"): cv.positive_int,
            vol.Optional("label"): cv.string,
        }
    )
    return schema(sensor)


def validate_walls_json(walls_json: str) -> list[dict]:
    """Validate and parse walls JSON."""
    try:
        walls = json.loads(walls_json)
        if not isinstance(walls, list):
            raise vol.Invalid("Walls must be a JSON array")
        return [validate_wall(wall) for wall in walls]
    except json.JSONDecodeError as err:
        raise vol.Invalid(f"Invalid JSON: {err}") from err


def validate_sensors_json(sensors_json: str) -> list[dict]:
    """Validate and parse sensors JSON."""
    try:
        sensors = json.loads(sensors_json)
        if not isinstance(sensors, list):
            raise vol.Invalid("Sensors must be a JSON array")
        if not sensors:
            raise vol.Invalid("At least one sensor is required")
        return [validate_sensor(sensor) for sensor in sensors]
    except json.JSONDecodeError as err:
        raise vol.Invalid(f"Invalid JSON: {err}") from err


class TemperatureMapConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Temperature Map."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step - name and basic settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store the basic config
            self._config = user_input

            # Check if name is unique
            await self.async_set_unique_id(user_input[CONF_NAME].lower().replace(" ", "_"))
            self._abort_if_unique_id_configured()

            # Move to geometry configuration step
            return await self.async_step_geometry()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): cv.positive_int,
                vol.Optional(CONF_COMFORT_MIN_TEMP, default=DEFAULT_COMFORT_MIN): vol.Coerce(float),
                vol.Optional(CONF_COMFORT_MAX_TEMP, default=DEFAULT_COMFORT_MAX): vol.Coerce(float),
                vol.Optional(CONF_AMBIENT_TEMP, default=DEFAULT_AMBIENT_TEMP): vol.Coerce(float),
                vol.Optional(CONF_SHOW_SENSOR_NAMES, default=DEFAULT_SHOW_SENSOR_NAMES): cv.boolean,
                vol.Optional(
                    CONF_SHOW_SENSOR_TEMPERATURES, default=DEFAULT_SHOW_SENSOR_TEMPERATURES
                ): cv.boolean,
                vol.Optional(CONF_ROTATION, default=DEFAULT_ROTATION): vol.In([0, 90, 180, 270]),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "name": "Temperature Map configuration",
            },
        )

    async def async_step_geometry(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the geometry step - walls and sensors."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate walls JSON
                walls = validate_walls_json(user_input[CONF_WALLS])

                # Validate sensors JSON
                sensors = validate_sensors_json(user_input[CONF_SENSORS])

                # Combine all configuration
                name = self._config.pop(CONF_NAME)

                # Store name in data, everything else in options
                return self.async_create_entry(
                    title=name,
                    data={CONF_NAME: name},
                    options={
                        **self._config,
                        CONF_WALLS: walls,
                        CONF_SENSORS: sensors,
                    },
                )

            except vol.Invalid as err:
                errors["base"] = str(err)

        # Example JSON for help text
        example_walls = json.dumps(
            [
                {"x1": 50, "y1": 50, "x2": 350, "y2": 50},
                {"x1": 350, "y1": 50, "x2": 350, "y2": 350},
            ],
            indent=2,
        )

        example_sensors = json.dumps(
            [
                {"entity": "sensor.living_room_temp", "x": 100, "y": 100, "label": "Living Room"},
                {"entity": "sensor.bedroom_temp", "x": 250, "y": 250},
            ],
            indent=2,
        )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_WALLS): cv.string,
                vol.Required(CONF_SENSORS): cv.string,
            }
        )

        return self.async_show_form(
            step_id="geometry",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "example_walls": example_walls,
                "example_sensors": example_sensors,
            },
        )

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Import a config entry from YAML configuration."""
        # Extract name for unique_id
        name = import_config[CONF_NAME]

        # Set unique ID based on name
        await self.async_set_unique_id(name.lower().replace(" ", "_"))
        self._abort_if_unique_id_configured()

        # Store name in data, rest in options
        return self.async_create_entry(
            title=name,
            data={CONF_NAME: name},
            options={
                CONF_UPDATE_INTERVAL: import_config.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
                CONF_COMFORT_MIN_TEMP: import_config.get(
                    CONF_COMFORT_MIN_TEMP, DEFAULT_COMFORT_MIN
                ),
                CONF_COMFORT_MAX_TEMP: import_config.get(
                    CONF_COMFORT_MAX_TEMP, DEFAULT_COMFORT_MAX
                ),
                CONF_AMBIENT_TEMP: import_config.get(CONF_AMBIENT_TEMP, DEFAULT_AMBIENT_TEMP),
                CONF_SHOW_SENSOR_NAMES: import_config.get(
                    CONF_SHOW_SENSOR_NAMES, DEFAULT_SHOW_SENSOR_NAMES
                ),
                CONF_SHOW_SENSOR_TEMPERATURES: import_config.get(
                    CONF_SHOW_SENSOR_TEMPERATURES, DEFAULT_SHOW_SENSOR_TEMPERATURES
                ),
                CONF_ROTATION: import_config.get(CONF_ROTATION, DEFAULT_ROTATION),
                CONF_WALLS: import_config[CONF_WALLS],
                CONF_SENSORS: import_config[CONF_SENSORS],
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> TemperatureMapOptionsFlow:
        """Get the options flow for this handler."""
        return TemperatureMapOptionsFlow()


class TemperatureMapOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Temperature Map."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._basic_options: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options - basic settings."""
        if user_input is not None:
            # Store basic settings and move to geometry step
            self._basic_options = user_input
            return await self.async_step_geometry()

        # Get current options
        current = self.config_entry.options

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): cv.positive_int,
                vol.Optional(
                    CONF_COMFORT_MIN_TEMP,
                    default=current.get(CONF_COMFORT_MIN_TEMP, DEFAULT_COMFORT_MIN),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_COMFORT_MAX_TEMP,
                    default=current.get(CONF_COMFORT_MAX_TEMP, DEFAULT_COMFORT_MAX),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_AMBIENT_TEMP,
                    default=current.get(CONF_AMBIENT_TEMP, DEFAULT_AMBIENT_TEMP),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_SHOW_SENSOR_NAMES,
                    default=current.get(CONF_SHOW_SENSOR_NAMES, DEFAULT_SHOW_SENSOR_NAMES),
                ): cv.boolean,
                vol.Optional(
                    CONF_SHOW_SENSOR_TEMPERATURES,
                    default=current.get(
                        CONF_SHOW_SENSOR_TEMPERATURES, DEFAULT_SHOW_SENSOR_TEMPERATURES
                    ),
                ): cv.boolean,
                vol.Optional(
                    CONF_ROTATION,
                    default=current.get(CONF_ROTATION, DEFAULT_ROTATION),
                ): vol.In([0, 90, 180, 270]),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )

    async def async_step_geometry(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle geometry options - walls and sensors."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate walls
                if CONF_WALLS in user_input:
                    walls = validate_walls_json(user_input[CONF_WALLS])
                else:
                    # Keep existing walls
                    walls = self.config_entry.options[CONF_WALLS]

                # Validate sensors
                if CONF_SENSORS in user_input:
                    sensors = validate_sensors_json(user_input[CONF_SENSORS])
                else:
                    # Keep existing sensors
                    sensors = self.config_entry.options[CONF_SENSORS]

                # Merge basic options from step 1 with geometry from step 2
                all_options = {
                    **self._basic_options,
                    CONF_WALLS: walls,
                    CONF_SENSORS: sensors,
                }

                # Create the entry with all options
                return self.async_create_entry(title="", data=all_options)

            except vol.Invalid as err:
                errors["base"] = str(err)
                # Fall through to show form again with error

        # Get current geometry as JSON for display
        current = self.config_entry.options
        current_walls = json.dumps(current.get(CONF_WALLS, []), indent=2)
        current_sensors = json.dumps(current.get(CONF_SENSORS, []), indent=2)

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_WALLS, default=current_walls): cv.string,
                vol.Optional(CONF_SENSORS, default=current_sensors): cv.string,
            }
        )

        return self.async_show_form(
            step_id="geometry",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": "Edit the JSON below to modify walls and sensors. Leave unchanged to keep current values.",
            },
        )
