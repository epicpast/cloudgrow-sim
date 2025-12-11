"""Tests for configuration models."""

from __future__ import annotations

import pytest

from cloudgrow_sim.core.config import (
    ActuatorConfig,
    ComponentsConfig,
    ControllerConfig,
    CoveringConfig,
    GeometryConfig,
    LocationConfig,
    ModifierConfig,
    SensorConfig,
)
from cloudgrow_sim.core.state import GeometryType


class TestLocationConfig:
    """Tests for LocationConfig."""

    def test_basic_creation(self) -> None:
        """Create basic location config."""
        config = LocationConfig(latitude=37.0, longitude=-78.0)
        assert config.latitude == 37.0
        assert config.longitude == -78.0
        assert config.elevation == 0.0  # default
        assert config.timezone == "UTC"  # default

    def test_full_creation(self) -> None:
        """Create location config with all fields."""
        config = LocationConfig(
            latitude=37.3,
            longitude=-78.4,
            elevation=200.0,
            timezone="America/New_York",
        )
        assert config.latitude == 37.3
        assert config.longitude == -78.4
        assert config.elevation == 200.0
        assert config.timezone == "America/New_York"

    def test_to_location(self) -> None:
        """Convert to Location state object."""
        config = LocationConfig(
            latitude=37.3,
            longitude=-78.4,
            elevation=150.0,
            timezone="America/New_York",
        )
        loc = config.to_location()
        assert loc.latitude == 37.3
        assert loc.longitude == -78.4
        assert loc.elevation == 150.0
        assert loc.timezone_str == "America/New_York"

    def test_invalid_latitude(self) -> None:
        """Error on invalid latitude."""
        with pytest.raises(ValueError):
            LocationConfig(latitude=100.0, longitude=0.0)

    def test_invalid_longitude(self) -> None:
        """Error on invalid longitude."""
        with pytest.raises(ValueError):
            LocationConfig(latitude=0.0, longitude=200.0)


class TestGeometryConfig:
    """Tests for GeometryConfig."""

    def test_basic_creation(self) -> None:
        """Create basic geometry config."""
        config = GeometryConfig(
            length=30.0,
            width=10.0,
            height_ridge=5.0,
            height_eave=3.0,
        )
        assert config.length == 30.0
        assert config.width == 10.0
        assert config.height_ridge == 5.0
        assert config.height_eave == 3.0
        assert config.type == GeometryType.GABLE  # default

    def test_quonset_type(self) -> None:
        """Create quonset geometry."""
        config = GeometryConfig(
            type=GeometryType.QUONSET,
            length=20.0,
            width=8.0,
            height_ridge=4.0,
            height_eave=2.0,
        )
        assert config.type == GeometryType.QUONSET

    def test_to_geometry(self) -> None:
        """Convert to GreenhouseGeometry state object."""
        config = GeometryConfig(
            type=GeometryType.GABLE,
            length=30.0,
            width=10.0,
            height_ridge=5.0,
            height_eave=3.0,
            orientation=45.0,
        )
        geom = config.to_geometry()
        assert geom.geometry_type == GeometryType.GABLE
        assert geom.length == 30.0
        assert geom.width == 10.0
        assert geom.height_ridge == 5.0
        assert geom.height_eave == 3.0
        assert geom.orientation == 45.0

    def test_eave_exceeds_ridge_error(self) -> None:
        """Error when eave exceeds ridge height."""
        with pytest.raises(ValueError, match="cannot exceed"):
            GeometryConfig(
                length=30.0,
                width=10.0,
                height_ridge=3.0,
                height_eave=5.0,  # Higher than ridge
            )

    def test_zero_dimensions_error(self) -> None:
        """Error on zero dimensions."""
        with pytest.raises(ValueError):
            GeometryConfig(
                length=0.0,  # Invalid
                width=10.0,
                height_ridge=5.0,
                height_eave=3.0,
            )


class TestCoveringConfig:
    """Tests for CoveringConfig."""

    def test_predefined_material(self) -> None:
        """Use predefined material."""
        config = CoveringConfig(material="double_polyethylene")
        assert config.material == "double_polyethylene"
        props = config.to_covering()
        assert props.material_name == "double_polyethylene"

    def test_single_glass_material(self) -> None:
        """Use single glass material."""
        config = CoveringConfig(material="single_glass")
        props = config.to_covering()
        assert props.material_name == "single_glass"

    def test_custom_material(self) -> None:
        """Use custom material properties."""
        config = CoveringConfig(
            material=None,  # Custom
            transmittance_solar=0.90,
            transmittance_par=0.92,
            transmittance_thermal=0.05,
            u_value=6.0,
            reflectance_solar=0.05,
        )
        props = config.to_covering()
        assert props.transmittance_solar == 0.90
        assert props.u_value == 6.0
        assert props.material_name == "custom"

    def test_default_values(self) -> None:
        """Check default covering config values."""
        config = CoveringConfig()
        assert config.material == "double_polyethylene"
        assert config.transmittance_solar == 0.77
        assert config.u_value == 4.0


class TestModifierConfig:
    """Tests for ModifierConfig."""

    def test_modifier_config_valid(self) -> None:
        """Create valid modifier config."""
        config = ModifierConfig(type="covering", name="main_covering")
        assert config.type == "covering"
        assert config.name == "main_covering"
        assert config.enabled is True  # default

    def test_modifier_config_extra_fields_allowed(self) -> None:
        """Extra fields pass through for component-specific params."""
        config = ModifierConfig(
            type="thermal_mass",
            name="water_barrels",
            mass=2000.0,
            specific_heat=4186.0,
            surface_area=10.0,
            initial_temperature=20.0,
        )
        assert config.type == "thermal_mass"
        assert config.name == "water_barrels"
        # Extra fields accessible via model_dump
        data = config.model_dump()
        assert data["mass"] == 2000.0
        assert data["specific_heat"] == 4186.0
        assert data["surface_area"] == 10.0
        assert data["initial_temperature"] == 20.0

    def test_modifier_config_type_required(self) -> None:
        """Error when type is missing."""
        with pytest.raises(ValueError):
            ModifierConfig(name="no_type")  # type: ignore[call-arg]

    def test_modifier_config_name_required(self) -> None:
        """Error when name is missing."""
        with pytest.raises(ValueError):
            ModifierConfig(type="covering")  # type: ignore[call-arg]

    def test_modifier_config_disabled(self) -> None:
        """Create disabled modifier."""
        config = ModifierConfig(type="covering", name="disabled_cover", enabled=False)
        assert config.enabled is False


class TestComponentsConfigWithModifiers:
    """Tests for ComponentsConfig including modifiers."""

    def test_components_config_includes_modifiers(self) -> None:
        """ComponentsConfig includes modifiers list."""
        config = ComponentsConfig(
            sensors=[SensorConfig(type="temperature", name="temp_1")],
            actuators=[
                ActuatorConfig(
                    type="exhaust_fan",
                    name="fan_1",
                    max_flow_rate=1.0,
                    power_consumption=500.0,
                )
            ],
            controllers=[
                ControllerConfig(
                    type="hysteresis",
                    name="ctrl_1",
                    process_variable="temp_1.temperature",
                    setpoint=25.0,
                )
            ],
            modifiers=[
                ModifierConfig(type="covering", name="cover_1", material="single_glass")
            ],
        )
        assert len(config.sensors) == 1
        assert len(config.actuators) == 1
        assert len(config.controllers) == 1
        assert len(config.modifiers) == 1
        assert config.modifiers[0].type == "covering"

    def test_components_config_empty_modifiers_default(self) -> None:
        """ComponentsConfig defaults to empty modifiers list."""
        config = ComponentsConfig()
        assert config.modifiers == []

    def test_components_config_multiple_modifiers(self) -> None:
        """ComponentsConfig can have multiple modifiers."""
        config = ComponentsConfig(
            modifiers=[
                ModifierConfig(type="covering", name="cover_1"),
                ModifierConfig(
                    type="thermal_mass",
                    name="mass_1",
                    mass=1000.0,
                    specific_heat=4186.0,
                    surface_area=5.0,
                    initial_temperature=20.0,
                ),
            ]
        )
        assert len(config.modifiers) == 2
        assert config.modifiers[0].type == "covering"
        assert config.modifiers[1].type == "thermal_mass"
