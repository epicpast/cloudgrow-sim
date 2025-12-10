"""Tests for climate modifier components."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cloudgrow_sim.components.modifiers.covering import CoveringMaterial
from cloudgrow_sim.components.modifiers.thermal_mass import ThermalMass
from cloudgrow_sim.core.state import (
    COVERING_MATERIALS,
    AirState,
    CoveringProperties,
    GeometryType,
    GreenhouseGeometry,
    GreenhouseState,
    Location,
)


@pytest.fixture
def sample_state() -> GreenhouseState:
    """Create a sample greenhouse state for testing."""
    return GreenhouseState(
        interior=AirState(temperature=25.0, humidity=60.0),
        exterior=AirState(temperature=15.0, humidity=50.0),
        time=datetime(2025, 6, 21, 12, 0, tzinfo=UTC),
        location=Location(latitude=37.3, longitude=-78.4),
        geometry=GreenhouseGeometry(
            geometry_type=GeometryType.GABLE,
            length=30.0,
            width=10.0,
            height_eave=3.0,
            height_ridge=5.0,
        ),
        covering=COVERING_MATERIALS["double_polyethylene"],
        solar_radiation=800.0,
        wind_speed=2.0,
        wind_direction=180.0,
    )


class TestCoveringMaterial:
    """Tests for CoveringMaterial modifier."""

    def test_default_material(self) -> None:
        """Default material is double polyethylene."""
        cover = CoveringMaterial("cover")
        assert cover.properties.material_name == "double_polyethylene"

    def test_predefined_material(self) -> None:
        """Use predefined material by name."""
        cover = CoveringMaterial("cover", material="single_glass")
        assert cover.properties.material_name == "single_glass"

    def test_polycarbonate_material(self) -> None:
        """Use polycarbonate material."""
        cover = CoveringMaterial("cover", material="polycarbonate_twin")
        assert cover.properties.material_name == "polycarbonate_twin"

    def test_custom_properties(self) -> None:
        """Use custom CoveringProperties."""
        custom = CoveringProperties(
            material_name="custom_film",
            transmittance_solar=0.85,
            transmittance_par=0.87,
            transmittance_thermal=0.10,
            u_value=5.0,
            reflectance_solar=0.10,
        )
        cover = CoveringMaterial("cover", properties=custom)
        assert cover.properties.material_name == "custom_film"
        assert cover.transmittance_solar == 0.85

    def test_unknown_material_error(self) -> None:
        """Error on unknown material name."""
        with pytest.raises(ValueError, match="Unknown material"):
            CoveringMaterial("cover", material="unknown_material")

    def test_property_accessors(self) -> None:
        """Test property accessors."""
        cover = CoveringMaterial("cover", material="single_glass")
        assert cover.transmittance_solar > 0.8
        assert cover.transmittance_par > 0.8
        assert cover.u_value > 4.0

    def test_get_properties(self) -> None:
        """Get properties dictionary."""
        cover = CoveringMaterial("cover", material="double_polyethylene")
        props = cover.get_properties()
        assert "material_name" in props
        assert "transmittance_solar" in props
        assert "u_value" in props
        assert "absorptance_solar" in props

    def test_update_passive(self, sample_state: GreenhouseState) -> None:
        """Update does nothing (passive modifier)."""
        cover = CoveringMaterial("cover")
        # Should not raise
        cover.update(1.0, sample_state)

    def test_disabled_modifier(self) -> None:
        """Disabled modifier can still be queried."""
        cover = CoveringMaterial("cover", enabled=False)
        assert cover.enabled is False
        # Properties still accessible
        assert cover.transmittance_solar > 0


class TestThermalMass:
    """Tests for ThermalMass modifier."""

    def test_default_values(self) -> None:
        """Default is 1000kg water at 20°C."""
        mass = ThermalMass("water_tank")
        assert mass.mass == 1000.0
        assert mass.specific_heat == 4186.0
        assert mass.temperature == 20.0
        assert mass.surface_area == 10.0

    def test_custom_values(self) -> None:
        """Custom thermal mass parameters."""
        mass = ThermalMass(
            "concrete",
            mass=500.0,
            specific_heat=880.0,
            surface_area=5.0,
            initial_temperature=15.0,
        )
        assert mass.mass == 500.0
        assert mass.specific_heat == 880.0
        assert mass.temperature == 15.0
        assert mass.surface_area == 5.0

    def test_thermal_capacity(self) -> None:
        """Thermal capacity is mass * specific heat."""
        mass = ThermalMass("tank", mass=100.0, specific_heat=4000.0)
        assert mass.thermal_capacity == 400000.0  # J/K

    def test_heat_exchange_positive(self) -> None:
        """Heat flows from mass to air when mass is warmer."""
        mass = ThermalMass("tank", initial_temperature=30.0)
        q = mass.calculate_heat_exchange(20.0)  # Air is cooler
        assert q > 0  # Heat to air

    def test_heat_exchange_negative(self) -> None:
        """Heat flows to mass when air is warmer."""
        mass = ThermalMass("tank", initial_temperature=15.0)
        q = mass.calculate_heat_exchange(25.0)  # Air is warmer
        assert q < 0  # Heat from air

    def test_heat_exchange_zero(self) -> None:
        """No heat flow when temperatures equal."""
        mass = ThermalMass("tank", initial_temperature=20.0)
        q = mass.calculate_heat_exchange(20.0)
        assert q == 0.0

    def test_update_cooling(self, sample_state: GreenhouseState) -> None:
        """Mass cools when warmer than air."""
        mass = ThermalMass("tank", initial_temperature=35.0)
        initial = mass.temperature

        mass.update(60.0, sample_state)  # 1 minute

        # Should have cooled
        assert mass.temperature < initial

    def test_update_heating(self, sample_state: GreenhouseState) -> None:
        """Mass heats when cooler than air."""
        mass = ThermalMass("tank", initial_temperature=15.0)
        initial = mass.temperature

        mass.update(60.0, sample_state)  # 1 minute

        # Should have warmed (interior is 25°C)
        assert mass.temperature > initial

    def test_update_disabled(self, sample_state: GreenhouseState) -> None:
        """Disabled modifier doesn't update."""
        mass = ThermalMass("tank", initial_temperature=30.0, enabled=False)

        mass.update(3600.0, sample_state)  # 1 hour

        # Temperature unchanged
        assert mass.temperature == 30.0

    def test_get_properties(self) -> None:
        """Get properties dictionary."""
        mass = ThermalMass("tank", mass=500.0, specific_heat=4000.0)
        props = mass.get_properties()
        assert props["mass"] == 500.0
        assert props["specific_heat"] == 4000.0
        assert props["thermal_capacity"] == 2000000.0
        assert "temperature" in props

    def test_reset(self) -> None:
        """Reset method exists (placeholder)."""
        mass = ThermalMass("tank")
        mass.reset()  # Should not raise
