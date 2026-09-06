"""Library for SMA Modbus TCP interface.

Consumes a ``modbus_connection.ModbusConnection`` — the library opens its own
unit handles and knows which unit IDs to poll. Each device is a single
:class:`~modbus_connection.model.Component` read from input registers; call
:meth:`async_update` to refresh every field in as few requests as the register
layout allows.

Use :func:`discover` to auto-detect the device type, serial number, and unit ID
from just a connection to the device's IP address.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

from modbus_connection import ModbusConnection, ModbusError

from ._base import SmaComponent, Vendor
from .home_manager import DeviceClass as SunnyHomeManagerDeviceClass
from .home_manager import SunnyHomeManager, SunnyHomeManagerModel, SystemStatus
from .sunny_boy import DeviceClass as SunnyBoyDeviceClass
from .sunny_boy import SunnyBoy, SunnyBoyModel
from .sunny_boy_smart_energy import (
    BatteryHealth,
    CmpBmsStatus,
    SunnyBoySmartEnergy,
    SunnyBoySmartEnergyModel,
)
from .sunny_boy_smart_energy import (
    DeviceClass as SunnyBoySmartEnergyDeviceClass,
)

__all__ = [
    "DEVICE_CLASSES",
    "BatteryHealth",
    "CmpBmsStatus",
    "DeviceType",
    "DiscoveryInfo",
    "SmaComponent",
    "SunnyBoy",
    "SunnyBoyDeviceClass",
    "SunnyBoyModel",
    "SunnyBoySmartEnergy",
    "SunnyBoySmartEnergyDeviceClass",
    "SunnyBoySmartEnergyModel",
    "SunnyHomeManager",
    "SunnyHomeManagerDeviceClass",
    "SunnyHomeManagerModel",
    "SystemStatus",
    "Vendor",
    "discover",
]


class DeviceType(StrEnum):
    """The SMA device models this library supports."""

    SUNNY_HOME_MANAGER = "sunny_home_manager"
    SUNNY_BOY_SMART_ENERGY = "sunny_boy_smart_energy"
    SUNNY_BOY = "sunny_boy"


DEVICE_CLASSES: dict[DeviceType, type[SmaComponent]] = {
    DeviceType.SUNNY_HOME_MANAGER: SunnyHomeManager,
    DeviceType.SUNNY_BOY_SMART_ENERGY: SunnyBoySmartEnergy,
    DeviceType.SUNNY_BOY: SunnyBoy,
}


_LOGGER = logging.getLogger(__name__)


# Device class values from input register 30051 (Nameplate.MainModel).
_DEVICE_CLASS_SHM = SunnyHomeManagerDeviceClass.COMMUNICATION_PRODUCTS.value
_DEVICE_CLASS_SB = SunnyBoyDeviceClass.SOLAR_INVERTERS.value
_DEVICE_CLASS_SBSE = SunnyBoySmartEnergyDeviceClass.HYBRID_INVERTER.value


@dataclass(frozen=True, slots=True)
class DiscoveryInfo:
    """Result of auto-discovering an SMA device on the network.

    ``device_type`` selects the :class:`SmaComponent` subclass to use;
    ``serial_number`` is the device's physical serial;
    ``unit_id`` is the Modbus unit ID the measurement registers answer on;
    the remaining fields are the raw Type Label values from unit ID 1.
    """

    device_type: DeviceType
    serial_number: int
    unit_id: int
    susy_id: int
    modbus_profile_revision: int
    device_class: int
    device_model: int
    vendor: int


def _combine_u32(words: list[int]) -> int:
    """Combine two big-endian 16-bit words into a 32-bit unsigned value."""
    return (words[0] << 16) | words[1]


def _is_nan(value: int) -> bool:
    """Check if a 32-bit value is a NaN sentinel."""
    return value in (0xFFFFFFFF, 0x00FFFFFD, 0x80000000)


async def discover(
    connection: ModbusConnection,
    *,
    unit_id: int | None = None,
) -> DiscoveryInfo:
    """Auto-detect the SMA device at the other end of ``connection``.

    Reads the Type Label from Unit ID 1 (input registers 30001-30006 and
    30051-30056): serial number, SUSy ID, Modbus profile revision, device
    class, device model, and manufacturer.

    The device class is mapped to a :class:`DeviceType`. The measurement unit
    ID defaults to the device class's standard unit ID (3 for inverters,
    2 for the Sunny Home Manager); pass ``unit_id`` to override it for edge
    cases where a device has been reconfigured.

    Returns a :class:`DiscoveryInfo` with all Type Label fields and the
    unit ID to use for measurements.
    Raises :class:`~modbus_connection.ModbusError` if the device cannot be
    discovered or is not a supported SMA device.
    """
    unit1 = connection.for_unit(1)

    # Read two contiguous Type Label blocks from unit 1:
    #   30001-30006: modbus profile revision, SUSy ID, serial number
    #   30051-30056: device class, device model, manufacturer
    words = await unit1.read_input_registers(30001, 6)
    modbus_profile_revision = _combine_u32(words[0:2])
    susy_id = _combine_u32(words[2:4])
    serial_number = _combine_u32(words[4:6])

    words = await unit1.read_input_registers(30051, 6)
    device_class = _combine_u32(words[0:2])
    device_model = _combine_u32(words[2:4])
    vendor = _combine_u32(words[4:6])

    if _is_nan(serial_number):
        raise ModbusError("Serial number not available on unit 1")
    if _is_nan(device_class):
        raise ModbusError("Device class not available on unit 1")

    # Map device class to DeviceType.
    if device_class == _DEVICE_CLASS_SHM:
        device_type = DeviceType.SUNNY_HOME_MANAGER
    elif device_class == _DEVICE_CLASS_SB:
        device_type = DeviceType.SUNNY_BOY
    elif device_class == _DEVICE_CLASS_SBSE:
        device_type = DeviceType.SUNNY_BOY_SMART_ENERGY
    else:
        raise ModbusError(f"Unknown device class: {device_class}")

    # Use the provided unit_id, or the device type's default.
    if unit_id is not None:
        _LOGGER.debug("Using overridden unit ID %d for %s", unit_id, device_type.value)
    else:
        unit_id = DEVICE_CLASSES[device_type].default_unit_id

    return DiscoveryInfo(
        device_type=device_type,
        serial_number=serial_number,
        unit_id=unit_id,
        susy_id=susy_id,
        modbus_profile_revision=modbus_profile_revision,
        device_class=device_class,
        device_model=device_model,
        vendor=vendor,
    )
