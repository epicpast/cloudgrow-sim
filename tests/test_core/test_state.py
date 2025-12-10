"""Tests for state management classes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cloudgrow_sim.core.state import (
    COVERING_MATERIALS,
    AirState,
    CoveringProperties,
    GeometryType,
    GreenhouseGeometry,
    GreenhouseState,
    Location,
)


class TestAirState:
    """Tests for AirState dataclass."""

    def test_default_creation(self) -> None:
        """Create with default values."""
        state = AirState()
        assert state.temperature == 20.0
        assert state.humidity == 50.0
        assert state.pressure == 101325.0
        assert state.co2_ppm == 400.0

    def test_custom_creation(self) -> None:
        """Create with custom values."""
        state = AirState(
            temperature=25.0,
            humidity=70.0,
            pressure=100000.0,
            co2_ppm=800.0,
        )
        assert state.temperature == 25.0
        assert state.humidity == 70.0
        assert state.pressure == 100000.0
        assert state.co2_ppm == 800.0

    def test_invalid_humidity_low(self) -> None:
        """Error on negative humidity."""
        with pytest.raises(ValueError, match="Humidity"):
            AirState(humidity=-10.0)

    def test_invalid_humidity_high(self) -> None:
        """Error on humidity > 100."""
        with pytest.raises(ValueError, match="Humidity"):
            AirState(humidity=110.0)

    def test_invalid_pressure(self) -> None:
        """Error on negative pressure."""
        with pytest.raises(ValueError, match="Pressure"):
            AirState(pressure=-100.0)


class TestLocation:
    """Tests for Location dataclass."""

    def test_valid_location(self) -> None:
        """Create valid location."""
        loc = Location(
            latitude=37.3,
            longitude=-78.4,
            elevation=200.0,
            timezone_str="America/New_York",
        )
        assert loc.latitude == 37.3
        assert loc.longitude == -78.4
        assert loc.elevation == 200.0
        assert loc.timezone_str == "America/New_York"

    def test_invalid_latitude_low(self) -> None:
        """Error on latitude < -90."""
        with pytest.raises(ValueError, match="Latitude"):
            Location(latitude=-100.0, longitude=0.0)

    def test_invalid_latitude_high(self) -> None:
        """Error on latitude > 90."""
        with pytest.raises(ValueError, match="Latitude"):
            Location(latitude=100.0, longitude=0.0)

    def test_invalid_longitude_low(self) -> None:
        """Error on longitude < -180."""
        with pytest.raises(ValueError, match="Longitude"):
            Location(latitude=0.0, longitude=-200.0)

    def test_invalid_longitude_high(self) -> None:
        """Error on longitude > 180."""
        with pytest.raises(ValueError, match="Longitude"):
            Location(latitude=0.0, longitude=200.0)


class TestGreenhouseGeometry:
    """Tests for GreenhouseGeometry dataclass."""

    def test_gable_geometry(self) -> None:
        """Create gable greenhouse geometry."""
        geom = GreenhouseGeometry(
            geometry_type=GeometryType.GABLE,
            length=30.0,
            width=10.0,
            height_eave=3.0,
            height_ridge=5.0,
            orientation=0.0,
        )
        assert geom.geometry_type == GeometryType.GABLE
        assert geom.length == 30.0
        assert geom.width == 10.0
        assert geom.height_ridge == 5.0

    def test_floor_area(self) -> None:
        """Floor area calculation."""
        geom = GreenhouseGeometry(
            geometry_type=GeometryType.GABLE,
            length=30.0,
            width=10.0,
            height_eave=3.0,
            height_ridge=5.0,
        )
        assert geom.floor_area == 300.0

    def test_volume_gable(self) -> None:
        """Volume calculation for gable."""
        geom = GreenhouseGeometry(
            geometry_type=GeometryType.GABLE,
            length=30.0,
            width=10.0,
            height_eave=3.0,
            height_ridge=5.0,
        )
        # Volume = floor * eave + (ridge - eave) * floor * 0.5
        # = 300 * 3 + 2 * 300 * 0.5 = 900 + 300 = 1200
        assert abs(geom.volume - 1200.0) < 1.0

    def test_eave_exceeds_ridge(self) -> None:
        """Error when eave height exceeds ridge."""
        with pytest.raises(ValueError, match="Eave height"):
            GreenhouseGeometry(
                geometry_type=GeometryType.GABLE,
                length=30.0,
                width=10.0,
                height_eave=6.0,
                height_ridge=5.0,
            )

    def test_quonset_volume(self) -> None:
        """Volume calculation for quonset."""
        geom = GreenhouseGeometry(
            geometry_type=GeometryType.QUONSET,
            length=30.0,
            width=10.0,
            height_eave=2.0,
            height_ridge=5.0,
        )
        # Should be positive and reasonable
        assert geom.volume > 0
        assert geom.volume < 2000  # Less than rectangular box


class TestCoveringProperties:
    """Tests for CoveringProperties dataclass."""

    def test_creation(self) -> None:
        """Create covering properties."""
        props = CoveringProperties(
            material_name="glass",
            transmittance_solar=0.85,
            transmittance_par=0.88,
            transmittance_thermal=0.10,
            u_value=5.0,
            reflectance_solar=0.08,
        )
        assert props.material_name == "glass"
        assert props.transmittance_solar == 0.85
        assert props.u_value == 5.0

    def test_absorptance(self) -> None:
        """Absorptance is 1 - transmittance - reflectance."""
        props = CoveringProperties(
            material_name="test",
            transmittance_solar=0.80,
            transmittance_par=0.80,
            transmittance_thermal=0.05,
            u_value=5.0,
            reflectance_solar=0.10,
        )
        assert abs(props.absorptance_solar - 0.10) < 0.01


class TestCoveringMaterialsDict:
    """Tests for pre-defined covering materials."""

    def test_polyethylene_exists(self) -> None:
        """Double polyethylene is defined."""
        assert "double_polyethylene" in COVERING_MATERIALS

    def test_glass_exists(self) -> None:
        """Single glass is defined."""
        assert "single_glass" in COVERING_MATERIALS

    def test_polycarbonate_exists(self) -> None:
        """Twin-wall polycarbonate is defined."""
        assert "polycarbonate_twin" in COVERING_MATERIALS

    def test_properties_valid(self) -> None:
        """All materials have valid property ranges."""
        for name, props in COVERING_MATERIALS.items():
            assert 0 <= props.transmittance_solar <= 1, f"{name} solar trans"
            assert 0 <= props.transmittance_par <= 1, f"{name} PAR trans"
            assert props.u_value > 0, f"{name} U-value"


class TestGreenhouseState:
    """Tests for GreenhouseState dataclass."""

    def test_creation(self) -> None:
        """Create full greenhouse state."""
        state = GreenhouseState(
            interior=AirState(temperature=25.0),
            exterior=AirState(temperature=15.0),
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
            wind_speed=3.0,
            wind_direction=180.0,
        )

        assert state.interior.temperature == 25.0
        assert state.exterior.temperature == 15.0
        assert state.solar_radiation == 800.0
        assert state.location.latitude == 37.3

    def test_default_creation(self) -> None:
        """Create with minimal arguments."""
        state = GreenhouseState()
        assert state.interior is not None
        assert state.exterior is not None
        assert state.time is not None
