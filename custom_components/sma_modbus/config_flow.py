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
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import (
    CONF_DEVICE_TYPE,
    DEFAULT_PORT,
    DEVICE_NAMES,
    DOMAIN,
)
from .sma_modbus import DEVICE_CLASSES, DeviceType

_LOGGER = logging.getLogger(__name__)

_PORT = NumberSelector(
    NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
)


def _device_options() -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=device_type.value, label=DEVICE_NAMES[device_type])
        for device_type in DeviceType
    ]


def _schema(suggested_values: dict[str, Any] | None = None) -> vol.Schema:
    """Build the user form schema."""
    suggested = suggested_values or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_DEVICE_TYPE,
                default=suggested.get(CONF_DEVICE_TYPE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_device_options(),
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_HOST,
                default=suggested.get(CONF_HOST),
            ): TextSelector(),
            vol.Required(
                CONF_PORT,
                default=suggested.get(CONF_PORT, DEFAULT_PORT),
            ): _PORT,
        }
    )


async def _async_validate(
    hass: HomeAssistant, data: dict[str, Any]
) -> int | None:
    """Probe the device by reading one refresh.

    Returns the serial number if the device reports one.
    Raises CannotConnect on a Modbus error or an unreachable device.
    """
    params = ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT])
    device_type = DeviceType(data[CONF_DEVICE_TYPE])
    connection = ModbusConnection(params)
    try:
        device = DEVICE_CLASSES[device_type](connection)
        await device.async_update()
    except (ModbusError, OSError) as err:
        raise CannotConnect from err
    finally:
        with suppress(ModbusError, OSError):
            await connection.close()
    return getattr(device, "serial_number", None)


class SmaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMA."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._dhcp_host: str | None = None

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        self._dhcp_host = discovery_info.ip
        # Abort if an entry with this host already exists.
        for entry in self._async_current_entries(include_ignore=False):
            if entry.data.get(CONF_HOST) == discovery_info.ip:
                self._abort_if_unique_id_configured()
                return self.async_abort(reason="already_configured")
        return await self.async_step_user()

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
            }
            try:
                serial = await _async_validate(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if serial is None:
                    errors["base"] = "no_serial"
                else:
                    unique_id = str(serial)
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=data[CONF_HOST],
                        data=data,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(
                {CONF_HOST: self._dhcp_host} if self._dhcp_host else None
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
