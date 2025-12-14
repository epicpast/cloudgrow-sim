"""Wind sensor implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudgrow_sim.core.base import Sensor
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState

if TYPE_CHECKING:
    from numpy.random import Generator


@register_component("sensor", "wind")
class WindSensor(Sensor):
    """Wind speed and direction sensor (anemometer).

    Measures wind speed in m/s and direction in degrees from North.
    Typically located exterior to the greenhouse.

    Attributes:
        name: Unique sensor identifier.
        location: Typically 'exterior'.
        noise_std_dev: Speed measurement noise in m/s.
        direction_noise_std_dev: Direction measurement noise in degrees.
    """

    def __init__(
        self,
        name: str,
        location: str = "exterior",
        *,
        noise_std_dev: float = 0.0,
        direction_noise_std_dev: float = 0.0,
        enabled: bool = True,
        rng: Generator | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize wind sensor.

        Args:
            name: Unique identifier.
            location: Sensor placement (typically 'exterior').
            noise_std_dev: Speed measurement noise in m/s.
            direction_noise_std_dev: Direction measurement noise in degrees.
            enabled: Whether sensor is active.
            rng: NumPy random generator for reproducible simulations.
            seed: Seed for creating a new random generator if rng is None.
        """
        super().__init__(
            name,
            location,
            noise_std_dev=noise_std_dev,
            enabled=enabled,
            rng=rng,
            seed=seed,
        )
        self._direction_noise = direction_noise_std_dev

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read wind speed and direction from state.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'wind_speed' (m/s) and 'wind_direction' (degrees).
        """
        speed = state.wind_speed
        direction = state.wind_direction

        # Add speed noise (ensure non-negative)
        speed = self._add_noise(speed)
        speed = max(0.0, speed)

        # Add direction noise (wrap to 0-360)
        direction = self._add_noise(direction, self._direction_noise)
        direction = direction % 360.0

        return {"wind_speed": speed, "wind_direction": direction}
