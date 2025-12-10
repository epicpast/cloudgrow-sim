"""Tests for actuator components."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cloudgrow_sim.components.actuators import (
    CirculationFan,
    EvaporativePad,
    ExhaustFan,
    Fogger,
    IntakeFan,
    RadiantHeater,
    RoofVent,
    ShadeCurtain,
    SideVent,
    ThermalCurtain,
    UnitHeater,
)
from cloudgrow_sim.core.state import (
    COVERING_MATERIALS,
    AirState,
    GeometryType,
    GreenhouseGeometry,
    GreenhouseState,
    Location,
)


@pytest.fixture
def sample_state() -> GreenhouseState:
    """Create a sample greenhouse state for testing."""
    return GreenhouseState(
        interior=AirState(temperature=30.0, humidity=70.0, co2_ppm=500.0),
        exterior=AirState(temperature=20.0, humidity=50.0, co2_ppm=400.0),
        time=datetime(2025, 6, 21, 14, 0, tzinfo=UTC),
        location=Location(latitude=37.3, longitude=-78.4),
        geometry=GreenhouseGeometry(
            geometry_type=GeometryType.GABLE,
            length=30.0,
            width=10.0,
            height_eave=3.0,
            height_ridge=5.0,
        ),
        covering=COVERING_MATERIALS["double_polyethylene"],
        solar_radiation=900.0,
        wind_speed=2.0,
        wind_direction=180.0,
    )


class TestExhaustFan:
    """Tests for ExhaustFan."""

    def test_initial_output(self) -> None:
        """Initial output is at minimum."""
        fan = ExhaustFan("fan1", max_flow_rate=5.0)
        assert fan.output == 0.0

    def test_set_output(self) -> None:
        """Set output to valid value."""
        fan = ExhaustFan("fan1")
        fan.set_output(0.75)
        assert fan.output == 0.75

    def test_output_clamped(self) -> None:
        """Output is clamped to limits."""
        fan = ExhaustFan("fan1")
        fan.set_output(1.5)
        assert fan.output == 1.0

        fan.set_output(-0.5)
        assert fan.output == 0.0

    def test_flow_rate(self) -> None:
        """Current flow rate based on output."""
        fan = ExhaustFan("fan1", max_flow_rate=10.0)
        fan.set_output(0.5)
        assert abs(fan.current_flow_rate - 5.0) < 0.01

    def test_power_cubic(self) -> None:
        """Power follows cubic relationship."""
        fan = ExhaustFan("fan1", power_consumption=1000.0)
        fan.set_output(0.5)
        # Power = 1000 * 0.5³ = 125 W
        assert abs(fan.current_power - 125.0) < 0.1

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Get effect returns ventilation rate."""
        fan = ExhaustFan("fan1", max_flow_rate=5.0)
        fan.set_output(1.0)
        effect = fan.get_effect(sample_state)

        assert "ventilation_rate" in effect
        assert effect["ventilation_rate"] > 0


class TestIntakeFan:
    """Tests for IntakeFan."""

    def test_flow_rate(self) -> None:
        """Intake fan provides flow."""
        fan = IntakeFan("intake", max_flow_rate=5.0)
        fan.set_output(1.0)
        assert fan.current_flow_rate == 5.0

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Get effect returns ventilation and heat."""
        fan = IntakeFan("intake", max_flow_rate=5.0)
        fan.set_output(1.0)
        effect = fan.get_effect(sample_state)

        assert "ventilation_rate" in effect
        assert "heat_addition" in effect


class TestCirculationFan:
    """Tests for CirculationFan."""

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Circulation fan provides velocity increase."""
        fan = CirculationFan("circ", power_consumption=100.0)
        fan.set_output(1.0)
        effect = fan.get_effect(sample_state)

        assert "air_velocity_increase" in effect
        assert effect["air_velocity_increase"] > 0
        assert "power" in effect


class TestRoofVent:
    """Tests for RoofVent."""

    def test_opening_area(self) -> None:
        """Opening area calculation."""
        vent = RoofVent("vent", width=2.0, height=0.5)
        vent.set_output(0.5)
        assert abs(vent.opening_area - 0.5) < 0.01

    def test_closed_no_flow(self, sample_state: GreenhouseState) -> None:
        """Closed vent gives zero flow."""
        vent = RoofVent("vent")
        vent.set_output(0.0)
        effect = vent.get_effect(sample_state)

        assert effect["ventilation_rate"] == 0.0

    def test_open_provides_flow(self, sample_state: GreenhouseState) -> None:
        """Open vent provides natural ventilation."""
        vent = RoofVent("vent", width=2.0, height=0.5, height_above_floor=4.0)
        vent.set_output(1.0)
        effect = vent.get_effect(sample_state)

        assert effect["ventilation_rate"] > 0


class TestSideVent:
    """Tests for SideVent."""

    def test_opening_area(self) -> None:
        """Opening area calculation."""
        vent = SideVent("vent", width=3.0, height=1.0)
        vent.set_output(1.0)
        assert abs(vent.opening_area - 3.0) < 0.01

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Side vent provides flow."""
        vent = SideVent("vent", width=2.0, height=1.0)
        vent.set_output(1.0)
        effect = vent.get_effect(sample_state)

        assert "ventilation_rate" in effect


class TestShadeCurtain:
    """Tests for ShadeCurtain."""

    def test_current_shading(self) -> None:
        """Current shading based on deployment."""
        curtain = ShadeCurtain("shade", shade_factor=0.6)
        curtain.set_output(0.5)
        assert abs(curtain.current_shading - 0.3) < 0.01

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Get effect returns solar reduction."""
        curtain = ShadeCurtain("shade", shade_factor=0.5)
        curtain.set_output(1.0)
        effect = curtain.get_effect(sample_state)

        assert "solar_reduction" in effect
        # 900 * 0.5 = 450 W/m² reduction
        assert abs(effect["solar_reduction"] - 450.0) < 1.0


class TestThermalCurtain:
    """Tests for ThermalCurtain."""

    def test_r_value(self) -> None:
        """Current R-value based on deployment."""
        curtain = ThermalCurtain("thermal", thermal_resistance=1.0)
        curtain.set_output(0.5)
        assert abs(curtain.current_r_value - 0.5) < 0.01

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Get effect returns U-value reduction."""
        curtain = ThermalCurtain("thermal", thermal_resistance=0.5)
        curtain.set_output(1.0)
        effect = curtain.get_effect(sample_state)

        assert "effective_u_value" in effect
        assert "added_r_value" in effect
        # Added R-value should be 0.5
        assert abs(effect["added_r_value"] - 0.5) < 0.01


class TestUnitHeater:
    """Tests for UnitHeater."""

    def test_heat_output(self) -> None:
        """Heat output calculation."""
        heater = UnitHeater("heater", heating_capacity=10000.0, efficiency=0.9)
        heater.set_output(1.0)
        # 10000 * 1.0 * 0.9 = 9000 W
        assert abs(heater.current_output_watts - 9000.0) < 1.0

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Get effect returns heat and fuel."""
        heater = UnitHeater("heater", heating_capacity=10000.0)
        heater.set_output(1.0)
        effect = heater.get_effect(sample_state)

        assert "heat_output" in effect
        assert "fuel_consumption" in effect
        assert effect["heat_output"] > 0


class TestRadiantHeater:
    """Tests for RadiantHeater."""

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Get effect returns radiant and convective split."""
        heater = RadiantHeater(
            "radiant",
            heating_capacity=5000.0,
            radiant_fraction=0.7,
        )
        heater.set_output(1.0)
        effect = heater.get_effect(sample_state)

        assert "radiant_heat" in effect
        assert "convective_heat" in effect
        # 70% radiant
        assert abs(effect["radiant_heat"] / effect["heat_output"] - 0.7) < 0.01


class TestEvaporativePad:
    """Tests for EvaporativePad."""

    def test_efficiency(self) -> None:
        """Current efficiency based on water flow."""
        pad = EvaporativePad("pad", saturation_efficiency=0.85)
        pad.set_output(0.5)
        assert abs(pad.current_efficiency - 0.425) < 0.01

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Get effect returns cooling parameters."""
        pad = EvaporativePad("pad", pad_area=10.0, saturation_efficiency=0.85)
        pad.set_output(1.0)
        effect = pad.get_effect(sample_state)

        assert "supply_temperature" in effect
        assert "temperature_drop" in effect
        assert "wet_bulb_temperature" in effect
        # Supply temp should be less than exterior dry-bulb
        assert effect["supply_temperature"] < 20.0

    def test_closed_no_effect(self, sample_state: GreenhouseState) -> None:
        """Closed pad provides no cooling."""
        pad = EvaporativePad("pad")
        pad.set_output(0.0)
        effect = pad.get_effect(sample_state)

        assert effect["temperature_drop"] == 0.0


class TestFogger:
    """Tests for Fogger."""

    def test_flow_rate(self) -> None:
        """Total flow rate calculation."""
        fogger = Fogger("fogger", nozzle_count=20, flow_rate_per_nozzle=5.0)
        assert fogger.total_flow_rate == 100.0  # L/h

    def test_current_flow(self) -> None:
        """Current flow based on output."""
        fogger = Fogger("fogger", nozzle_count=20, flow_rate_per_nozzle=5.0)
        fogger.set_output(0.5)
        assert fogger.current_flow_rate == 50.0

    def test_get_effect(self, sample_state: GreenhouseState) -> None:
        """Get effect returns cooling and humidity."""
        fogger = Fogger("fogger", nozzle_count=20, flow_rate_per_nozzle=5.0)
        fogger.set_output(1.0)
        effect = fogger.get_effect(sample_state)

        assert "water_flow" in effect
        assert "evaporative_cooling" in effect
        assert "humidity_addition_rate" in effect
        assert effect["evaporative_cooling"] > 0


class TestActuatorReset:
    """Tests for actuator reset behavior."""

    def test_reset_to_minimum(self) -> None:
        """Reset returns output to minimum."""
        fan = ExhaustFan("fan")
        fan.set_output(0.75)
        fan.reset()
        assert fan.output == 0.0
