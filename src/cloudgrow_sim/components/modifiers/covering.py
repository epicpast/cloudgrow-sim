"""Covering material modifier implementation."""

from __future__ import annotations

from typing import Any

from cloudgrow_sim.core.base import ClimateModifier
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import (
    COVERING_MATERIALS,
    CoveringProperties,
    GreenhouseState,
)


@register_component("modifier", "covering")
class CoveringMaterial(ClimateModifier):
    """Greenhouse covering material modifier.

    Represents the optical and thermal properties of the greenhouse
    covering (glass, polyethylene, polycarbonate, etc.).

    This modifier affects:
    - Solar transmission into the greenhouse
    - Heat loss through the covering
    - Long-wave radiation exchange with the sky

    Attributes:
        name: Unique modifier identifier.
        properties: CoveringProperties object with material characteristics.
    """

    def __init__(
        self,
        name: str,
        *,
        material: str | None = None,
        properties: CoveringProperties | None = None,
        enabled: bool = True,
    ) -> None:
        """Initialize covering material.

        Args:
            name: Unique identifier.
            material: Pre-defined material name (from COVERING_MATERIALS).
            properties: Custom CoveringProperties (overrides material).
            enabled: Whether modifier is active.

        Raises:
            ValueError: If neither material nor properties provided.
        """
        super().__init__(name, enabled=enabled)

        if properties is not None:
            self._properties = properties
        elif material is not None:
            if material not in COVERING_MATERIALS:
                available = list(COVERING_MATERIALS.keys())
                msg = f"Unknown material '{material}'. Available: {available}"
                raise ValueError(msg)
            self._properties = COVERING_MATERIALS[material]
        else:
            # Default to double polyethylene
            self._properties = COVERING_MATERIALS["double_polyethylene"]

    @property
    def properties(self) -> CoveringProperties:
        """Covering material properties."""
        return self._properties

    @property
    def transmittance_solar(self) -> float:
        """Solar transmittance (0-1)."""
        return self._properties.transmittance_solar

    @property
    def transmittance_par(self) -> float:
        """PAR transmittance (0-1)."""
        return self._properties.transmittance_par

    @property
    def u_value(self) -> float:
        """Overall heat transfer coefficient (W/(m²·K))."""
        return self._properties.u_value

    def get_properties(self) -> dict[str, Any]:
        """Get all covering properties.

        Returns:
            Dictionary of material properties.
        """
        return {
            "material_name": self._properties.material_name,
            "transmittance_solar": self._properties.transmittance_solar,
            "transmittance_par": self._properties.transmittance_par,
            "transmittance_thermal": self._properties.transmittance_thermal,
            "u_value": self._properties.u_value,
            "reflectance_solar": self._properties.reflectance_solar,
            "absorptance_solar": self._properties.absorptance_solar,
        }

    def update(self, dt: float, state: GreenhouseState) -> None:
        """Update modifier state.

        Covering material is passive and doesn't change during simulation.

        Args:
            dt: Time step in seconds.
            state: Current greenhouse state.
        """
        pass
