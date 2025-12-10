"""Solar radiation sensor implementations."""

from __future__ import annotations

import random

from cloudgrow_sim.core.base import Sensor
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState
from cloudgrow_sim.physics.solar import par_from_solar


@register_component("sensor", "solar_radiation")
class SolarRadiationSensor(Sensor):
    """Pyranometer sensor measuring global horizontal irradiance.

    Measures total solar radiation in W/m².

    Attributes:
        name: Unique sensor identifier.
        location: Typically 'exterior' for pyranometers.
        noise_std_dev: Measurement noise in W/m².
    """

    def __init__(
        self,
        name: str,
        location: str = "exterior",
        *,
        noise_std_dev: float = 0.0,
        enabled: bool = True,
    ) -> None:
        """Initialize solar radiation sensor."""
        super().__init__(name, location, noise_std_dev=noise_std_dev, enabled=enabled)

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read solar radiation from state.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'solar_radiation' in W/m².
        """
        true_value = state.solar_radiation

        # Add measurement noise (ensure non-negative)
        if self.noise_std_dev > 0:
            noise = random.gauss(0, self.noise_std_dev)
            measured = max(0.0, true_value + noise)
        else:
            measured = true_value

        return {"solar_radiation": measured}


@register_component("sensor", "par")
class PARSensor(Sensor):
    """Photosynthetically Active Radiation (PAR) sensor.

    Measures PAR in µmol/(m²·s), typically used for plant growth monitoring.
    Can either read from state directly or calculate from solar radiation.

    Attributes:
        name: Unique sensor identifier.
        location: 'interior' for transmitted PAR, 'exterior' for incident.
        noise_std_dev: Measurement noise in µmol/(m²·s).
    """

    def __init__(
        self,
        name: str,
        location: str = "interior",
        *,
        noise_std_dev: float = 0.0,
        enabled: bool = True,
    ) -> None:
        """Initialize PAR sensor."""
        super().__init__(name, location, noise_std_dev=noise_std_dev, enabled=enabled)

    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Read PAR from state.

        Calculates PAR from solar radiation, applying covering transmittance
        for interior sensors.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'par' in µmol/(m²·s).
        """
        # Calculate PAR from solar radiation
        solar = state.solar_radiation

        if self.location == "interior":
            # Apply covering PAR transmittance
            solar *= state.covering.transmittance_par

        par = par_from_solar(solar)

        # Add measurement noise (ensure non-negative)
        if self.noise_std_dev > 0:
            noise = random.gauss(0, self.noise_std_dev)
            par = max(0.0, par + noise)

        return {"par": par}
