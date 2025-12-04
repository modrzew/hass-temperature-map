"""Test the Temperature Map coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Try to import homeassistant, skip all tests if not available
try:
    from homeassistant import config_entries
    from homeassistant.core import HomeAssistant
    from custom_components.temperature_map.const import (
        CONF_AMBIENT_TEMP,
        CONF_COMFORT_MAX_TEMP,
        CONF_COMFORT_MIN_TEMP,
        CONF_ROTATION,
        CONF_SENSORS,
        CONF_SHOW_SENSOR_NAMES,
        CONF_SHOW_SENSOR_TEMPERATURES,
        CONF_UPDATE_INTERVAL,
        CONF_WALLS,
        DOMAIN,
    )
    from custom_components.temperature_map.coordinator import TemperatureMapCoordinator

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False
    # Define dummy values to allow module import
    CONF_AMBIENT_TEMP = None
    CONF_COMFORT_MAX_TEMP = None
    CONF_COMFORT_MIN_TEMP = None
    CONF_ROTATION = None
    CONF_SENSORS = None
    CONF_SHOW_SENSOR_NAMES = None
    CONF_SHOW_SENSOR_TEMPERATURES = None
    CONF_UPDATE_INTERVAL = None
    CONF_WALLS = None
    DOMAIN = None
    TemperatureMapCoordinator = None

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not HA_AVAILABLE, reason="Home Assistant not installed"),
]


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.states = Mock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def config_entry():
    """Create a config entry for testing."""
    return config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Map",
        data={"name": "Test Map"},
        options={
            CONF_UPDATE_INTERVAL: 15,
            CONF_COMFORT_MIN_TEMP: 20.0,
            CONF_COMFORT_MAX_TEMP: 26.0,
            CONF_AMBIENT_TEMP: 22.0,
            CONF_SHOW_SENSOR_NAMES: True,
            CONF_SHOW_SENSOR_TEMPERATURES: True,
            CONF_ROTATION: 0,
            CONF_WALLS: [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}],
            CONF_SENSORS: [{"entity": "sensor.test_temp", "x": 100, "y": 100}],
        },
        source="user",
        unique_id="test_map",
    )


def test_coordinator_initialization(mock_hass, config_entry):
    """Test coordinator initialization."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    assert coordinator.name == f"{DOMAIN}_Test Map"
    assert coordinator.update_interval == timedelta(minutes=15)
    assert coordinator.config_entry == config_entry


def test_coordinator_gets_config_from_options(mock_hass, config_entry):
    """Test that coordinator reads config from options."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    config = coordinator._config

    assert config[CONF_UPDATE_INTERVAL] == 15
    assert config[CONF_COMFORT_MIN_TEMP] == 20.0
    assert config[CONF_WALLS] == [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}]


async def test_coordinator_handles_update_interval_change(mock_hass, config_entry):
    """Test that coordinator handles update interval changes."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    # Initial interval
    assert coordinator.update_interval == timedelta(minutes=15)

    # Create a new config entry with updated options
    updated_entry = config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Map",
        data=config_entry.data,
        options={
            **config_entry.options,
            CONF_UPDATE_INTERVAL: 30,  # Changed from 15 to 30
        },
        source="user",
        unique_id="test_map",
    )

    # Update coordinator's reference
    coordinator.config_entry = updated_entry

    # Mock async_request_refresh
    coordinator.async_request_refresh = AsyncMock()

    # Call the update handler
    await coordinator.async_config_entry_updated(mock_hass, updated_entry)

    # Check that interval was updated
    assert coordinator.update_interval == timedelta(minutes=30)

    # Check that refresh was requested
    coordinator.async_request_refresh.assert_called_once()


async def test_coordinator_handles_geometry_change(mock_hass, config_entry):
    """Test that coordinator detects geometry changes."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    # Set initial geometry cache
    coordinator._last_walls = config_entry.options[CONF_WALLS]
    coordinator._last_sensors = config_entry.options[CONF_SENSORS]

    # Create a new config entry with updated geometry
    updated_entry = config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Map",
        data=config_entry.data,
        options={
            **config_entry.options,
            CONF_WALLS: [{"x1": 100, "y1": 100, "x2": 400, "y2": 100}],  # Changed
        },
        source="user",
        unique_id="test_map",
    )

    # Update coordinator's reference
    coordinator.config_entry = updated_entry

    # Mock async_request_refresh
    coordinator.async_request_refresh = AsyncMock()

    # Call the update handler
    await coordinator.async_config_entry_updated(mock_hass, updated_entry)

    # Check that refresh was requested (geometry changed)
    coordinator.async_request_refresh.assert_called_once()


async def test_coordinator_handles_temperature_settings_change(mock_hass, config_entry):
    """Test that coordinator handles temperature settings changes."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    # Create a new config entry with updated temperature settings
    updated_entry = config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Map",
        data=config_entry.data,
        options={
            **config_entry.options,
            CONF_COMFORT_MIN_TEMP: 18.0,  # Changed from 20.0
            CONF_COMFORT_MAX_TEMP: 24.0,  # Changed from 26.0
            CONF_ROTATION: 90,  # Changed from 0
        },
        source="user",
        unique_id="test_map",
    )

    # Update coordinator's reference
    coordinator.config_entry = updated_entry

    # Mock async_request_refresh
    coordinator.async_request_refresh = AsyncMock()

    # Call the update handler
    await coordinator.async_config_entry_updated(mock_hass, updated_entry)

    # Check that refresh was requested (settings changed)
    coordinator.async_request_refresh.assert_called_once()

    # Verify new settings are accessible
    assert coordinator._config[CONF_COMFORT_MIN_TEMP] == 18.0
    assert coordinator._config[CONF_COMFORT_MAX_TEMP] == 24.0
    assert coordinator._config[CONF_ROTATION] == 90


async def test_coordinator_update_data_with_valid_sensors(mock_hass, config_entry):
    """Test coordinator fetching data with valid sensors."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    # Mock sensor state
    mock_state = Mock()
    mock_state.state = "23.5"
    mock_state.attributes = {"friendly_name": "Test Temperature"}
    mock_hass.states.get.return_value = mock_state

    # Mock image rendering
    mock_image_bytes = b"fake_png_data"
    mock_hass.async_add_executor_job.return_value = mock_image_bytes

    # Fetch data
    result = await coordinator._async_update_data()

    # Verify result
    assert result == mock_image_bytes
    assert coordinator._cached_image == mock_image_bytes

    # Verify geometry cache was updated
    assert coordinator._last_walls == config_entry.options[CONF_WALLS]
    assert coordinator._last_sensors == config_entry.options[CONF_SENSORS]


async def test_coordinator_update_data_with_unavailable_sensor(mock_hass, config_entry):
    """Test coordinator handling unavailable sensors."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    # Mock unavailable sensor state
    mock_state = Mock()
    mock_state.state = "unavailable"
    mock_hass.states.get.return_value = mock_state

    # Mock image rendering (should still work with no sensors)
    mock_image_bytes = b"fake_png_data"
    mock_hass.async_add_executor_job.return_value = mock_image_bytes

    # Fetch data
    result = await coordinator._async_update_data()

    # Should still return an image (floor plan only)
    assert result == mock_image_bytes


async def test_coordinator_update_data_with_missing_sensor(mock_hass, config_entry):
    """Test coordinator handling missing sensors."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    # Mock missing sensor (returns None)
    mock_hass.states.get.return_value = None

    # Mock image rendering
    mock_image_bytes = b"fake_png_data"
    mock_hass.async_add_executor_job.return_value = mock_image_bytes

    # Fetch data
    result = await coordinator._async_update_data()

    # Should still return an image
    assert result == mock_image_bytes
