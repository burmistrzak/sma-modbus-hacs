"""Support for SMA sensors."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import SmaConfigEntry
from .coordinator import SmaCoordinator
from .entity import SmaEntity
from .sma_modbus import DeviceType
from .sma_modbus.home_manager import SystemStatus
from .sma_modbus.sunny_boy_smart_energy import BatteryHealth, CmpBmsStatus

PARALLEL_UPDATES = 0


@dataclass(frozen=True)
class SmaSensorEntityDescription(SensorEntityDescription):
    """Describes an SMA sensor entity.

    ``key`` is the attribute name on the library device component and the
    entity translation key.
    """


def _energy(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    )


def _power(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _battery(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _voltage(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    )


def _current(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    )


def _frequency(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    )


def _temperature(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    )


def _apparent_power(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _reactive_power(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _power_factor(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    )


def _enum(key: str, enum_type: type[IntEnum]) -> SmaSensorEntityDescription:
    """Create an ENUM sensor description for a typed status field.

    The library returns an ``IntEnum`` member (or ``None`` on the sentinel);
    the entity converts it to the member's lowercase ``.name`` so Home
    Assistant stores the state as a string from ``options``. Translation keys
    must be ``[a-z0-9-_]+``.
    """
    return SmaSensorEntityDescription(
        key=key,
        device_class=SensorDeviceClass.ENUM,
        options=[member.name.lower() for member in enum_type],
    )


def _diagnostic(key: str) -> SmaSensorEntityDescription:
    return SmaSensorEntityDescription(
        key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    )


SENSOR_DESCRIPTIONS: Final[dict[DeviceType, list[SmaSensorEntityDescription]]] = {
    DeviceType.SUNNY_HOME_MANAGER: [
        _enum("system_status", SystemStatus),
        _energy("grid_import_energy"),
        _energy("grid_export_energy"),
        _power("grid_import_power"),
        _power("grid_export_power"),
    ],
    DeviceType.SUNNY_BOY_SMART_ENERGY: [
        # PV
        _power("pv_power"),
        _energy("pv_energy_total"),
        # AC power
        _power("ac_power"),
        _power("ac_power_l1"),
        _power("ac_power_l2"),
        _power("ac_power_l3"),
        # AC voltage
        _voltage("ac_voltage_l1"),
        _voltage("ac_voltage_l2"),
        _voltage("ac_voltage_l3"),
        _voltage("ac_voltage_l1_l2"),
        _voltage("ac_voltage_l2_l3"),
        _voltage("ac_voltage_l3_l1"),
        # AC current
        _current("ac_current"),
        _current("ac_current_l1"),
        _current("ac_current_l2"),
        _current("ac_current_l3"),
        # AC frequency
        _frequency("grid_frequency"),
        # AC reactive power
        _reactive_power("ac_reactive_power"),
        _reactive_power("ac_reactive_power_l1"),
        _reactive_power("ac_reactive_power_l2"),
        _reactive_power("ac_reactive_power_l3"),
        # AC apparent power
        _apparent_power("ac_apparent_power"),
        _apparent_power("ac_apparent_power_l1"),
        _apparent_power("ac_apparent_power_l2"),
        _apparent_power("ac_apparent_power_l3"),
        # AC power factor
        _power_factor("power_factor"),
        _power_factor("power_factor_eei"),
        # Battery
        _current("battery_current"),
        _battery("battery_state_of_charge"),
        _battery("battery_nominal_capacity"),
        _temperature("battery_temperature"),
        _voltage("battery_voltage"),
        _power("battery_charge_power"),
        _power("battery_discharge_power"),
        _energy("battery_charge_energy"),
        _energy("battery_discharge_energy"),
        _enum("battery_health", BatteryHealth),
        _voltage("battery_max_voltage"),
        _temperature("battery_temperature_max"),
        _temperature("battery_temperature_min"),
        _voltage("battery_end_of_charge_voltage"),
        _voltage("battery_end_of_discharge_voltage"),
        _current("battery_max_charge_current"),
        _current("battery_max_discharge_current"),
        _voltage("battery_cell_voltage_sum"),
        _voltage("battery_cell_voltage_min"),
        _voltage("battery_cell_voltage_max"),
        _enum("bms_operating_status", CmpBmsStatus),
        _energy("battery_current_charge_energy"),
        _energy("battery_current_discharge_energy"),
        # DC strings (0-based)
        _power("dc_power_0"),
        _power("dc_power_1"),
        _power("dc_power_2"),
        _energy("dc_energy_total_0"),
        _energy("dc_energy_total_1"),
        _energy("dc_energy_total_2"),
        _voltage("dc_voltage_0"),
        _voltage("dc_voltage_1"),
        _voltage("dc_voltage_2"),
        _current("dc_current_0"),
        _current("dc_current_1"),
        _current("dc_current_2"),
        # Insulation
        _diagnostic("insulation_resistance"),
        _current("insulation_residual_current"),
    ],
    DeviceType.SUNNY_BOY: [
        # PV
        _power("pv_power"),
        _energy("pv_energy_total"),
        # AC power
        _power("ac_power"),
        _power("ac_power_l1"),
        _power("ac_power_l2"),
        _power("ac_power_l3"),
        # AC voltage
        _voltage("ac_voltage_l1"),
        _voltage("ac_voltage_l2"),
        _voltage("ac_voltage_l3"),
        _voltage("ac_voltage_l1_l2"),
        _voltage("ac_voltage_l2_l3"),
        _voltage("ac_voltage_l3_l1"),
        # AC current
        _current("ac_current"),
        _current("ac_current_l1"),
        _current("ac_current_l2"),
        _current("ac_current_l3"),
        # AC frequency
        _frequency("grid_frequency"),
        # AC reactive power
        _reactive_power("ac_reactive_power"),
        _reactive_power("ac_reactive_power_l1"),
        _reactive_power("ac_reactive_power_l2"),
        _reactive_power("ac_reactive_power_l3"),
        # AC apparent power
        _apparent_power("ac_apparent_power"),
        _apparent_power("ac_apparent_power_l1"),
        _apparent_power("ac_apparent_power_l2"),
        _apparent_power("ac_apparent_power_l3"),
        # AC power factor
        _power_factor("power_factor"),
        _power_factor("power_factor_eei"),
        # DC strings (0-based)
        _power("dc_power_0"),
        _power("dc_power_1"),
        _voltage("dc_voltage_0"),
        _voltage("dc_voltage_1"),
        _current("dc_current_0"),
        _current("dc_current_1"),
        # Insulation
        _diagnostic("insulation_resistance"),
        _current("insulation_residual_current"),
    ],
}

_ENTITY_CATEGORY: Final[dict[str, EntityCategory]] = {
    "battery_nominal_capacity": EntityCategory.DIAGNOSTIC,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SmaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SMA sensor entities based on a config entry."""
    coordinator = config_entry.runtime_data
    descriptions = SENSOR_DESCRIPTIONS[coordinator.device_type]
    async_add_entities(
        SmaSensor(coordinator, description) for description in descriptions
    )


class SmaSensor(SmaEntity, SensorEntity):
    """Defines a SMA sensor entity."""

    entity_description: SmaSensorEntityDescription

    def __init__(
        self,
        coordinator: SmaCoordinator,
        description: SmaSensorEntityDescription,
    ) -> None:
        """Initialize a SMA sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}-{description.key}"
        self._attr_translation_key = description.key
        if (category := _ENTITY_CATEGORY.get(description.key)) is not None:
            self._attr_entity_category = category
        self._attr_native_value = self._read_value()

    def _read_value(self) -> StateType:
        """Read the field value from the device component."""
        value = getattr(self.device, self.entity_description.key)
        if isinstance(value, IntEnum):
            return value.name.lower()
        if isinstance(value, float):
            return round(value, 4)
        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self._read_value()
        self.async_write_ha_state()
