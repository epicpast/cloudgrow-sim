"""Solar radiation sensor implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cloudgrow_sim.core.base import Sensor
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState
from cloudgrow_sim.physics.solar import par_from_solar

if TYPE_CHECKING:
    from numpy.random import Generator


@register_component("sensor", "solar_radiation")
class SolarRadiationSensor(Sensor):
    """Pyranometer sensor measuring global horizontal irradiance.

    Measures total solar radiation in W/m2.

    Attributes:
        name: Unique sensor identifier.
        location: Typically 'exterior' for pyranometers.
        noise_std_dev: Measurement noise in W/m2.
    """

    def __init__(
        self,
        name: str,
        location: str = "exterior",
        *,
        noise_std_dev: float = 0.0,
        enabled: bool = True,
        rng: Generator | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize solar radiation sensor."""
        super().__init__(
            name,
            location,
            noise_std_dev=noise_std_dev,
            enabled=enabled,
            rng=rng,
            seed=seed,
        )

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read solar radiation from state.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'solar_radiation' in W/m2.
        """
        true_value = state.solar_radiation

        # Add measurement noise (ensure non-negative)
        measured = self._add_noise(true_value)
        measured = max(0.0, measured)

        return {"solar_radiation": measured}


@register_component("sensor", "par")
class PARSensor(Sensor):
    """Photosynthetically Active Radiation (PAR) sensor.

    Measures PAR in umol/(m2*s), typically used for plant growth monitoring.
    Can either read from state directly or calculate from solar radiation.

    Attributes:
        name: Unique sensor identifier.
        location: 'interior' for transmitted PAR, 'exterior' for incident.
        noise_std_dev: Measurement noise in umol/(m2*s).
    """

    def __init__(
        self,
        name: str,
        location: str = "interior",
        *,
        noise_std_dev: float = 0.0,
        enabled: bool = True,
        rng: Generator | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize PAR sensor."""
        super().__init__(
            name,
            location,
            noise_std_dev=noise_std_dev,
            enabled=enabled,
            rng=rng,
            seed=seed,
        )

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read PAR from state.

        Calculates PAR from solar radiation, applying covering transmittance
        for interior sensors.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'par' in umol/(m2*s).
        """
        # Calculate PAR from solar radiation
        solar = state.solar_radiation

        if self.location == "interior":
            # Apply covering PAR transmittance
            solar *= state.covering.transmittance_par

        par = par_from_solar(solar)

        # Add measurement noise (ensure non-negative)
        par = self._add_noise(par)
        par = max(0.0, par)

        return {"par": par}
