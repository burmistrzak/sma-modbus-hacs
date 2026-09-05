"""Config flow for the SMA Modbus integration."""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import (
    CONF_DEVICE_TYPE,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_UNIT_IDS,
    DEVICE_NAMES,
    DOMAIN,
)
from .sma_modbus import DEVICE_CLASSES, DeviceType

_LOGGER = logging.getLogger(__name__)

_PORT = NumberSelector(
    NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
)
_UNIT = NumberSelector(
    NumberSelectorConfig(min=1, max=247, step=1, mode=NumberSelectorMode.BOX)
)


def _device_options() -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=device_type.value, label=DEVICE_NAMES[device_type])
        for device_type in DeviceType
    ]


def _schema(device_type: DeviceType | None = None) -> vol.Schema:
    """Build the user form schema.

    The unit ID default follows the selected device type: 2 for the Sunny
    Home Manager, 3 for inverters.
    """
    default_unit = (
        DEFAULT_UNIT_IDS[device_type]
        if device_type
        else next(iter(DEFAULT_UNIT_IDS.values()))
    )
    return vol.Schema(
        {
            vol.Required(CONF_DEVICE_TYPE): SelectSelector(
                SelectSelectorConfig(
                    options=_device_options(),
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_HOST): TextSelector(),
            vol.Required(CONF_PORT, default=DEFAULT_PORT): _PORT,
            vol.Required(CONF_UNIT_ID, default=default_unit): _UNIT,
        }
    )


async def _async_validate(
    hass: HomeAssistant, data: dict[str, Any]
) -> tuple[DeviceType, int | None]:
    """Probe the device by reading one refresh.

    Returns the device type and serial number (if the device reports one).
    Raises CannotConnect on a Modbus error or an unreachable device.
    """
    params = ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT])
    device_type = DeviceType(data[CONF_DEVICE_TYPE])
    connection = ModbusConnection(params)
    try:
        unit = connection.for_unit(data[CONF_UNIT_ID])
        device = DEVICE_CLASSES[device_type](unit)
        await device.async_update()
    except (ModbusError, OSError) as err:
        raise CannotConnect from err
    finally:
        with suppress(ModbusError, OSError):
            await connection.close()
    serial = getattr(device, "serial_number", None)
    return device_type, serial


class SmaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMA."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_DEVICE_TYPE: user_input[CONF_DEVICE_TYPE],
                CONF_HOST: str(user_input[CONF_HOST]).strip(),
                CONF_PORT: int(user_input[CONF_PORT]),
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }
            try:
                device_type, serial = await _async_validate(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Use the serial number as the unique ID when the device
                # reports one (inverters); fall back to the connection
                # parameters for devices without a Type Label block.
                if serial is not None:
                    unique_id = str(serial)
                else:
                    unique_id = (
                        f"{data[CONF_HOST]}:{data[CONF_PORT]}"
                        f":{data[CONF_UNIT_ID]}:{device_type.value}"
                    )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_HOST],
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(
                DeviceType(user_input[CONF_DEVICE_TYPE])
                if user_input and CONF_DEVICE_TYPE in user_input
                else None
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
