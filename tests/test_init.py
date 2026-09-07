"""Test the SMA Modbus custom integration setup and sensor creation."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_entries_for_config_entry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sma_modbus.const import CONF_DEVICE_TYPE, DOMAIN
from custom_components.sma_modbus.coordinator import SmaCoordinator
from custom_components.sma_modbus.sensor import SENSOR_DESCRIPTIONS
from custom_components.sma_modbus.sma_modbus import DeviceType, SunnyBoySmartEnergy
from custom_components.sma_modbus.sma_modbus.testing import set_input_registers


def _preloaded_connection() -> MockModbusConnection:
    """Return a mock connection preloaded with Sunny Boy Smart Energy data."""
    connection = MockModbusConnection()
    unit = connection.for_unit(3)
    set_input_registers(
        connection,
        SunnyBoySmartEnergy(unit),
        {
            "pv_power": 4000,
            "pv_energy_total": 123456789,
            "battery_state_of_charge": 80,
            "dc_voltage_1": 35000,
            "serial_number": 30001234,
            "device_class": 8009,
            "device_type": 19085,
            "vendor": 461,
        },
    )
    return connection


async def test_setup_and_sensors(hass: HomeAssistant) -> None:
    """Test the integration sets up and exposes the device sensors."""
    connection = _preloaded_connection()

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="SMA30001234",
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_DEVICE_TYPE: DeviceType.SUNNY_BOY_SMART_ENERGY.value,
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.sma_modbus.ModbusConnection",
        return_value=connection,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    coordinator: SmaCoordinator = entry.runtime_data
    assert coordinator.device.pv_power == 4000
    assert coordinator.device.battery_state_of_charge == 80

    entity_registry = async_get_entity_registry(hass)
    entities = async_entries_for_config_entry(entity_registry, entry.entry_id)
    assert len(entities) == len(SENSOR_DESCRIPTIONS[DeviceType.SUNNY_BOY_SMART_ENERGY])


async def test_setup_unload(hass: HomeAssistant) -> None:
    """Test the integration unloads cleanly."""
    connection = _preloaded_connection()

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="SMA30001234",
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_DEVICE_TYPE: DeviceType.SUNNY_BOY_SMART_ENERGY.value,
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.sma_modbus.ModbusConnection",
        return_value=connection,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
