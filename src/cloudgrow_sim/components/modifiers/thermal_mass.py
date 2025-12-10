"""Thermal mass modifier implementation."""

from __future__ import annotations

from typing import Any

from cloudgrow_sim.core.base import ClimateModifier
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState


@register_component("modifier", "thermal_mass")
class ThermalMass(ClimateModifier):
    """Thermal mass element for temperature buffering.

    Thermal mass (concrete floors, water barrels, etc.) stores
    heat during the day and releases it at night, moderating
    temperature swings.

    Attributes:
        name: Unique modifier identifier.
        mass: Mass of thermal storage in kg.
        specific_heat: Specific heat capacity in J/(kg·K).
        surface_area: Surface area exposed to air in m².
    """

    def __init__(
        self,
        name: str,
        *,
        mass: float = 1000.0,
        specific_heat: float = 4186.0,  # Water default
        surface_area: float = 10.0,
        initial_temperature: float = 20.0,
        heat_transfer_coefficient: float = 10.0,
        enabled: bool = True,
    ) -> None:
        """Initialize thermal mass.

        Args:
            name: Unique identifier.
            mass: Mass of thermal storage in kg.
            specific_heat: Specific heat capacity in J/(kg·K).
                          Water: 4186, Concrete: ~880
            surface_area: Surface area exposed to air in m².
            initial_temperature: Starting temperature in °C.
            heat_transfer_coefficient: Surface h in W/(m²·K).
            enabled: Whether modifier is active.
        """
        super().__init__(name, enabled=enabled)
        self._mass = mass
        self._specific_heat = specific_heat
        self._surface_area = surface_area
        self._temperature = initial_temperature
        self._heat_transfer_coefficient = heat_transfer_coefficient

    @property
    def mass(self) -> float:
        """Mass in kg."""
        return self._mass

    @property
    def specific_heat(self) -> float:
        """Specific heat capacity in J/(kg·K)."""
        return self._specific_heat

    @property
    def thermal_capacity(self) -> float:
        """Total thermal capacity in J/K."""
        return self._mass * self._specific_heat

    @property
    def temperature(self) -> float:
        """Current temperature of thermal mass in °C."""
        return self._temperature

    @property
    def surface_area(self) -> float:
        """Surface area exposed to air in m²."""
        return self._surface_area

    def get_properties(self) -> dict[str, Any]:
        """Get thermal mass properties.

        Returns:
            Dictionary of thermal properties.
        """
        return {
            "mass": self._mass,
            "specific_heat": self._specific_heat,
            "thermal_capacity": self.thermal_capacity,
            "surface_area": self._surface_area,
            "temperature": self._temperature,
            "heat_transfer_coefficient": self._heat_transfer_coefficient,
        }

    def calculate_heat_exchange(self, air_temperature: float) -> float:
        """Calculate heat exchange with surrounding air.

        Args:
            air_temperature: Surrounding air temperature in °C.

        Returns:
            Heat transfer rate in W (positive = heat to air).
        """
        # Q = h * A * (T_mass - T_air)
        delta_t = self._temperature - air_temperature
        return self._heat_transfer_coefficient * self._surface_area * delta_t

    def update(self, dt: float, state: GreenhouseState) -> None:
        """Update thermal mass temperature.

        Calculates heat exchange with greenhouse air and updates
        the thermal mass temperature.

        Args:
            dt: Time step in seconds.
            state: Current greenhouse state.
        """
        if not self.enabled:
            return

        # Heat exchange with interior air
        q_exchange = self.calculate_heat_exchange(state.interior.temperature)

        # Temperature change of thermal mass
        # dT = Q * dt / (m * c)
        delta_t = -q_exchange * dt / self.thermal_capacity

        self._temperature += delta_t

    def reset(self) -> None:
        """Reset thermal mass to initial conditions."""
        # Would need to store initial temperature to implement properly
        pass


# Pre-defined thermal mass types
THERMAL_MASS_PRESETS: dict[str, dict[str, float]] = {
    "water_barrel_200L": {
        "mass": 200.0,
        "specific_heat": 4186.0,
        "surface_area": 1.5,
    },
    "water_barrel_55gal": {
        "mass": 208.0,
        "specific_heat": 4186.0,
        "surface_area": 1.6,
    },
    "concrete_floor_10cm": {
        "mass": 2400.0,  # kg per m² (density * thickness)
        "specific_heat": 880.0,
        "surface_area": 1.0,  # per m² of floor
    },
    "concrete_block_wall": {
        "mass": 150.0,  # per m² of wall
        "specific_heat": 880.0,
        "surface_area": 1.0,
    },
}
