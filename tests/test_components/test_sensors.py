"""Tests for sensor components."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cloudgrow_sim.components.sensors import (
    CO2Sensor,
    CombinedTempHumiditySensor,
    HumiditySensor,
    PARSensor,
    SolarRadiationSensor,
    TemperatureSensor,
    WindSensor,
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
        interior=AirState(temperature=25.0, humidity=60.0, co2_ppm=500.0),
        exterior=AirState(temperature=18.0, humidity=45.0, co2_ppm=400.0),
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


class TestTemperatureSensor:
    """Tests for TemperatureSensor."""

    def test_read_interior(self, sample_state: GreenhouseState) -> None:
        """Read interior temperature."""
        sensor = TemperatureSensor("temp_int", location="interior")
        reading = sensor.read(sample_state)

        assert "temperature" in reading
        assert abs(reading["temperature"] - 25.0) < 0.01

    def test_read_exterior(self, sample_state: GreenhouseState) -> None:
        """Read exterior temperature."""
        sensor = TemperatureSensor("temp_ext", location="exterior")
        reading = sensor.read(sample_state)

        assert abs(reading["temperature"] - 18.0) < 0.01

    def test_noise(self, sample_state: GreenhouseState) -> None:
        """Noise is added when configured."""
        sensor = TemperatureSensor("temp", noise_std_dev=0.5)

        # Take multiple readings and check variance
        readings = [sensor.read(sample_state)["temperature"] for _ in range(100)]
        mean = sum(readings) / len(readings)
        variance = sum((r - mean) ** 2 for r in readings) / len(readings)

        # Should have noticeable variance
        assert variance > 0.1

    def test_no_noise(self, sample_state: GreenhouseState) -> None:
        """No noise when noise_std_dev is 0."""
        sensor = TemperatureSensor("temp", noise_std_dev=0.0)

        readings = [sensor.read(sample_state)["temperature"] for _ in range(10)]

        # All readings should be identical
        assert all(r == readings[0] for r in readings)


class TestHumiditySensor:
    """Tests for HumiditySensor."""

    def test_read_interior(self, sample_state: GreenhouseState) -> None:
        """Read interior humidity."""
        sensor = HumiditySensor("hum_int", location="interior")
        reading = sensor.read(sample_state)

        assert "humidity" in reading
        assert abs(reading["humidity"] - 60.0) < 0.01

    def test_clamps_to_range(self, sample_state: GreenhouseState) -> None:
        """Humidity is clamped to [0, 100]."""
        sensor = HumiditySensor("hum", noise_std_dev=20.0)

        # Sample state has 60% humidity, with noise could go outside range
        # but should always be clamped
        for _ in range(50):
            reading = sensor.read(sample_state)
            assert 0.0 <= reading["humidity"] <= 100.0


class TestCombinedTempHumiditySensor:
    """Tests for CombinedTempHumiditySensor."""

    def test_reads_both(self, sample_state: GreenhouseState) -> None:
        """Read both temperature and humidity."""
        sensor = CombinedTempHumiditySensor("dht", location="interior")
        reading = sensor.read(sample_state)

        assert "temperature" in reading
        assert "humidity" in reading
        assert abs(reading["temperature"] - 25.0) < 0.01
        assert abs(reading["humidity"] - 60.0) < 0.01

    def test_separate_noise(self, sample_state: GreenhouseState) -> None:
        """Separate noise parameters work."""
        sensor = CombinedTempHumiditySensor(
            "dht",
            temp_noise_std_dev=0.1,
            humidity_noise_std_dev=2.0,
        )

        # Humidity should vary more
        temp_readings = []
        hum_readings = []
        for _ in range(100):
            r = sensor.read(sample_state)
            temp_readings.append(r["temperature"])
            hum_readings.append(r["humidity"])

        temp_var = sum((t - 25.0) ** 2 for t in temp_readings) / len(temp_readings)
        hum_var = sum((h - 60.0) ** 2 for h in hum_readings) / len(hum_readings)

        assert hum_var > temp_var * 100  # Humidity variance much larger


class TestCO2Sensor:
    """Tests for CO2Sensor."""

    def test_read_interior(self, sample_state: GreenhouseState) -> None:
        """Read interior CO2."""
        sensor = CO2Sensor("co2_int", location="interior")
        reading = sensor.read(sample_state)

        assert "co2" in reading
        assert abs(reading["co2"] - 500.0) < 0.01

    def test_read_exterior(self, sample_state: GreenhouseState) -> None:
        """Read exterior CO2."""
        sensor = CO2Sensor("co2_ext", location="exterior")
        reading = sensor.read(sample_state)

        assert abs(reading["co2"] - 400.0) < 0.01


class TestSolarRadiationSensor:
    """Tests for SolarRadiationSensor."""

    def test_read(self, sample_state: GreenhouseState) -> None:
        """Read solar radiation."""
        sensor = SolarRadiationSensor("pyranometer")
        reading = sensor.read(sample_state)

        assert "solar_radiation" in reading
        assert abs(reading["solar_radiation"] - 800.0) < 0.01

    def test_clamps_negative(self, sample_state: GreenhouseState) -> None:
        """Negative readings are clamped to 0."""
        sensor = SolarRadiationSensor("pyranometer", noise_std_dev=100.0)

        # With enough noise, could go negative but should be clamped
        for _ in range(50):
            reading = sensor.read(sample_state)
            assert reading["solar_radiation"] >= 0.0


class TestPARSensor:
    """Tests for PARSensor."""

    def test_interior_applies_transmittance(
        self, sample_state: GreenhouseState
    ) -> None:
        """Interior PAR accounts for covering transmittance."""
        sensor = PARSensor("par_int", location="interior")
        reading = sensor.read(sample_state)

        # PAR should be less than exterior due to covering
        assert "par" in reading
        # Double poly PAR transmittance is about 0.82
        # 800 * 0.82 * 0.45 * 4.57 ≈ 1350 µmol/m²/s
        assert 1000 < reading["par"] < 1700

    def test_exterior_no_transmittance(self, sample_state: GreenhouseState) -> None:
        """Exterior PAR is full conversion."""
        sensor = PARSensor("par_ext", location="exterior")
        reading = sensor.read(sample_state)

        # 800 * 0.45 * 4.57 ≈ 1645 µmol/m²/s
        assert 1500 < reading["par"] < 1800


class TestWindSensor:
    """Tests for WindSensor."""

    def test_read(self, sample_state: GreenhouseState) -> None:
        """Read wind speed and direction."""
        sensor = WindSensor("anemometer")
        reading = sensor.read(sample_state)

        assert "wind_speed" in reading
        assert "wind_direction" in reading
        assert abs(reading["wind_speed"] - 3.0) < 0.01
        assert abs(reading["wind_direction"] - 180.0) < 0.01

    def test_direction_wraps(self, sample_state: GreenhouseState) -> None:
        """Direction wraps to [0, 360)."""
        sensor = WindSensor(
            "anemometer",
            noise_std_dev=0.0,
            direction_noise_std_dev=50.0,
        )

        for _ in range(100):
            reading = sensor.read(sample_state)
            assert 0.0 <= reading["wind_direction"] < 360.0

    def test_speed_non_negative(self, sample_state: GreenhouseState) -> None:
        """Speed is clamped to non-negative."""
        sensor = WindSensor("anemometer", noise_std_dev=5.0)

        for _ in range(100):
            reading = sensor.read(sample_state)
            assert reading["wind_speed"] >= 0.0


class TestSensorUpdate:
    """Tests for sensor update method."""

    def test_update_stores_reading(self, sample_state: GreenhouseState) -> None:
        """Update method stores last reading."""
        sensor = TemperatureSensor("temp")
        sensor.update(1.0, sample_state)

        assert sensor.last_reading == {"temperature": 25.0}

    def test_disabled_sensor_no_reading(self, sample_state: GreenhouseState) -> None:
        """Disabled sensor doesn't update."""
        sensor = TemperatureSensor("temp", enabled=False)
        sensor.update(1.0, sample_state)

        assert sensor.last_reading == {}


class TestSensorReproducibility:
    """Tests for sensor RNG reproducibility."""

    def test_seed_produces_reproducible_results(
        self, sample_state: GreenhouseState
    ) -> None:
        """Same seed produces identical noise sequences."""
        sensor1 = TemperatureSensor("temp1", noise_std_dev=0.5, seed=42)
        sensor2 = TemperatureSensor("temp2", noise_std_dev=0.5, seed=42)

        readings1 = [sensor1.read(sample_state)["temperature"] for _ in range(10)]
        readings2 = [sensor2.read(sample_state)["temperature"] for _ in range(10)]

        assert readings1 == readings2

    def test_different_seeds_produce_different_results(
        self, sample_state: GreenhouseState
    ) -> None:
        """Different seeds produce different noise sequences."""
        sensor1 = TemperatureSensor("temp1", noise_std_dev=0.5, seed=42)
        sensor2 = TemperatureSensor("temp2", noise_std_dev=0.5, seed=99)

        readings1 = [sensor1.read(sample_state)["temperature"] for _ in range(10)]
        readings2 = [sensor2.read(sample_state)["temperature"] for _ in range(10)]

        assert readings1 != readings2

    def test_shared_rng_across_sensors(self, sample_state: GreenhouseState) -> None:
        """Multiple sensors can share same RNG for coordinated randomness."""
        import numpy as np

        shared_rng = np.random.default_rng(42)

        sensor1 = TemperatureSensor("temp1", noise_std_dev=0.5, rng=shared_rng)
        sensor2 = HumiditySensor("hum1", noise_std_dev=1.0, rng=shared_rng)

        # Both should use same RNG
        assert sensor1.rng is shared_rng
        assert sensor2.rng is shared_rng

        # Both draw from same sequence
        _ = sensor1.read(sample_state)
        _ = sensor2.read(sample_state)

    def test_add_noise_with_zero_std_returns_exact_value(self) -> None:
        """_add_noise returns exact value when std_dev is 0."""
        sensor = TemperatureSensor("temp", noise_std_dev=0.0)
        assert sensor._add_noise(25.0) == 25.0
        assert sensor._add_noise(25.0, std_dev=0.0) == 25.0

    def test_add_noise_with_override_std_dev(self) -> None:
        """_add_noise uses override std_dev when provided."""
        sensor = TemperatureSensor("temp", noise_std_dev=0.0, seed=42)
        # With override, should add noise
        value_with_noise = sensor._add_noise(25.0, std_dev=1.0)
        assert value_with_noise != 25.0

    def test_rng_property_returns_generator(self) -> None:
        """rng property returns the random generator."""
        import numpy as np

        sensor = TemperatureSensor("temp", seed=42)
        assert isinstance(sensor.rng, np.random.Generator)
