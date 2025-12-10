"""Curtain actuator implementations."""

from __future__ import annotations

from cloudgrow_sim.core.base import Actuator
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState


@register_component("actuator", "shade_curtain")
class ShadeCurtain(Actuator):
    """Shade curtain for reducing solar radiation.

    Shade curtains reduce solar heat gain and protect plants from
    excessive light intensity. Can be oriented N-S or E-W.

    Attributes:
        name: Unique actuator identifier.
        shade_factor: Maximum shading when fully deployed (0-1).
        orientation: 'north_south' or 'east_west'.
    """

    def __init__(
        self,
        name: str,
        *,
        shade_factor: float = 0.5,
        orientation: str = "north_south",
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize shade curtain.

        Args:
            name: Unique identifier.
            shade_factor: Maximum shading fraction when fully deployed.
            orientation: Curtain orientation ('north_south' or 'east_west').
            output_limits: Min/max deployment fraction.
            enabled: Whether actuator is active.
        """
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._shade_factor = shade_factor
        self._orientation = orientation

    @property
    def shade_factor(self) -> float:
        """Maximum shading factor."""
        return self._shade_factor

    @property
    def orientation(self) -> str:
        """Curtain orientation."""
        return self._orientation

    @property
    def current_shading(self) -> float:
        """Current effective shading based on deployment."""
        return self._shade_factor * self.output

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the shade curtain.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with shading effects.
        """
        effective_shading = self.current_shading

        # Calculate solar reduction
        solar_reduction = state.solar_radiation * effective_shading

        return {
            "solar_reduction": solar_reduction,
            "effective_shading": effective_shading,
            "transmittance_modifier": 1.0 - effective_shading,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply curtain effect to state."""
        pass


@register_component("actuator", "thermal_curtain")
class ThermalCurtain(Actuator):
    """Thermal curtain for heat retention.

    Thermal curtains reduce heat loss at night by creating an
    insulating air gap and reducing radiation to the cold sky.

    Attributes:
        name: Unique actuator identifier.
        thermal_resistance: Additional R-value when deployed (m²·K/W).
        transmittance_solar: Solar transmittance when deployed.
    """

    def __init__(
        self,
        name: str,
        *,
        thermal_resistance: float = 0.5,
        transmittance_solar: float = 0.3,
        orientation: str = "east_west",
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize thermal curtain.

        Args:
            name: Unique identifier.
            thermal_resistance: Added R-value when fully deployed (m²·K/W).
            transmittance_solar: Solar transmittance when deployed (0-1).
            orientation: Curtain orientation.
            output_limits: Min/max deployment fraction.
            enabled: Whether actuator is active.
        """
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._thermal_resistance = thermal_resistance
        self._transmittance_solar = transmittance_solar
        self._orientation = orientation

    @property
    def thermal_resistance(self) -> float:
        """Maximum thermal resistance in m²·K/W."""
        return self._thermal_resistance

    @property
    def current_r_value(self) -> float:
        """Current effective R-value based on deployment."""
        return self._thermal_resistance * self.output

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the thermal curtain.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with thermal and solar effects.
        """
        deployment = self.output

        # Calculate effective U-value reduction
        # When fully deployed, adds thermal_resistance to existing R-value
        base_r = 1.0 / state.covering.u_value
        added_r = self._thermal_resistance * deployment
        effective_r = base_r + added_r
        effective_u = 1.0 / effective_r

        # Calculate solar transmittance reduction
        base_transmittance = state.covering.transmittance_solar
        curtain_effect = deployment * (1.0 - self._transmittance_solar)
        effective_transmittance = base_transmittance * (1.0 - curtain_effect)

        return {
            "effective_u_value": effective_u,
            "u_value_reduction": state.covering.u_value - effective_u,
            "effective_transmittance": effective_transmittance,
            "added_r_value": added_r,
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply curtain effect to state."""
        pass
