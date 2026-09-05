"""The SMA Modbus custom integration.

This custom component bundles the ``sma_modbus`` device library (under
``sma_modbus/``) and opens its own Modbus TCP connection, so it can be tested
via HACS before the shared-connection Modbus integration lands in Home
Assistant core. Once it has, the core ``sma`` integration supersedes this one
and shares the connection instead of opening its own.
"""

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import CONF_DEVICE_TYPE, CONF_UNIT_ID, DEFAULT_PORT
from .coordinator import SmaCoordinator
from .sma_modbus import DEVICE_CLASSES, DeviceType

_LOGGER: Final = logging.getLogger(__name__)

PLATFORMS: Final = [Platform.SENSOR]

type SmaConfigEntry = ConfigEntry[SmaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SmaConfigEntry) -> bool:
    """Set up SMA from a config entry.

    A Modbus TCP connection is owned by this entry and closed when it unloads.
    """
    host: str = entry.data[CONF_HOST]
    port: int = entry.data.get(CONF_PORT, DEFAULT_PORT)
    unit_id: int = entry.data[CONF_UNIT_ID]
    device_type = DeviceType(entry.data[CONF_DEVICE_TYPE])

    connection = ModbusConnection(ModbusTcpParams(host=host, port=port))
    entry.async_on_unload(connection.close)

    unit = connection.for_unit(unit_id)
    device = DEVICE_CLASSES[device_type](unit)

    coordinator = SmaCoordinator(hass, entry, device, device_type)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: SmaConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Remove a device from a config entry.

    Allows the user to manually remove the device from the UI when it is no
    longer reachable.  We allow removal if the coordinator's last update
    failed (the device is not communicating).
    """
    coordinator = config_entry.runtime_data
    return coordinator.last_update_success is False
