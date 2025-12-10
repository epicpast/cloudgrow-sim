"""Fan actuator implementations."""

from __future__ import annotations

from cloudgrow_sim.core.base import Actuator
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState
from cloudgrow_sim.physics.ventilation import (
    fan_flow_rate,
    sensible_heat_ventilation,
)


@register_component("actuator", "exhaust_fan")
class ExhaustFan(Actuator):
    """Exhaust fan for removing air from the greenhouse.

    Exhaust fans create negative pressure, drawing in outside air
    through vents and openings. Primary cooling method in warm weather.

    Attributes:
        name: Unique actuator identifier.
        max_flow_rate: Maximum airflow capacity in m³/s.
        power_consumption: Electrical power at full speed in W.
    """

    def __init__(
        self,
        name: str,
        *,
        max_flow_rate: float = 5.0,
        power_consumption: float = 500.0,
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize exhaust fan.

        Args:
            name: Unique identifier.
            max_flow_rate: Maximum airflow in m³/s.
            power_consumption: Power at full speed in W.
            output_limits: Min/max output fraction.
            enabled: Whether actuator is active.
        """
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._max_flow_rate = max_flow_rate
        self._power_consumption = power_consumption

    @property
    def max_flow_rate(self) -> float:
        """Maximum airflow capacity in m³/s."""
        return self._max_flow_rate

    @property
    def current_flow_rate(self) -> float:
        """Current airflow rate based on output setting."""
        return fan_flow_rate(self._max_flow_rate, 1, self.output)

    @property
    def current_power(self) -> float:
        """Current power consumption in W."""
        # Fan power scales with cube of speed (affinity laws)
        return self._power_consumption * self.output**3

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the exhaust fan.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'ventilation_rate' (m³/s) and 'heat_removal' (W).
        """
        flow_rate = self.current_flow_rate

        # Calculate sensible heat removal (negative = cooling)
        heat_removal = sensible_heat_ventilation(
            flow_rate,
            state.exterior.temperature,
            state.interior.temperature,
            rh_avg=(state.interior.humidity + state.exterior.humidity) / 2,
        )

        return {
            "ventilation_rate": flow_rate,
            "heat_removal": heat_removal,
            "power": self.current_power,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply ventilation effect to state.

        Note: Actual state modification is handled by the simulation engine.
        This method prepares the effect calculation.

        Args:
            dt: Time step in seconds.
            state: Current greenhouse state.
        """
        # Effects are calculated in get_effect() and applied by engine
        pass


@register_component("actuator", "intake_fan")
class IntakeFan(Actuator):
    """Intake fan for bringing outside air into the greenhouse.

    Creates positive pressure, often used with evaporative cooling pads.

    Attributes:
        name: Unique actuator identifier.
        max_flow_rate: Maximum airflow capacity in m³/s.
        power_consumption: Electrical power at full speed in W.
    """

    def __init__(
        self,
        name: str,
        *,
        max_flow_rate: float = 5.0,
        power_consumption: float = 500.0,
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize intake fan."""
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._max_flow_rate = max_flow_rate
        self._power_consumption = power_consumption

    @property
    def current_flow_rate(self) -> float:
        """Current airflow rate based on output setting."""
        return fan_flow_rate(self._max_flow_rate, 1, self.output)

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the intake fan."""
        flow_rate = self.current_flow_rate

        heat_addition = sensible_heat_ventilation(
            flow_rate,
            state.exterior.temperature,
            state.interior.temperature,
        )

        return {
            "ventilation_rate": flow_rate,
            "heat_addition": -heat_addition,  # Positive when bringing in cooler air
            "power": self._power_consumption * self.output**3,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply ventilation effect to state."""
        pass


@register_component("actuator", "circulation_fan")
class CirculationFan(Actuator):
    """Horizontal air flow (HAF) fan for air circulation.

    Circulation fans don't exchange air with outside, but improve
    air mixing and reduce temperature stratification.

    Attributes:
        name: Unique actuator identifier.
        power_consumption: Electrical power at full speed in W.
    """

    def __init__(
        self,
        name: str,
        *,
        power_consumption: float = 100.0,
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize circulation fan."""
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._power_consumption = power_consumption

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the circulation fan.

        Circulation fans primarily reduce temperature stratification
        and improve convective heat transfer coefficients.
        """
        del state  # Unused - circulation fans don't depend on state
        return {
            "air_velocity_increase": 0.5 * self.output,  # m/s contribution
            "power": self._power_consumption * self.output,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply circulation effect to state."""
        pass
