# Contributing

This is a custom Home Assistant integration. Contributions are welcome.

## Development setup

```bash
scripts/setup        # install dev / lint / test requirements
```

## Linting and tests

```bash
ruff check .
ruff format --check .
pytest
```

## Running against Home Assistant

```bash
scripts/develop     # start Home Assistant with config/
```

Then add the `SMA Modbus` integration via *Settings → Devices & Services → Add
integration* and point it at your SMA device.
