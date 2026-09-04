"""Test the SMA Modbus custom integration setup and sensor creation."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_entries_for_config_entry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sma_modbus.const import CONF_DEVICE_TYPE, CONF_UNIT_ID, DOMAIN
from custom_components.sma_modbus.coordinator import SmaCoordinator
from custom_components.sma_modbus.sensor import SENSOR_DESCRIPTIONS
from custom_components.sma_modbus.sma_modbus import DeviceType, SunnyBoySmartEnergy
from custom_components.sma_modbus.sma_modbus.testing import set_input_registers


def _preloaded_unit() -> MockModbusUnit:
    """Return a mock unit preloaded with Sunny Boy Smart Energy data."""
    connection = MockModbusConnection()
    unit = connection.for_unit(3)
    set_input_registers(
        unit,
        SunnyBoySmartEnergy(unit),
        {
            "pv_power": 4000,
            "pv_energy_total": 123456789,
            "battery_state_of_charge": 80,
            "dc_voltage_1": 35000,
        },
    )
    return unit


async def test_setup_and_sensors(hass: HomeAssistant) -> None:
    """Test the integration sets up and exposes the device sensors."""
    unit = _preloaded_unit()
    connection = MockModbusConnection()
    connection.for_unit = lambda _unit_id: unit  # return the preloaded unit

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.178.1:502:3:sunny_boy_smart_energy",
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_UNIT_ID: 3,
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
    unit = _preloaded_unit()
    connection = MockModbusConnection()
    connection.for_unit = lambda _unit_id: unit

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.178.1:502:3:sunny_boy_smart_energy",
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_UNIT_ID: 3,
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
