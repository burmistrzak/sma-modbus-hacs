"""pytest fixtures for the SMA custom integration tests."""

from pytest_homeassistant_custom_component.plugins import (  # noqa: F401
    enable_custom_integrations,
)

pytest_plugins = ("pytest_homeassistant_custom_component",)
