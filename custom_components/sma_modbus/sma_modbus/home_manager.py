"""SMA Sunny Home Manager grid meter.

The Sunny Home Manager is a grid meter that reports total imported and
exported energy together with the instantaneous import and export power.
Register addresses per the SMA Modbus profile, read as input registers.
"""

from modbus_connection.model import int32, uint32

from ._base import SmaComponent


class SunnyHomeManager(SmaComponent):
    """Grid import/export energy and power of a Sunny Home Manager."""

    # Two contiguous served blocks; the planner fetches each in one request.
    register_ranges = (
        (30581, 30584),  # grid energy counters
        (30865, 30868),  # grid power
    )

    grid_import_energy = uint32(30581, unit="Wh", nan=0xFFFFFFFF)
    """Total active energy imported from the grid (Measurement.GridMs.TotWhIn)."""

    grid_export_energy = uint32(30583, unit="Wh", nan=0xFFFFFFFF)
    """Total active energy exported to the grid (Measurement.GridMs.TotWhOut)."""

    grid_import_power = int32(30865, unit="W", nan=0x80000000)
    """Active power imported from the grid (TotalWIn)."""

    grid_export_power = int32(30867, unit="W", nan=0x80000000)
    """Active power exported to the grid (TotalWOut)."""
