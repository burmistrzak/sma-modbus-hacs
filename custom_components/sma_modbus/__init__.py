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
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import CONF_DEVICE_TYPE, CONF_UNIT_ID, DEFAULT_PORT, DOMAIN
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
    """Unload a config entry and remove its devices and entities."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _async_remove_devices_and_entities(hass, entry)
    return unload_ok


def _async_remove_devices_and_entities(
    hass: HomeAssistant, entry: SmaConfigEntry
) -> None:
    """Remove all devices and entities for this config entry."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        for entity in er.async_entries_for_device(
            ent_reg, device.id, include_disabled_entities=True
        ):
            ent_reg.async_remove(entity.entity_id)
        dev_reg.async_remove_device(device.id)
