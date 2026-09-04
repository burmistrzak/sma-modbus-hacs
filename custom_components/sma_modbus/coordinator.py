"""DataUpdateCoordinator that polls an SMA device."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from modbus_connection import ModbusError

from .const import DOMAIN, SCAN_INTERVAL
from .sma_modbus import DeviceType, SmaComponent

_LOGGER = logging.getLogger(__name__)

type SmaCoordinatorConfigEntry = ConfigEntry[SmaCoordinator]


class SmaCoordinator(DataUpdateCoordinator[SmaComponent]):
    """Poll an SMA device through its Modbus unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SmaCoordinatorConfigEntry,
        device: SmaComponent,
        device_type: DeviceType,
    ) -> None:
        """Initialize the SMA coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device
        self.device_type = device_type

    async def _async_update_data(self) -> SmaComponent:
        """Refresh all SMA data."""
        try:
            await self.device.async_update()
        except ModbusError as err:
            raise UpdateFailed(f"Error communicating with SMA device: {err}") from err
        return self.device
