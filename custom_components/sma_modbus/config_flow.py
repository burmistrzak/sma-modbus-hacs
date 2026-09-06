"""Config flow for the SMA Modbus integration."""

from __future__ import annotations

import logging
import re
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
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
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


def _extract_serial(hostname: str) -> str | None:
    """Extract the serial number from an SMA mDNS hostname.

    SMA devices advertise hostnames like ``SMA12345678.local``.
    Returns the numeric serial as a string, or ``None``.
    """
    match = re.match(r"SMA(\d+)", hostname, re.IGNORECASE)
    return match.group(1) if match else None


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


async def _async_probe_device_type(
    host: str, port: int
) -> DeviceType | None:
    """Try each device type until one answers.

    Returns the first matching ``DeviceType`` or ``None``.
    """
    for device_type in DeviceType:
        params = ModbusTcpParams(host=host, port=port)
        connection = ModbusConnection(params)
        try:
            device = DEVICE_CLASSES[device_type](connection)
            await device.async_update()
        except (ModbusError, OSError):
            continue
        else:
            return device_type
        finally:
            with suppress(ModbusError, OSError):
                await connection.close()
    return None


class SmaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMA."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_data: dict[str, Any] = {}

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle Zeroconf discovery.

        Extracts the serial from the mDNS hostname (``SMA<serial>.local``),
        sets the unique ID, and probes the device to determine its type.
        If already configured, updates the host if it changed.
        """
        host = discovery_info.host
        serial = _extract_serial(discovery_info.hostname)
        if serial is None:
            # No serial in hostname — fall through to manual setup.
            self._discovered_data = {CONF_HOST: host}
            return await self.async_step_user()

        unique_id = f"SMA{serial}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        # Probe the device to determine its type.
        device_type = await _async_probe_device_type(host, DEFAULT_PORT)
        if device_type is None:
            # Can't determine type — fall through to manual setup.
            self._discovered_data = {CONF_HOST: host}
            return await self.async_step_user()

        self._discovered_data = {
            CONF_DEVICE_TYPE: device_type.value,
            CONF_HOST: host,
            CONF_PORT: DEFAULT_PORT,
        }
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_data[CONF_HOST],
                data=self._discovered_data,
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "device": DEVICE_NAMES[
                    DeviceType(self._discovered_data[CONF_DEVICE_TYPE])
                ],
            },
        )

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
                    unique_id = f"SMA{serial}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: data[CONF_HOST]}
                    )
                    return self.async_create_entry(
                        title=data[CONF_HOST],
                        data=data,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self._discovered_data or None),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
