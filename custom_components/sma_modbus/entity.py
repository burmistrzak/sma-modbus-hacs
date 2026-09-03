"""Base entity for the SMA Modbus integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAMES, DOMAIN
from .coordinator import SmaCoordinator
from .sma_modbus import SmaComponent


class SmaEntity(CoordinatorEntity[SmaCoordinator]):
    """Defines a SMA coordinator entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmaCoordinator) -> None:
        """Initialize a SMA entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.unique_id)},
            manufacturer="SMA",
            name=coordinator.config_entry.title,
            model=DEVICE_NAMES[coordinator.device_type],
        )

    @property
    def device(self) -> SmaComponent:
        """Return the SMA device component polled by the coordinator."""
        return self.coordinator.device
