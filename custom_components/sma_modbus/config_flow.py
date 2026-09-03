"""Config flow for the SMA Modbus integration."""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any

import voluptuous as vol
from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

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

from .const import (
    CONF_DEVICE_TYPE,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
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


def _schema() -> vol.Schema:
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
            vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT,
        }
    )


async def _async_validate(hass: HomeAssistant, data: dict[str, Any]) -> DeviceType:
    """Probe the device by reading one refresh.

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
    return device_type


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
                device_type = await _async_validate(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                unique_id = (
                    f"{data[CONF_HOST]}:{data[CONF_PORT]}"
                    f":{data[CONF_UNIT_ID]}:{device_type.value}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"SMA {DEVICE_NAMES[device_type]}",
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
