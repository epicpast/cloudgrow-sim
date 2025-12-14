"""Temperature sensor implementation."""

from __future__ import annotations

from cloudgrow_sim.core.base import Sensor
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState


@register_component("sensor", "temperature")
class TemperatureSensor(Sensor):
    """Temperature sensor that measures air temperature.

    Reads temperature from either interior or exterior air state
    based on location configuration.

    Attributes:
        name: Unique sensor identifier.
        location: 'interior' or 'exterior'.
        noise_std_dev: Standard deviation of measurement noise in C.
    """

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read temperature from state.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'temperature' key in C.
        """
        if self.location == "exterior":
            true_value = state.exterior.temperature
        else:
            true_value = state.interior.temperature

        # Add measurement noise using the base class method
        measured = self._add_noise(true_value)

        return {"temperature": measured}
