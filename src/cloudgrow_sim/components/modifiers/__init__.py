"""Climate modifier components for greenhouse simulation.

This module provides passive elements that affect the greenhouse
climate without active control, such as covering materials and
thermal mass.
"""

from cloudgrow_sim.components.modifiers.covering import CoveringMaterial
from cloudgrow_sim.components.modifiers.thermal_mass import ThermalMass

__all__ = [
    "CoveringMaterial",
    "ThermalMass",
]
