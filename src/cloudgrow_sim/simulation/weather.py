"""Weather data sources for greenhouse simulation.

This module provides weather data to the simulation engine through
various sources:
- Synthetic: Generate realistic weather patterns mathematically
- CSV: Load historical weather data from files
- (Future) Home Assistant: Real-time data from HA sensors

All weather sources implement the WeatherSource protocol.
"""

from __future__ import annotations

import csv
import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

# Allowed file extensions for CSV weather files
_ALLOWED_CSV_EXTENSIONS: frozenset[str] = frozenset({".csv", ".CSV"})


@dataclass
class WeatherConditions:
    """Current weather conditions at a point in time.

    Attributes:
        timestamp: Time of the weather observation.
        temperature: Air temperature in C.
        humidity: Relative humidity as percentage (0-100).
        solar_radiation: Global horizontal irradiance in W/m2.
        wind_speed: Wind speed in m/s.
        wind_direction: Wind direction in degrees from North.
        cloud_cover: Cloud cover fraction (0-1).
        pressure: Atmospheric pressure in Pa.
        precipitation: Precipitation rate in mm/h.
    """

    timestamp: datetime
    temperature: float
    humidity: float
    solar_radiation: float
    wind_speed: float = 0.0
    wind_direction: float = 180.0
    cloud_cover: float = 0.0
    pressure: float = 101325.0
    precipitation: float = 0.0


class WeatherSource(ABC):
    """Abstract base class for weather data sources.

    All weather sources must implement get_conditions() to provide
    weather data for a given timestamp.
    """

    @abstractmethod
    def get_conditions(self, timestamp: datetime) -> WeatherConditions:
        """Get weather conditions for a specific timestamp.

        Args:
            timestamp: The datetime to get conditions for.

        Returns:
            WeatherConditions for the requested time.
        """
        ...

    def get_conditions_range(
        self,
        start: datetime,
        end: datetime,
        interval: timedelta,
    ) -> Iterator[WeatherConditions]:
        """Generate weather conditions over a time range.

        Args:
            start: Start datetime.
            end: End datetime.
            interval: Time step between conditions.

        Yields:
            WeatherConditions for each time step.
        """
        current = start
        while current <= end:
            yield self.get_conditions(current)
            current += interval


@dataclass
class SyntheticWeatherConfig:
    """Configuration for synthetic weather generation.

    Attributes:
        latitude: Site latitude for day length calculations.
        temp_mean: Mean annual temperature in C.
        temp_amplitude_annual: Annual temperature variation in C.
        temp_amplitude_daily: Daily temperature variation in C.
        humidity_mean: Mean relative humidity (%).
        humidity_amplitude: Daily humidity variation (%).
        solar_max: Maximum clear-sky solar radiation in W/m2.
        wind_mean: Mean wind speed in m/s.
        wind_std: Wind speed standard deviation.
        cloud_cover_mean: Mean cloud cover (0-1).
    """

    latitude: float = 37.0
    temp_mean: float = 15.0
    temp_amplitude_annual: float = 12.0
    temp_amplitude_daily: float = 8.0
    humidity_mean: float = 60.0
    humidity_amplitude: float = 20.0
    solar_max: float = 1000.0
    wind_mean: float = 2.5
    wind_std: float = 1.5
    cloud_cover_mean: float = 0.3


class SyntheticWeatherSource(WeatherSource):
    """Generate synthetic weather data using mathematical models.

    Produces realistic daily and seasonal patterns:
    - Temperature: Sinusoidal daily and annual cycles
    - Solar: Bell curve following sun path
    - Humidity: Inverse relationship with temperature
    - Wind: Random with diurnal pattern

    This is useful for testing and demonstration when real weather
    data is not available.
    """

    def __init__(self, config: SyntheticWeatherConfig | None = None) -> None:
        """Initialize synthetic weather source.

        Args:
            config: Weather generation configuration.
        """
        self.config = config or SyntheticWeatherConfig()
        self._seed = 42  # For reproducible randomness

    def _day_of_year(self, dt: datetime) -> int:
        """Get day of year (1-366)."""
        return dt.timetuple().tm_yday

    def _hour_decimal(self, dt: datetime) -> float:
        """Get decimal hour of day (0-24)."""
        return dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    def _day_length(self, day: int) -> float:
        """Approximate day length in hours.

        Uses simplified model based on latitude and day of year.

        Args:
            day: Day of year (1-366).

        Returns:
            Day length in hours.
        """
        lat_rad = math.radians(self.config.latitude)

        # Solar declination (simplified)
        declination = 23.45 * math.sin(math.radians(360 * (day - 81) / 365))
        decl_rad = math.radians(declination)

        # Hour angle at sunrise/sunset
        cos_hour_angle = -math.tan(lat_rad) * math.tan(decl_rad)
        cos_hour_angle = max(-1.0, min(1.0, cos_hour_angle))

        hour_angle = math.degrees(math.acos(cos_hour_angle))
        return 2 * hour_angle / 15.0

    def _sunrise_hour(self, day: int) -> float:
        """Get approximate sunrise hour."""
        day_length = self._day_length(day)
        return 12.0 - day_length / 2.0

    def _sunset_hour(self, day: int) -> float:
        """Get approximate sunset hour."""
        day_length = self._day_length(day)
        return 12.0 + day_length / 2.0

    def get_conditions(self, timestamp: datetime) -> WeatherConditions:
        """Generate weather conditions for a timestamp.

        Args:
            timestamp: The datetime to generate conditions for.

        Returns:
            Synthetic WeatherConditions.
        """
        day = self._day_of_year(timestamp)
        hour = self._hour_decimal(timestamp)

        # Temperature: annual + daily cycle
        # Annual: coldest around day 15 (mid-January), warmest around day 196
        annual_temp = self.config.temp_amplitude_annual * math.cos(
            2 * math.pi * (day - 15) / 365
        )

        # Daily: coldest at dawn (~6am), warmest at ~3pm
        daily_temp = self.config.temp_amplitude_daily * math.cos(
            2 * math.pi * (hour - 15) / 24
        )

        temperature = self.config.temp_mean - annual_temp + daily_temp

        # Solar radiation: bell curve during daylight
        sunrise = self._sunrise_hour(day)
        sunset = self._sunset_hour(day)

        if sunrise < hour < sunset:
            # Normalized hour within daylight period
            day_progress = (hour - sunrise) / (sunset - sunrise)
            # Bell curve peaking at solar noon
            solar_factor = math.sin(math.pi * day_progress)
            # Apply cloud cover reduction
            cloud_factor = 1.0 - 0.75 * self.config.cloud_cover_mean
            solar_radiation = self.config.solar_max * solar_factor * cloud_factor
        else:
            solar_radiation = 0.0

        # Humidity: inversely related to temperature
        # Higher at night, lower during hot afternoons
        humidity_base = self.config.humidity_mean
        humidity_daily = self.config.humidity_amplitude * math.cos(
            2 * math.pi * (hour - 15) / 24
        )
        humidity = max(20.0, min(100.0, humidity_base + humidity_daily))

        # Wind: slight diurnal pattern (calmer at night)
        wind_diurnal = 0.3 * math.sin(2 * math.pi * (hour - 6) / 24)
        wind_base = self.config.wind_mean * (1.0 + wind_diurnal)
        # Simple pseudo-random variation based on timestamp
        wind_noise = math.sin(day * 0.1 + hour * 0.5) * self.config.wind_std * 0.5
        wind_speed = max(0.0, wind_base + wind_noise)

        # Wind direction: slowly varying
        wind_direction = (180.0 + 90.0 * math.sin(day * 0.05)) % 360.0

        return WeatherConditions(
            timestamp=timestamp,
            temperature=temperature,
            humidity=humidity,
            solar_radiation=max(0.0, solar_radiation),
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            cloud_cover=self.config.cloud_cover_mean,
            pressure=101325.0,
            precipitation=0.0,
        )


@dataclass
class CSVWeatherMapping:
    """Column mapping for CSV weather files.

    Maps CSV column names to weather condition fields.
    """

    timestamp: str = "timestamp"
    temperature: str = "temperature"
    humidity: str = "humidity"
    solar_radiation: str = "solar_radiation"
    wind_speed: str = "wind_speed"
    wind_direction: str = "wind_direction"
    cloud_cover: str = "cloud_cover"
    pressure: str = "pressure"
    precipitation: str = "precipitation"


def _validate_csv_path(file_path: Path) -> Path:
    """Validate and sanitize a CSV file path.

    Performs security checks to prevent path traversal attacks and
    symlink bypass attacks, and ensures the file has a valid CSV extension.

    Security measures:
    - Resolves path components (../) to prevent directory traversal
    - Follows symlinks to check the real target path
    - Blocks access to sensitive system directories

    Args:
        file_path: The path to validate.

    Returns:
        The resolved, validated path.

    Raises:
        ValueError: If the path is invalid, has wrong extension,
                    or fails security checks.
    """
    # Resolve to absolute path to normalize any .. or . components
    resolved_path = file_path.resolve()

    # SEC-1 Fix: Follow symlinks to get the real target path
    # This prevents symlink bypass attacks where a symlink named "weather.csv"
    # could point to a sensitive file like /etc/passwd
    try:
        # resolve(strict=True) follows symlinks and raises FileNotFoundError
        # if the target doesn't exist
        real_path = resolved_path.resolve(strict=True)
    except FileNotFoundError:
        # File doesn't exist yet - use the resolved path for validation
        # This is safe because we're checking the target path, not the symlink
        real_path = resolved_path

    # Check file extension on the real path
    if real_path.suffix.lower() not in _ALLOWED_CSV_EXTENSIONS:
        msg = (
            f"Invalid file extension '{real_path.suffix}'. "
            f"Only CSV files are allowed (extensions: {_ALLOWED_CSV_EXTENSIONS})"
        )
        raise ValueError(msg)

    # Security check: Ensure resolved path doesn't escape to sensitive locations
    # This prevents path traversal attacks like "../../etc/passwd"
    # Check the REAL path (after following symlinks)
    resolved_str = str(real_path)

    # Block access to common sensitive system directories
    # These patterns are specific enough to avoid blocking temp directories
    # (e.g., /var/folders on macOS is allowed, but /var/log is not)
    # The patterns use exact directory boundaries to be precise
    sensitive_patterns = (
        # Unix sensitive directories
        "/etc/",
        "/var/log/",
        "/var/run/",
        "/var/spool/",
        "/var/cache/",
        "/usr/",
        "/bin/",
        "/sbin/",
        "/root/",
        "/proc/",
        "/sys/",
        # Windows sensitive directories
        "\\Windows\\",
        "\\System32\\",
        "\\Program Files\\",
    )

    for pattern in sensitive_patterns:
        if pattern in resolved_str:
            msg = f"Access to system directory not allowed: {real_path}"
            raise ValueError(msg)

    return resolved_path


class CSVWeatherSource(WeatherSource):
    """Load weather data from CSV files.

    Supports various CSV formats with configurable column mapping.
    Interpolates between data points for smooth transitions.

    Attributes:
        strict: If True, raise ValueError when columns are missing instead
            of using defaults. Useful for catching configuration errors early.
    """

    def __init__(
        self,
        file_path: Path | str,
        mapping: CSVWeatherMapping | None = None,
        timestamp_format: str = "%Y-%m-%d %H:%M:%S",
        strict: bool = False,
    ) -> None:
        """Initialize CSV weather source.

        Args:
            file_path: Path to CSV file.
            mapping: Column name mapping.
            timestamp_format: strptime format for timestamp column.
            strict: If True, raise ValueError when mapped columns are missing
                from the CSV file. If False (default), use sensible defaults
                for missing columns and log a warning.

        Raises:
            ValueError: If file path is invalid or has wrong extension.
        """
        # H3 Fix: Validate and sanitize path to prevent traversal attacks
        self.file_path = _validate_csv_path(Path(file_path))
        self.mapping = mapping or CSVWeatherMapping()
        self.timestamp_format = timestamp_format
        self._strict = strict
        self._data: list[WeatherConditions] = []
        self._loaded = False
        self._skipped_rows = 0

    def _load_data(self) -> None:
        """Load and parse CSV file."""
        if self._loaded:
            return

        self._data = []
        self._skipped_rows = 0
        # Track columns that used defaults (log once per column, not per row)
        columns_with_defaults: set[str] = set()
        # Track available columns for error messages (set on first row)
        available_columns: set[str] = set()

        def get_float_or_default(
            row: dict[str, str],
            column: str,
            default: float,
        ) -> float:
            """Get float value from row, logging if default is used.

            Args:
                row: CSV row as a dictionary.
                column: Column name to extract.
                default: Default value if column is missing.

            Returns:
                The float value from the column, or default if missing.

            Raises:
                ValueError: If strict mode is enabled and column is missing,
                    or if the value cannot be converted to float.
            """
            value = row.get(column)
            if value is None:
                if self._strict:
                    msg = (
                        f"Column '{column}' not found in CSV file. "
                        f"Available columns: {sorted(available_columns)}"
                    )
                    raise ValueError(msg)
                columns_with_defaults.add(column)
                return default
            try:
                return float(value)
            except ValueError as e:
                msg = f"Column '{column}' has invalid value '{value}': {e}"
                raise ValueError(msg) from e

        with self.file_path.open(newline="") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                # Capture available columns from first row
                if not available_columns:
                    available_columns = set(row.keys())

                try:
                    timestamp = datetime.strptime(
                        row[self.mapping.timestamp],
                        self.timestamp_format,
                    ).replace(tzinfo=UTC)

                    conditions = WeatherConditions(
                        timestamp=timestamp,
                        temperature=get_float_or_default(
                            row, self.mapping.temperature, 20.0
                        ),
                        humidity=get_float_or_default(row, self.mapping.humidity, 50.0),
                        solar_radiation=get_float_or_default(
                            row, self.mapping.solar_radiation, 0.0
                        ),
                        wind_speed=get_float_or_default(
                            row, self.mapping.wind_speed, 0.0
                        ),
                        wind_direction=get_float_or_default(
                            row, self.mapping.wind_direction, 180.0
                        ),
                        cloud_cover=get_float_or_default(
                            row, self.mapping.cloud_cover, 0.0
                        ),
                        pressure=get_float_or_default(
                            row, self.mapping.pressure, 101325.0
                        ),
                        precipitation=get_float_or_default(
                            row, self.mapping.precipitation, 0.0
                        ),
                    )
                    self._data.append(conditions)
                except KeyError as e:
                    self._skipped_rows += 1
                    logger.warning(
                        "Skipping row %d in %s: missing column %s",
                        row_num,
                        self.file_path,
                        e,
                    )
                except ValueError as e:
                    self._skipped_rows += 1
                    logger.warning(
                        "Skipping row %d in %s: invalid value - %s",
                        row_num,
                        self.file_path,
                        e,
                    )

        # Strict mode: raise if any columns used defaults
        if self._strict and columns_with_defaults:
            msg = (
                f"Strict mode: columns not found in CSV file: "
                f"{sorted(columns_with_defaults)}. "
                f"Available columns: {sorted(available_columns)}"
            )
            raise ValueError(msg)

        # Log warning for any columns that used default values
        if columns_with_defaults:
            logger.warning(
                "CSV file %s: columns not found, using defaults: %s. "
                "Check CSVWeatherMapping if this is unexpected.",
                self.file_path,
                ", ".join(sorted(columns_with_defaults)),
            )

        # Sort by timestamp
        self._data.sort(key=lambda c: c.timestamp)
        self._loaded = True

        if self._skipped_rows > 0:
            logger.info(
                "Loaded %d weather records from %s (%d rows skipped)",
                len(self._data),
                self.file_path,
                self._skipped_rows,
            )

    def _find_bracketing_indices(
        self, timestamp: datetime
    ) -> tuple[int | None, int | None]:
        """Find indices of data points bracketing the timestamp."""
        self._load_data()

        if not self._data:
            return None, None

        # Binary search for efficiency
        left, right = 0, len(self._data) - 1

        if timestamp <= self._data[left].timestamp:
            return None, left
        if timestamp >= self._data[right].timestamp:
            return right, None

        while right - left > 1:
            mid = (left + right) // 2
            if self._data[mid].timestamp <= timestamp:
                left = mid
            else:
                right = mid

        return left, right

    def _interpolate(
        self,
        c1: WeatherConditions,
        c2: WeatherConditions,
        timestamp: datetime,
    ) -> WeatherConditions:
        """Interpolate between two weather conditions."""
        # Calculate interpolation factor
        total_seconds = (c2.timestamp - c1.timestamp).total_seconds()
        if total_seconds == 0:
            return c1

        factor = (timestamp - c1.timestamp).total_seconds() / total_seconds

        def lerp(a: float, b: float) -> float:
            return a + (b - a) * factor

        return WeatherConditions(
            timestamp=timestamp,
            temperature=lerp(c1.temperature, c2.temperature),
            humidity=lerp(c1.humidity, c2.humidity),
            solar_radiation=lerp(c1.solar_radiation, c2.solar_radiation),
            wind_speed=lerp(c1.wind_speed, c2.wind_speed),
            wind_direction=lerp(c1.wind_direction, c2.wind_direction),
            cloud_cover=lerp(c1.cloud_cover, c2.cloud_cover),
            pressure=lerp(c1.pressure, c2.pressure),
            precipitation=lerp(c1.precipitation, c2.precipitation),
        )

    def get_conditions(self, timestamp: datetime) -> WeatherConditions:
        """Get interpolated weather conditions for timestamp.

        Args:
            timestamp: The datetime to get conditions for.

        Returns:
            Interpolated WeatherConditions.

        Raises:
            ValueError: If no data is loaded or timestamp is out of range.
        """
        self._load_data()

        if not self._data:
            msg = f"No weather data loaded from {self.file_path}"
            raise ValueError(msg)

        left_idx, right_idx = self._find_bracketing_indices(timestamp)

        # Handle edge cases
        if left_idx is None and right_idx is not None:
            # Before first data point - use first
            first = self._data[right_idx]
            return WeatherConditions(
                timestamp=timestamp,
                temperature=first.temperature,
                humidity=first.humidity,
                solar_radiation=first.solar_radiation,
                wind_speed=first.wind_speed,
                wind_direction=first.wind_direction,
                cloud_cover=first.cloud_cover,
                pressure=first.pressure,
                precipitation=first.precipitation,
            )

        if right_idx is None and left_idx is not None:
            # After last data point - use last
            last = self._data[left_idx]
            return WeatherConditions(
                timestamp=timestamp,
                temperature=last.temperature,
                humidity=last.humidity,
                solar_radiation=last.solar_radiation,
                wind_speed=last.wind_speed,
                wind_direction=last.wind_direction,
                cloud_cover=last.cloud_cover,
                pressure=last.pressure,
                precipitation=last.precipitation,
            )

        # Both indices are valid - interpolate
        if left_idx is None or right_idx is None:
            # This shouldn't happen with valid data, but satisfy type checker
            msg = f"Invalid bracketing indices for timestamp {timestamp}"
            raise ValueError(msg)

        # Interpolate between bracketing points
        return self._interpolate(
            self._data[left_idx],
            self._data[right_idx],
            timestamp,
        )

    @property
    def time_range(self) -> tuple[datetime, datetime] | None:
        """Get the time range of loaded data."""
        self._load_data()
        if not self._data:
            return None
        return self._data[0].timestamp, self._data[-1].timestamp

    @property
    def skipped_rows(self) -> int:
        """Number of rows skipped during loading due to errors."""
        self._load_data()
        return self._skipped_rows

    def __len__(self) -> int:
        """Number of data points loaded."""
        self._load_data()
        return len(self._data)
