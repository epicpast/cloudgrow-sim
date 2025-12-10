"""Tests for weather data sources."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cloudgrow_sim.simulation.weather import (
    CSVWeatherMapping,
    CSVWeatherSource,
    SyntheticWeatherConfig,
    SyntheticWeatherSource,
    WeatherConditions,
)


class TestWeatherConditions:
    """Tests for WeatherConditions dataclass."""

    def test_creation(self) -> None:
        """Create weather conditions with all fields."""
        now = datetime.now(UTC)
        cond = WeatherConditions(
            timestamp=now,
            temperature=25.0,
            humidity=60.0,
            solar_radiation=800.0,
            wind_speed=3.0,
            wind_direction=180.0,
            cloud_cover=0.3,
            pressure=101325.0,
            precipitation=0.0,
        )
        assert cond.temperature == 25.0
        assert cond.humidity == 60.0
        assert cond.solar_radiation == 800.0

    def test_defaults(self) -> None:
        """Default values for optional fields."""
        now = datetime.now(UTC)
        cond = WeatherConditions(
            timestamp=now,
            temperature=20.0,
            humidity=50.0,
            solar_radiation=500.0,
        )
        assert cond.wind_speed == 0.0
        assert cond.wind_direction == 180.0
        assert cond.cloud_cover == 0.0
        assert cond.pressure == 101325.0
        assert cond.precipitation == 0.0


class TestSyntheticWeatherSource:
    """Tests for SyntheticWeatherSource."""

    def test_default_config(self) -> None:
        """Default configuration works."""
        source = SyntheticWeatherSource()
        now = datetime.now(UTC)
        cond = source.get_conditions(now)
        assert cond.timestamp == now
        assert -50 < cond.temperature < 50
        assert 0 <= cond.humidity <= 100
        assert cond.solar_radiation >= 0

    def test_custom_config(self) -> None:
        """Custom configuration applies."""
        config = SyntheticWeatherConfig(
            temp_mean=25.0,
            temp_amplitude_daily=5.0,
            humidity_mean=70.0,
        )
        source = SyntheticWeatherSource(config)
        # Get midday conditions
        dt = datetime(2025, 6, 21, 12, 0, tzinfo=UTC)
        cond = source.get_conditions(dt)
        # Temperature should be reasonable for a summer day
        # (includes annual cycle which adds warmth in summer)
        assert 10 < cond.temperature < 50

    def test_diurnal_temperature_cycle(self) -> None:
        """Temperature follows diurnal cycle."""
        source = SyntheticWeatherSource()
        dt = datetime(2025, 6, 21, tzinfo=UTC)

        # Early morning (6 AM) should be coolest
        morning = source.get_conditions(dt.replace(hour=6))
        # Afternoon (3 PM) should be warmest
        afternoon = source.get_conditions(dt.replace(hour=15))

        assert afternoon.temperature > morning.temperature

    def test_solar_radiation_daylight(self) -> None:
        """Solar radiation positive during day, zero at night."""
        source = SyntheticWeatherSource(
            SyntheticWeatherConfig(latitude=37.0, solar_max=1000.0)
        )
        dt = datetime(2025, 6, 21, tzinfo=UTC)

        # Midday should have high solar
        noon = source.get_conditions(dt.replace(hour=12))
        assert noon.solar_radiation > 500

        # Midnight should have zero solar
        midnight = source.get_conditions(dt.replace(hour=0))
        assert midnight.solar_radiation == 0

    def test_solar_bell_curve(self) -> None:
        """Solar radiation follows bell curve during day."""
        source = SyntheticWeatherSource()
        dt = datetime(2025, 6, 21, tzinfo=UTC)

        morning = source.get_conditions(dt.replace(hour=8))
        noon = source.get_conditions(dt.replace(hour=12))
        afternoon = source.get_conditions(dt.replace(hour=16))

        # Noon should be highest
        assert noon.solar_radiation > morning.solar_radiation
        assert noon.solar_radiation > afternoon.solar_radiation

    def test_get_conditions_range(self) -> None:
        """Generate conditions over a range."""
        source = SyntheticWeatherSource()
        start = datetime(2025, 6, 21, 0, 0, tzinfo=UTC)
        end = datetime(2025, 6, 21, 23, 0, tzinfo=UTC)

        conditions = list(source.get_conditions_range(start, end, timedelta(hours=1)))

        assert len(conditions) == 24
        assert conditions[0].timestamp == start
        assert conditions[-1].timestamp == end

    def test_wind_variation(self) -> None:
        """Wind speed varies throughout day."""
        source = SyntheticWeatherSource(
            SyntheticWeatherConfig(wind_mean=5.0, wind_std=2.0)
        )

        winds = []
        dt = datetime(2025, 6, 21, tzinfo=UTC)
        for hour in range(24):
            cond = source.get_conditions(dt.replace(hour=hour))
            winds.append(cond.wind_speed)

        # Should have some variation
        assert max(winds) > min(winds)
        # All non-negative
        assert all(w >= 0 for w in winds)


class TestCSVWeatherSource:
    """Tests for CSVWeatherSource."""

    def test_load_simple_csv(self) -> None:
        """Load a simple CSV weather file."""
        csv_content = """timestamp,temperature,humidity,solar_radiation
2025-06-21 00:00:00,15.0,70.0,0.0
2025-06-21 06:00:00,18.0,65.0,200.0
2025-06-21 12:00:00,28.0,45.0,900.0
2025-06-21 18:00:00,25.0,50.0,300.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            path = Path(f.name)

        try:
            source = CSVWeatherSource(path)

            # Check we can get conditions
            dt = datetime(2025, 6, 21, 12, 0, 0, tzinfo=UTC)
            cond = source.get_conditions(dt)

            assert cond.temperature == 28.0
            assert cond.humidity == 45.0
            assert cond.solar_radiation == 900.0

        finally:
            path.unlink()

    def test_interpolation(self) -> None:
        """Interpolate between data points."""
        csv_content = """timestamp,temperature,humidity,solar_radiation
2025-06-21 00:00:00,10.0,80.0,0.0
2025-06-21 12:00:00,30.0,40.0,1000.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            path = Path(f.name)

        try:
            source = CSVWeatherSource(path)

            # Get conditions at midpoint (6 AM)
            dt = datetime(2025, 6, 21, 6, 0, 0, tzinfo=UTC)
            cond = source.get_conditions(dt)

            # Should be interpolated
            assert 19 < cond.temperature < 21  # ~20
            assert 59 < cond.humidity < 61  # ~60
            assert 490 < cond.solar_radiation < 510  # ~500

        finally:
            path.unlink()

    def test_custom_mapping(self) -> None:
        """Use custom column mapping."""
        csv_content = """time,temp_c,rh_pct,ghi
2025-06-21 12:00:00,25.0,55.0,800.0
"""
        mapping = CSVWeatherMapping(
            timestamp="time",
            temperature="temp_c",
            humidity="rh_pct",
            solar_radiation="ghi",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            path = Path(f.name)

        try:
            source = CSVWeatherSource(path, mapping=mapping)
            dt = datetime(2025, 6, 21, 12, 0, 0, tzinfo=UTC)
            cond = source.get_conditions(dt)

            assert cond.temperature == 25.0
            assert cond.humidity == 55.0
            assert cond.solar_radiation == 800.0

        finally:
            path.unlink()

    def test_time_range(self) -> None:
        """Get time range of loaded data."""
        csv_content = """timestamp,temperature,humidity,solar_radiation
2025-06-21 00:00:00,15.0,70.0,0.0
2025-06-21 12:00:00,28.0,45.0,900.0
2025-06-22 00:00:00,16.0,68.0,0.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            path = Path(f.name)

        try:
            source = CSVWeatherSource(path)
            time_range = source.time_range

            assert time_range is not None
            assert time_range[0] == datetime(2025, 6, 21, 0, 0, 0, tzinfo=UTC)
            assert time_range[1] == datetime(2025, 6, 22, 0, 0, 0, tzinfo=UTC)

        finally:
            path.unlink()

    def test_len(self) -> None:
        """Get number of data points."""
        csv_content = """timestamp,temperature,humidity,solar_radiation
2025-06-21 00:00:00,15.0,70.0,0.0
2025-06-21 06:00:00,18.0,65.0,200.0
2025-06-21 12:00:00,28.0,45.0,900.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            path = Path(f.name)

        try:
            source = CSVWeatherSource(path)
            assert len(source) == 3

        finally:
            path.unlink()

    def test_empty_file_error(self) -> None:
        """Error when file has no data."""
        csv_content = """timestamp,temperature,humidity,solar_radiation
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            path = Path(f.name)

        try:
            source = CSVWeatherSource(path)
            dt = datetime(2025, 6, 21, 12, 0, 0, tzinfo=UTC)

            with pytest.raises(ValueError, match="No weather data"):
                source.get_conditions(dt)

        finally:
            path.unlink()

    def test_before_data_range(self) -> None:
        """Handle timestamp before data range."""
        csv_content = """timestamp,temperature,humidity,solar_radiation
2025-06-21 12:00:00,25.0,50.0,800.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            path = Path(f.name)

        try:
            source = CSVWeatherSource(path)
            # Request before first data point
            dt = datetime(2025, 6, 20, 0, 0, 0, tzinfo=UTC)
            cond = source.get_conditions(dt)

            # Should return first data point values
            assert cond.temperature == 25.0

        finally:
            path.unlink()
