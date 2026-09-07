"""Test the SMA Modbus custom integration setup and sensor creation."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_entries_for_config_entry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sma_modbus import DEVICE_CLASSES
from custom_components.sma_modbus.const import CONF_DEVICE_TYPE, DOMAIN
from custom_components.sma_modbus.coordinator import SmaCoordinator
from custom_components.sma_modbus.sensor import SENSOR_DESCRIPTIONS
from custom_components.sma_modbus.sma_modbus import DeviceType, DiscoveryInfo, Vendor
from custom_components.sma_modbus.sma_modbus.testing import set_input_registers

SERIAL = 30001234
UNIQUE_ID = f"SMA{SERIAL}"


def _mock_discovery_info(device_type: DeviceType, unit_id: int = 3) -> DiscoveryInfo:
    """Return a fake DiscoveryInfo for the given device type."""
    return DiscoveryInfo(
        device_type=device_type,
        serial_number=SERIAL,
        unit_id=unit_id,
        susy_id=270,
        modbus_profile_revision=1140,
        device_class=8009,
        device_model=19085,
        vendor=Vendor.SMA.value,
    )


def _preloaded_connection(device_type: DeviceType) -> MockModbusConnection:
    """Return a mock connection preloaded with measurement data."""
    connection = MockModbusConnection()
    device_cls = DEVICE_CLASSES[device_type]
    device = device_cls(connection)
    set_input_registers(
        connection,
        device,
        {
            "serial_number": SERIAL,
            "device_class": _mock_discovery_info(device_type).device_class,
            "device_type": _mock_discovery_info(device_type).device_model,
            "vendor": Vendor.SMA.value,
        },
    )
    return connection


@pytest.mark.parametrize(
    "device_type",
    [
        DeviceType.SUNNY_HOME_MANAGER,
        DeviceType.SUNNY_BOY_SMART_ENERGY,
        DeviceType.SUNNY_BOY,
        DeviceType.SUNNY_TRIPOWER,
    ],
)
async def test_setup_and_sensors(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    device_type: DeviceType,
) -> None:
    """Test the integration sets up and exposes the device sensors."""
    connection = _preloaded_connection(device_type)

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UNIQUE_ID,
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_DEVICE_TYPE: device_type.value,
        },
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.sma_modbus.ModbusConnection",
            return_value=connection,
        ),
        patch(
            "custom_components.sma_modbus.discover",
            AsyncMock(return_value=_mock_discovery_info(device_type)),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    coordinator: SmaCoordinator = entry.runtime_data
    assert coordinator.device_type is device_type

    entity_registry = async_get_entity_registry(hass)
    entities = async_entries_for_config_entry(entity_registry, entry.entry_id)
    assert len(entities) == len(SENSOR_DESCRIPTIONS[device_type])


async def test_setup_unload(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test the integration unloads cleanly."""
    device_type = DeviceType.SUNNY_BOY_SMART_ENERGY
    connection = _preloaded_connection(device_type)

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UNIQUE_ID,
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_DEVICE_TYPE: device_type.value,
        },
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.sma_modbus.ModbusConnection",
            return_value=connection,
        ),
        patch(
            "custom_components.sma_modbus.discover",
            AsyncMock(return_value=_mock_discovery_info(device_type)),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_coordinator_update_failure(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the coordinator logs when the device becomes unavailable."""
    device_type = DeviceType.SUNNY_BOY_SMART_ENERGY
    connection = _preloaded_connection(device_type)

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UNIQUE_ID,
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_DEVICE_TYPE: device_type.value,
        },
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.sma_modbus.ModbusConnection",
            return_value=connection,
        ),
        patch(
            "custom_components.sma_modbus.discover",
            AsyncMock(return_value=_mock_discovery_info(device_type)),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator: SmaCoordinator = entry.runtime_data
    assert coordinator._was_available is True

    # Simulate a device failure.
    with patch.object(
        coordinator.device,
        "async_update",
        AsyncMock(side_effect=ModbusError("connection lost")),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert "became unavailable" in caplog.text
    assert coordinator._was_available is False

    # Simulate recovery.
    with patch.object(
        coordinator.device,
        "async_update",
        AsyncMock(),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert "is now available" in caplog.text
    assert coordinator._was_available is True
