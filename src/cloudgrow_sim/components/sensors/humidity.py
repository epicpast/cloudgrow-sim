"""Humidity sensor implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudgrow_sim.core.base import Sensor
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState

if TYPE_CHECKING:
    from numpy.random import Generator


@register_component("sensor", "humidity")
class HumiditySensor(Sensor):
    """Relative humidity sensor.

    Measures relative humidity as a percentage (0-100%).

    Attributes:
        name: Unique sensor identifier.
        location: 'interior' or 'exterior'.
        noise_std_dev: Standard deviation of measurement noise in %.
    """

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read humidity from state.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'humidity' key in %.
        """
        if self.location == "exterior":
            true_value = state.exterior.humidity
        else:
            true_value = state.interior.humidity

        # Add measurement noise and clamp to valid range
        measured = self._add_noise(true_value)
        measured = max(0.0, min(100.0, measured))

        return {"humidity": measured}


@register_component("sensor", "temp_humidity")
class CombinedTempHumiditySensor(Sensor):
    """Combined temperature and humidity sensor.

    Common sensor type that measures both temperature and humidity
    from a single device (e.g., DHT22, SHT31).

    Attributes:
        name: Unique sensor identifier.
        location: 'interior' or 'exterior'.
        noise_std_dev: Standard deviation for both measurements.
        temp_noise_std_dev: Separate noise for temperature (optional).
        humidity_noise_std_dev: Separate noise for humidity (optional).
    """

    def __init__(
        self,
        name: str,
        location: str = "interior",
        *,
        noise_std_dev: float = 0.0,
        temp_noise_std_dev: float | None = None,
        humidity_noise_std_dev: float | None = None,
        enabled: bool = True,
        rng: Generator | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize combined sensor.

        Args:
            name: Unique identifier.
            location: Sensor placement.
            noise_std_dev: Default noise for both measurements.
            temp_noise_std_dev: Override noise for temperature.
            humidity_noise_std_dev: Override noise for humidity.
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
        self._temp_noise = (
            temp_noise_std_dev if temp_noise_std_dev is not None else noise_std_dev
        )
        self._humidity_noise = (
            humidity_noise_std_dev
            if humidity_noise_std_dev is not None
            else noise_std_dev
        )

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read temperature and humidity from state.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'temperature' (C) and 'humidity' (%) keys.
        """
        air_state = state.exterior if self.location == "exterior" else state.interior

        # Temperature with noise
        temp = self._add_noise(air_state.temperature, self._temp_noise)

        # Humidity with noise (clamped to valid range)
        humidity = self._add_noise(air_state.humidity, self._humidity_noise)
        humidity = max(0.0, min(100.0, humidity))

        return {"temperature": temp, "humidity": humidity}
