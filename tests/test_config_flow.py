"""Test the SMA Modbus config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sma_modbus.const import CONF_DEVICE_TYPE, CONF_UNIT_ID, DOMAIN
from custom_components.sma_modbus.sma_modbus import DeviceType, DiscoveryInfo, Vendor

SERIAL = 30001234
UNIQUE_ID = f"SMA{SERIAL}"


def _mock_discovery_info(
    device_type: DeviceType = DeviceType.SUNNY_BOY_SMART_ENERGY,
) -> DiscoveryInfo:
    """Return a fake DiscoveryInfo."""
    return DiscoveryInfo(
        device_type=device_type,
        serial_number=SERIAL,
        unit_id=3,
        susy_id=270,
        modbus_profile_revision=1140,
        device_class=8009,
        device_model=19085,
        vendor=Vendor.SMA.value,
    )


async def test_user_flow_success(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Test the user-initiated config flow succeeds."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.sma_modbus.config_flow._async_discover",
        AsyncMock(return_value=_mock_discovery_info()),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.178.1", CONF_PORT: 502, CONF_UNIT_ID: 0},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.178.1"
    assert result["data"][CONF_HOST] == "192.168.178.1"
    assert result["data"][CONF_PORT] == 502
    assert result["data"][CONF_DEVICE_TYPE] == DeviceType.SUNNY_BOY_SMART_ENERGY.value


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Test the user flow shows an error when discovery fails."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.sma_modbus.config_flow._async_discover",
        AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.178.1", CONF_PORT: 502, CONF_UNIT_ID: 0},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "cannot_connect"


async def test_user_flow_already_configured(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Test the user flow aborts when the device is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UNIQUE_ID,
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_DEVICE_TYPE: DeviceType.SUNNY_BOY_SMART_ENERGY.value,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.sma_modbus.config_flow._async_discover",
        AsyncMock(return_value=_mock_discovery_info()),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.178.50", CONF_PORT: 502, CONF_UNIT_ID: 0},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_flow_success(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Test the zeroconf discovery flow succeeds."""
    zeroconf_info = type(
        "ZeroconfServiceInfo",
        (),
        {
            "host": "192.168.178.1",
            "hostname": f"SMA{SERIAL}.local",
            "port": 80,
        },
    )()

    with patch(
        "custom_components.sma_modbus.config_flow._async_discover",
        AsyncMock(return_value=_mock_discovery_info()),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=zeroconf_info,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "192.168.178.1"
    assert result["data"][CONF_HOST] == "192.168.178.1"
    assert result["data"][CONF_DEVICE_TYPE] == DeviceType.SUNNY_BOY_SMART_ENERGY.value


async def test_zeroconf_flow_already_configured(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Test the zeroconf flow aborts when already configured and updates host."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UNIQUE_ID,
        data={
            CONF_HOST: "192.168.178.1",
            CONF_PORT: 502,
            CONF_DEVICE_TYPE: DeviceType.SUNNY_BOY_SMART_ENERGY.value,
        },
    )
    entry.add_to_hass(hass)

    zeroconf_info = type(
        "ZeroconfServiceInfo",
        (),
        {
            "host": "192.168.178.50",
            "hostname": f"SMA{SERIAL}.local",
            "port": 80,
        },
    )()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=zeroconf_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_no_serial_falls_through(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Test the zeroconf flow falls through to manual setup without a serial."""
    zeroconf_info = type(
        "ZeroconfServiceInfo",
        (),
        {
            "host": "192.168.178.1",
            "hostname": "unknown.local",
            "port": 80,
        },
    )()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=zeroconf_info,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_flow_with_unit_id(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Test the user flow stores a non-default unit ID when provided."""
    info = _mock_discovery_info()
    info = DiscoveryInfo(
        device_type=info.device_type,
        serial_number=info.serial_number,
        unit_id=5,
        susy_id=info.susy_id,
        modbus_profile_revision=info.modbus_profile_revision,
        device_class=info.device_class,
        device_model=info.device_model,
        vendor=info.vendor,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.sma_modbus.config_flow._async_discover",
        AsyncMock(return_value=info),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.178.1", CONF_PORT: 502, CONF_UNIT_ID: 5},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_UNIT_ID] == 5
