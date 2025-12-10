"""Tests for configuration models."""

from __future__ import annotations

import pytest

from cloudgrow_sim.core.config import (
    CoveringConfig,
    GeometryConfig,
    LocationConfig,
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
