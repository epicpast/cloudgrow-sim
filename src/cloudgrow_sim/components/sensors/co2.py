"""CO2 sensor implementation."""

from __future__ import annotations

import random

from cloudgrow_sim.core.base import Sensor
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState


@register_component("sensor", "co2")
class CO2Sensor(Sensor):
    """Carbon dioxide concentration sensor.

    Measures CO2 concentration in parts per million (ppm).
    Typically NDIR (Non-Dispersive Infrared) sensors.

    Attributes:
        name: Unique sensor identifier.
        location: 'interior' or 'exterior'.
        noise_std_dev: Measurement noise in ppm.
    """

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read CO2 concentration from state.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'co2' in ppm.
        """
        if self.location == "exterior":
            true_value = state.exterior.co2_ppm
        else:
            true_value = state.interior.co2_ppm

        # Add measurement noise (ensure non-negative)
        if self.noise_std_dev > 0:
            noise = random.gauss(0, self.noise_std_dev)
            measured = max(0.0, true_value + noise)
        else:
            measured = true_value

        return {"co2": measured}
