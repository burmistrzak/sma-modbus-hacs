# SMA Modbus

Custom Home Assistant integration for **SMA** devices, utilizing the modernized Modbus stack.

The device-specific communication lives in the `sma_modbus` library, which is
**vendorized** under `custom_components/sma_modbus/sma_modbus/`, so this integration
is self-contained and installable through [HACS](https://hacs.xyz).

> [!WARNING]
> This is an experimental, agentic port of the core [Fonius](https://github.com/home-assistant/core/tree/dev/homeassistant/components/fronius) component.
> 
> Do not use it for anything else than testing.
>
> You have been warned.


## What you get

One sensor per measurement, polled over Modbus:

- **Sunny Home Manager 2.0** — grid import/export energy and power.
- **Sunny Boy Smart Energy** — PV energy and power, battery charge/discharge
  energy and power, battery state of charge, and per-string DC power, voltage
  and lifetime energy.
- **Sunny Boy** — PV energy and power, per-string DC power and voltage.

A measurement reads as `unavailable` when the device reports its not-a-value
sentinel, so a powered-down or unsupported value is distinct from a real zero.

## Installation (HACS)

1. Add this repository to HACS as a custom integration
   (*HACS → Integrations → ⋮ → Custom repositories*, category *Integration*).
2. Install **SMA Modbus**, then restart Home Assistant.
3. *Settings → Devices & Services → Add integration → SMA Modbus*.
4. Pick your device type, enter the IP/hostname, Modbus port (default 502) and
   unit ID (Home Manager: 2, inverters: 3).

> Modbus must be enabled on the device (SMA inverters: *Device configuration →
> Modbus → Enable Modbus TCP*).

## Requirements

- Home Assistant 2026.9.0 or later
- `modbus-connection[tmodbus]` is installed automatically from `manifest.json`
  `requirements`.

## About this custom build

This custom integration **opens its own Modbus TCP connection**, which is the
practical way to make it testable through HACS *before* the shared-connection
Modbus integration is released in Home Assistant core.

A matching **core integration** (`sma_modbus`) exists that, once the new Modbus
integration is in core, asks the Modbus integration for a shared unit instead
(`async_get_unit`) and consumes the standalone `sma-modbus` library from PyPI.
When that core integration ships, this custom component is superseded by it
and can be removed.

## Development

```bash
scripts/setup     # install dev / lint / test requirements
ruff check . && ruff format --check .
pytest
scripts/develop   # start Home Assistant with config/
```
