# SMA Modbus

Custom Home Assistant integration for **SMA** devices, utilizing the modernized Modbus stack.

The device-specific communication lives in the [`sma_modbus`](https://github.com/burmistrzak/sma-modbus) library, which is
**vendorized** under `custom_components/sma_modbus/sma_modbus/`, so this integration
is self-contained and installable through [HACS](https://hacs.xyz).

> [!WARNING]
> This is a **beta** integration, based on a partial agentic port of the core [Fronius](https://github.com/home-assistant/core/tree/dev/homeassistant/components/fronius) component.
> 
> While everything _works_ on my end, do not use it for anything else than testing
> and reporting bugs just yet.
>
> **You have been warned.**


## Supported Devices

- **Sunny Home Manager 2.0**
- **Sunny Boy Smart Energy 3.6-6.0**
- **Sunny Boy 3.0-6.0**
- **Sunny Tripower 3.0-6.0** <sup>untested</sup>

Only _essential parameters_ are enabled by default.


## Installation (HACS)

1. Add this repository to HACS as a custom integration
   (*HACS → Integrations → ⋮ → Custom repositories*, category *Integration*).
2. Install **SMA Modbus**, then restart Home Assistant.
3. *Settings → Devices & Services → Add integration → SMA Modbus*.
4. Enter the IP/hostname and Modbus port (default 502). The device type is
   auto-detected. Optionally provide a Unit ID if auto-discovery fails.

> Modbus must be enabled on the device.

## Requirements

- Home Assistant 2026.9.0 or later
- `modbus-connection[tmodbus]` is installed automatically from `manifest.json`
  requirements.


## Removal

1. *Settings → Devices & Services → SMA Modbus* → select the device → **Delete**.
   This removes the config entry and all entities.
2. In HACS, uninstall **SMA Modbus**, then restart Home Assistant.


## Development

```bash
scripts/setup     # install dev / lint / test requirements
ruff check . && ruff format --check .
pytest
scripts/develop   # start Home Assistant with config/
```

## Disclaimer

This is an unofficial integration and in no way affiliated with SMA Solar Technology AG.
