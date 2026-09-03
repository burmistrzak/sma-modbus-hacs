"""Support for SMA sensors."""

from dataclasses import dataclass
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
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import SmaConfigEntry
from .coordinator import SmaCoordinator
from .entity import SmaEntity
from .sma_modbus import DeviceType

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


SENSOR_DESCRIPTIONS: Final[dict[DeviceType, list[SmaSensorEntityDescription]]] = {
    DeviceType.SUNNY_HOME_MANAGER: [
        _energy("grid_import_energy"),
        _energy("grid_export_energy"),
        _power("grid_import_power"),
        _power("grid_export_power"),
    ],
    DeviceType.SUNNY_BOY_SMART_ENERGY: [
        _power("pv_power"),
        _energy("pv_energy_total"),
        _energy("battery_charge_energy"),
        _energy("battery_discharge_energy"),
        _power("battery_charge_power"),
        _power("battery_discharge_power"),
        _battery("battery_state_of_charge"),
        _battery("battery_nominal_capacity"),
        _power("dc_power_1"),
        _power("dc_power_2"),
        _power("dc_power_3"),
        _energy("dc_energy_total_1"),
        _energy("dc_energy_total_2"),
        _energy("dc_energy_total_3"),
        _voltage("dc_voltage_1"),
        _voltage("dc_voltage_2"),
        _voltage("dc_voltage_3"),
    ],
    DeviceType.SUNNY_BOY: [
        _power("pv_power"),
        _energy("pv_energy_total"),
        _power("dc_power_1"),
        _power("dc_power_2"),
        _voltage("dc_voltage_1"),
        _voltage("dc_voltage_2"),
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
        if isinstance(value, float):
            return round(value, 4)
        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self._read_value()
        self.async_write_ha_state()
