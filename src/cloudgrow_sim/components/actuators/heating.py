"""Heating actuator implementations."""

from __future__ import annotations

from cloudgrow_sim.core.base import Actuator
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState


@register_component("actuator", "unit_heater")
class UnitHeater(Actuator):
    """Forced-air unit heater.

    Unit heaters use a fan to blow air over a heat exchanger,
    providing rapid heating response. Common in commercial greenhouses.

    Attributes:
        name: Unique actuator identifier.
        heating_capacity: Maximum heat output in W.
        efficiency: Heating efficiency (0-1).
    """

    def __init__(
        self,
        name: str,
        *,
        heating_capacity: float = 10000.0,
        efficiency: float = 0.85,
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize unit heater.

        Args:
            name: Unique identifier.
            heating_capacity: Maximum heat output in W.
            efficiency: Heating efficiency (0.8-0.95 typical).
            output_limits: Min/max output fraction.
            enabled: Whether actuator is active.
        """
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._heating_capacity = heating_capacity
        self._efficiency = efficiency

    @property
    def heating_capacity(self) -> float:
        """Maximum heating capacity in W."""
        return self._heating_capacity

    @property
    def current_output_watts(self) -> float:
        """Current heat output in W."""
        return self._heating_capacity * self.output * self._efficiency

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the unit heater.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'heat_output' (W) and 'fuel_consumption'.
        """
        del state  # Unused - heater output doesn't depend on state
        heat_output = self.current_output_watts

        # Fuel consumption (assuming natural gas)
        # Energy content of natural gas: ~10.5 kWh/m³
        fuel_input = heat_output / self._efficiency
        fuel_consumption = fuel_input / 10500 / 3600  # m³/s

        return {
            "heat_output": heat_output,
            "fuel_input": fuel_input,
            "fuel_consumption": fuel_consumption,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply heater effect to state."""
        pass


@register_component("actuator", "radiant_heater")
class RadiantHeater(Actuator):
    """Radiant (infrared) heater.

    Radiant heaters heat objects directly through infrared radiation,
    more efficient for heating plants without heating all the air.

    Attributes:
        name: Unique actuator identifier.
        heating_capacity: Maximum radiant output in W.
        radiant_fraction: Fraction of output as radiant heat (vs convective).
    """

    def __init__(
        self,
        name: str,
        *,
        heating_capacity: float = 5000.0,
        radiant_fraction: float = 0.7,
        efficiency: float = 0.90,
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize radiant heater.

        Args:
            name: Unique identifier.
            heating_capacity: Maximum heat output in W.
            radiant_fraction: Fraction as radiant heat (0.6-0.8 typical).
            efficiency: Heating efficiency.
            output_limits: Min/max output fraction.
            enabled: Whether actuator is active.
        """
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._heating_capacity = heating_capacity
        self._radiant_fraction = radiant_fraction
        self._efficiency = efficiency

    @property
    def heating_capacity(self) -> float:
        """Maximum heating capacity in W."""
        return self._heating_capacity

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the radiant heater.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with radiant and convective heat components.
        """
        del state  # Unused - heater output doesn't depend on state
        total_output = self._heating_capacity * self.output * self._efficiency
        radiant_output = total_output * self._radiant_fraction
        convective_output = total_output * (1.0 - self._radiant_fraction)

        return {
            "heat_output": total_output,
            "radiant_heat": radiant_output,
            "convective_heat": convective_output,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply heater effect to state."""
        pass
