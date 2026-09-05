"""Constants for the SMA Modbus integration."""

from datetime import timedelta
from enum import StrEnum
from typing import Final

from .sma_modbus import DeviceType

DOMAIN: Final = "sma_modbus"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_UNIT_ID: Final = "unit_id"
CONF_DEVICE_TYPE: Final = "device_type"

DEFAULT_PORT: Final = 502
DEFAULT_UNIT_ID: Final = 3


class UnitOfElectricResistance(StrEnum):
    """Electric resistance units."""

    MICROOHM = "μΩ"
    MILLIOHM = "mΩ"
    OHM = "Ω"
    KILOOHM = "kΩ"
    MEGAOHM = "MΩ"


# Default Modbus unit ID per device type: the Sunny Home Manager answers on
# unit 2, inverters on unit 3.
DEFAULT_UNIT_IDS: dict[DeviceType, int] = {
    DeviceType.SUNNY_HOME_MANAGER: 2,
    DeviceType.SUNNY_BOY_SMART_ENERGY: 3,
    DeviceType.SUNNY_BOY: 3,
}

SCAN_INTERVAL: Final = timedelta(seconds=30)

DEVICE_NAMES: dict[DeviceType, str] = {
    DeviceType.SUNNY_HOME_MANAGER: "Sunny Home Manager 2.0",
    DeviceType.SUNNY_BOY_SMART_ENERGY: "Sunny Boy Smart Energy 3.6-6.0",
    DeviceType.SUNNY_BOY: "Sunny Boy 3.0-6.0",
}
