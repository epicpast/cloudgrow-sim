"""Shared pytest fixtures for cloudgrow_sim tests."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from cloudgrow_sim.core.events import reset_event_bus
from cloudgrow_sim.core.registry import reset_registry
from cloudgrow_sim.core.state import (
    AirState,
    CoveringProperties,
    GreenhouseGeometry,
    GreenhouseState,
    Location,
)

# =============================================================================
# Autouse fixtures for test isolation
# =============================================================================


@pytest.fixture(autouse=True)
def reset_global_state() -> None:
    """Reset global singletons before each test for isolation.

    This fixture runs automatically before each test to ensure:
    - Event bus is cleared of handlers and history
    - Component registry is cleared of registrations and instances
    """
    reset_event_bus()
    reset_registry()


# =============================================================================
# Random number generator fixtures
# =============================================================================


@pytest.fixture
def rng() -> np.random.Generator:
    """Provide a seeded random generator for reproducible tests."""
    return np.random.default_rng(42)


@pytest.fixture
def deterministic_seed() -> int:
    """Provide a fixed seed for reproducible simulations."""
    return 42


# =============================================================================
# AirState fixtures
# =============================================================================


@pytest.fixture
def default_air_state() -> AirState:
    """Standard indoor air conditions."""
    return AirState(
        temperature=20.0,
        humidity=50.0,
        pressure=101325.0,
        co2_ppm=400.0,
    )


@pytest.fixture
def warm_humid_air_state() -> AirState:
    """Warm, humid greenhouse conditions."""
    return AirState(
        temperature=28.0,
        humidity=75.0,
        pressure=101325.0,
        co2_ppm=800.0,
    )


@pytest.fixture
def cold_dry_air_state() -> AirState:
    """Cold, dry winter conditions."""
    return AirState(
        temperature=5.0,
        humidity=30.0,
        pressure=101325.0,
        co2_ppm=420.0,
    )


@pytest.fixture
def exterior_summer_air_state() -> AirState:
    """Typical summer exterior conditions."""
    return AirState(
        temperature=30.0,
        humidity=60.0,
        pressure=101325.0,
        co2_ppm=420.0,
    )


@pytest.fixture
def exterior_winter_air_state() -> AirState:
    """Typical winter exterior conditions."""
    return AirState(
        temperature=-5.0,
        humidity=70.0,
        pressure=101325.0,
        co2_ppm=420.0,
    )


# =============================================================================
# Location fixtures
# =============================================================================


@pytest.fixture
def default_location() -> Location:
    """Default test location (mid-Atlantic US)."""
    return Location(
        latitude=37.3,
        longitude=-78.4,
        elevation=200.0,
        timezone_str="America/New_York",
    )


@pytest.fixture
def tropical_location() -> Location:
    """Tropical location near equator."""
    return Location(
        latitude=10.0,
        longitude=-84.0,
        elevation=50.0,
        timezone_str="America/Costa_Rica",
    )


@pytest.fixture
def nordic_location() -> Location:
    """Nordic location with extreme day lengths."""
    return Location(
        latitude=60.0,
        longitude=25.0,
        elevation=10.0,
        timezone_str="Europe/Helsinki",
    )


# =============================================================================
# Geometry fixtures
# =============================================================================


@pytest.fixture
def default_geometry() -> GreenhouseGeometry:
    """Standard gable greenhouse geometry."""
    return GreenhouseGeometry(
        length=30.0,
        width=10.0,
        height_ridge=5.0,
        height_eave=3.0,
        orientation=0.0,
    )


@pytest.fixture
def small_geometry() -> GreenhouseGeometry:
    """Small hobby greenhouse."""
    return GreenhouseGeometry(
        length=6.0,
        width=4.0,
        height_ridge=3.0,
        height_eave=2.0,
        orientation=0.0,
    )


@pytest.fixture
def large_geometry() -> GreenhouseGeometry:
    """Large commercial greenhouse."""
    return GreenhouseGeometry(
        length=100.0,
        width=30.0,
        height_ridge=8.0,
        height_eave=5.0,
        orientation=0.0,
    )


# =============================================================================
# Covering fixtures
# =============================================================================


@pytest.fixture
def default_covering() -> CoveringProperties:
    """Double polyethylene covering (default)."""
    return CoveringProperties(
        material_name="double_polyethylene",
        transmittance_solar=0.77,
        transmittance_par=0.75,
        transmittance_thermal=0.05,
        u_value=4.0,
        reflectance_solar=0.13,
    )


@pytest.fixture
def glass_covering() -> CoveringProperties:
    """Single glass covering."""
    return CoveringProperties(
        material_name="single_glass",
        transmittance_solar=0.85,
        transmittance_par=0.83,
        transmittance_thermal=0.02,
        u_value=5.8,
        reflectance_solar=0.08,
    )


@pytest.fixture
def polycarbonate_covering() -> CoveringProperties:
    """Twin-wall polycarbonate covering."""
    return CoveringProperties(
        material_name="polycarbonate_twin",
        transmittance_solar=0.80,
        transmittance_par=0.78,
        transmittance_thermal=0.03,
        u_value=3.5,
        reflectance_solar=0.10,
    )


# =============================================================================
# GreenhouseState fixtures
# =============================================================================


@pytest.fixture
def default_greenhouse_state(
    default_air_state: AirState,
    default_location: Location,
    default_geometry: GreenhouseGeometry,
    default_covering: CoveringProperties,
) -> GreenhouseState:
    """Standard greenhouse state with typical conditions."""
    return GreenhouseState(
        time=datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC),
        interior=default_air_state,
        exterior=AirState(
            temperature=25.0,
            humidity=55.0,
            pressure=101325.0,
            co2_ppm=420.0,
        ),
        solar_radiation=800.0,
        wind_speed=2.0,
        wind_direction=180.0,
        location=default_location,
        geometry=default_geometry,
        covering=default_covering,
    )


@pytest.fixture
def summer_greenhouse_state(
    warm_humid_air_state: AirState,
    exterior_summer_air_state: AirState,
    default_location: Location,
    default_geometry: GreenhouseGeometry,
    default_covering: CoveringProperties,
) -> GreenhouseState:
    """Summer greenhouse with high solar and warm temperatures."""
    return GreenhouseState(
        time=datetime(2024, 7, 15, 14, 0, 0, tzinfo=UTC),
        interior=warm_humid_air_state,
        exterior=exterior_summer_air_state,
        solar_radiation=950.0,
        wind_speed=3.0,
        wind_direction=220.0,
        location=default_location,
        geometry=default_geometry,
        covering=default_covering,
    )


@pytest.fixture
def winter_greenhouse_state(
    default_air_state: AirState,
    exterior_winter_air_state: AirState,
    default_location: Location,
    default_geometry: GreenhouseGeometry,
    default_covering: CoveringProperties,
) -> GreenhouseState:
    """Winter greenhouse with heating needs."""
    return GreenhouseState(
        time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        interior=default_air_state,
        exterior=exterior_winter_air_state,
        solar_radiation=200.0,
        wind_speed=5.0,
        wind_direction=315.0,
        location=default_location,
        geometry=default_geometry,
        covering=default_covering,
    )


@pytest.fixture
def night_greenhouse_state(
    cold_dry_air_state: AirState,
    default_location: Location,
    default_geometry: GreenhouseGeometry,
    default_covering: CoveringProperties,
) -> GreenhouseState:
    """Nighttime greenhouse with no solar radiation."""
    return GreenhouseState(
        time=datetime(2024, 6, 21, 2, 0, 0, tzinfo=UTC),
        interior=cold_dry_air_state,
        exterior=AirState(
            temperature=15.0,
            humidity=80.0,
            pressure=101325.0,
            co2_ppm=420.0,
        ),
        solar_radiation=0.0,
        wind_speed=1.0,
        wind_direction=90.0,
        location=default_location,
        geometry=default_geometry,
        covering=default_covering,
    )


# =============================================================================
# Time fixtures
# =============================================================================


@pytest.fixture
def summer_solstice_noon() -> datetime:
    """Summer solstice at solar noon."""
    return datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def winter_solstice_noon() -> datetime:
    """Winter solstice at solar noon."""
    return datetime(2024, 12, 21, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def equinox_noon() -> datetime:
    """Spring equinox at solar noon."""
    return datetime(2024, 3, 20, 12, 0, 0, tzinfo=UTC)


# =============================================================================
# Utility fixtures
# =============================================================================


@pytest.fixture
def sample_fixture() -> str:
    """Example fixture - replace with project-specific fixtures."""
    return "sample_value"
