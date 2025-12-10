"""Cooling actuator implementations."""

from __future__ import annotations

from cloudgrow_sim.core.base import Actuator
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState
from cloudgrow_sim.physics.psychrometrics import (
    wet_bulb_temperature,
)


@register_component("actuator", "evaporative_pad")
class EvaporativePad(Actuator):
    """Evaporative cooling pad.

    Evaporative pads cool incoming air by evaporating water.
    Most effective in hot, dry climates. Used with intake fans.

    Attributes:
        name: Unique actuator identifier.
        pad_area: Pad face area in m².
        pad_thickness: Pad thickness in m.
        saturation_efficiency: Cooling efficiency at full water flow (0-1).
    """

    def __init__(
        self,
        name: str,
        *,
        pad_area: float = 10.0,
        pad_thickness: float = 0.15,
        saturation_efficiency: float = 0.85,
        water_consumption_rate: float = 0.001,  # m³/s per m² at full output
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize evaporative pad.

        Args:
            name: Unique identifier.
            pad_area: Face area of pad in m².
            pad_thickness: Pad thickness in m.
            saturation_efficiency: Max cooling efficiency (0.7-0.9 typical).
            water_consumption_rate: Water use per m² at full output.
            output_limits: Min/max water flow fraction.
            enabled: Whether actuator is active.
        """
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._pad_area = pad_area
        self._pad_thickness = pad_thickness
        self._saturation_efficiency = saturation_efficiency
        self._water_consumption_rate = water_consumption_rate

    @property
    def pad_area(self) -> float:
        """Pad face area in m²."""
        return self._pad_area

    @property
    def current_efficiency(self) -> float:
        """Current saturation efficiency based on water flow."""
        return self._saturation_efficiency * self.output

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the evaporative pad.

        The supply air temperature approaches wet-bulb temperature
        based on saturation efficiency.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with cooling effect parameters.
        """
        if self.output <= 0:
            return {
                "supply_temperature": state.exterior.temperature,
                "temperature_drop": 0.0,
                "water_consumption": 0.0,
            }

        t_db = state.exterior.temperature
        rh = state.exterior.humidity

        # Calculate wet-bulb temperature
        t_wb = wet_bulb_temperature(t_db, rh)

        # Supply temperature based on saturation efficiency
        # T_supply = T_db - efficiency * (T_db - T_wb)
        efficiency = self.current_efficiency
        t_supply = t_db - efficiency * (t_db - t_wb)

        # Water consumption
        water_use = self._water_consumption_rate * self._pad_area * self.output

        return {
            "supply_temperature": t_supply,
            "temperature_drop": t_db - t_supply,
            "wet_bulb_temperature": t_wb,
            "saturation_efficiency": efficiency,
            "water_consumption": water_use,  # m³/s
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply cooling effect to state."""
        pass


@register_component("actuator", "fogger")
class Fogger(Actuator):
    """High-pressure fogging system.

    Foggers produce fine water droplets that evaporate in the air,
    providing cooling and humidification. Works inside the greenhouse.

    Attributes:
        name: Unique actuator identifier.
        nozzle_count: Number of fog nozzles.
        flow_rate_per_nozzle: Water flow per nozzle in L/h.
    """

    def __init__(
        self,
        name: str,
        *,
        nozzle_count: int = 20,
        flow_rate_per_nozzle: float = 5.0,  # L/h per nozzle
        droplet_size: float = 10.0,  # microns (typical 5-50)
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize fogger.

        Args:
            name: Unique identifier.
            nozzle_count: Number of fog nozzles.
            flow_rate_per_nozzle: Water flow per nozzle in L/h.
            droplet_size: Average droplet size in microns.
            output_limits: Min/max output fraction.
            enabled: Whether actuator is active.
        """
        super().__init__(name, output_limits=output_limits, enabled=enabled)
        self._nozzle_count = nozzle_count
        self._flow_rate_per_nozzle = flow_rate_per_nozzle
        self._droplet_size = droplet_size

    @property
    def total_flow_rate(self) -> float:
        """Total water flow rate in L/h at full output."""
        return self._nozzle_count * self._flow_rate_per_nozzle

    @property
    def current_flow_rate(self) -> float:
        """Current water flow rate in L/h."""
        return self.total_flow_rate * self.output

    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the effect of the fogger.

        Fogging adds moisture and provides evaporative cooling.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary with humidification and cooling effects.
        """
        if self.output <= 0:
            return {
                "water_flow": 0.0,
                "evaporative_cooling": 0.0,
                "humidity_addition": 0.0,
            }

        flow_rate_kg_s = self.current_flow_rate / 3600.0  # L/h to kg/s

        # Calculate evaporative cooling (latent heat of vaporization)
        # h_fg ≈ 2.45 MJ/kg at typical greenhouse temperatures
        evaporative_cooling = flow_rate_kg_s * 2.45e6  # W

        # Calculate humidity addition
        # Assuming all water evaporates (simplified)
        volume = state.geometry.volume
        rho_air = 1.2  # kg/m³ approximate
        air_mass = volume * rho_air

        # Humidity ratio increase per second
        # dW = water_mass / air_mass
        humidity_addition_rate = flow_rate_kg_s / air_mass  # kg_w/kg_da per second

        return {
            "water_flow": self.current_flow_rate,  # L/h
            "evaporative_cooling": evaporative_cooling,  # W
            "humidity_addition_rate": humidity_addition_rate,  # kg/kg per second
        }

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply fogging effect to state."""
        pass
