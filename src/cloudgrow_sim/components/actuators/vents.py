"""Vent actuator implementations."""

from __future__ import annotations

from cloudgrow_sim.core.base import Actuator
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState
from cloudgrow_sim.physics.ventilation import (
    combined_natural_ventilation,
    vent_opening_area,
)


@register_component("actuator", "roof_vent")
class RoofVent(Actuator):
    """Roof vent for natural ventilation.

    Roof vents leverage both stack effect (hot air rises) and
    wind-driven ventilation for passive cooling.

    Attributes:
        name: Unique actuator identifier.
        width: Vent width in meters.
        height: Vent height in meters.
        height_above_floor: Height of vent above floor in meters.
    """

    def __init__(
        self,
        name: str,
        *,
        width: float = 1.0,
        height: float = 0.5,
        height_above_floor: float = 4.0,
        discharge_coefficient: float = 0.65,
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize roof vent.

        Args:
            name: Unique identifier.
            width: Vent width in m.
            height: Vent height in m.
            height_above_floor: Height of vent center above floor in m.
            discharge_coefficient: Flow coefficient for opening.
            output_limits: Min/max opening fraction.
            enabled: Whether actuator is active.
        """
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._width = width
        self._height = height
        self._height_above_floor = height_above_floor
        self._discharge_coefficient = discharge_coefficient

    @property
    def opening_area(self) -> float:
        """Current opening area based on output setting."""
        return vent_opening_area(self._width, self._height, self.output)

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the roof vent.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with 'ventilation_rate' (m³/s).
        """
        if self.output <= 0:
            return {"ventilation_rate": 0.0, "opening_area": 0.0}

        flow_rate = combined_natural_ventilation(
            opening_area=self.opening_area,
            height=self._height_above_floor,
            t_inside=state.interior.temperature,
            t_outside=state.exterior.temperature,
            wind_speed=state.wind_speed,
            discharge_coefficient=self._discharge_coefficient,
        )

        return {
            "ventilation_rate": flow_rate,
            "opening_area": self.opening_area,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply vent effect to state."""
        pass


@register_component("actuator", "side_vent")
class SideVent(Actuator):
    """Side wall vent for natural ventilation.

    Side vents are lower than roof vents and primarily rely on
    wind-driven ventilation. Often used for intake air.

    Attributes:
        name: Unique actuator identifier.
        width: Vent width in meters.
        height: Vent height in meters.
        height_above_floor: Height of vent above floor in meters.
    """

    def __init__(
        self,
        name: str,
        *,
        width: float = 2.0,
        height: float = 1.0,
        height_above_floor: float = 1.0,
        discharge_coefficient: float = 0.65,
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize side vent."""
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._width = width
        self._height = height
        self._height_above_floor = height_above_floor
        self._discharge_coefficient = discharge_coefficient

    @property
    def opening_area(self) -> float:
        """Current opening area based on output setting."""
        return vent_opening_area(self._width, self._height, self.output)

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the side vent."""
        if self.output <= 0:
            return {"ventilation_rate": 0.0, "opening_area": 0.0}

        flow_rate = combined_natural_ventilation(
            opening_area=self.opening_area,
            height=self._height_above_floor,
            t_inside=state.interior.temperature,
            t_outside=state.exterior.temperature,
            wind_speed=state.wind_speed,
            discharge_coefficient=self._discharge_coefficient,
        )

        return {
            "ventilation_rate": flow_rate,
            "opening_area": self.opening_area,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply vent effect to state."""
        pass
