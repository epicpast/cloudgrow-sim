"""Tests for CLI interface."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cloudgrow_sim.core.registry import reset_registry
from cloudgrow_sim.main import app

runner = CliRunner()


class TestRunCommand:
    """Tests for the run command."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()

    def test_run_with_config_file(self, tmp_path: Path) -> None:
        """Test run command with config file."""
        config = tmp_path / "test.yaml"
        config.write_text("""
name: "CLI Test"
time_step: 60.0
duration: 120.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")

        result = runner.invoke(app, ["run", str(config), "-q"])

        # Should complete (exit code 0)
        assert result.exit_code == 0

    def test_run_with_both_config_and_scenario_errors(self, tmp_path: Path) -> None:
        """Test that specifying both config and scenario errors."""
        config = tmp_path / "test.yaml"
        config.write_text("name: test\n")

        result = runner.invoke(app, ["run", str(config), "--scenario", "basic"])

        assert result.exit_code == 1
        assert "Cannot specify both" in result.stdout

    def test_run_with_missing_config_errors(self) -> None:
        """Test that missing config file errors."""
        result = runner.invoke(app, ["run", "/nonexistent/path.yaml"])

        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_run_with_invalid_config_errors(self, tmp_path: Path) -> None:
        """Test that invalid config file errors."""
        config = tmp_path / "invalid.yaml"
        config.write_text("not: valid: yaml: config")

        result = runner.invoke(app, ["run", str(config)])

        assert result.exit_code == 1

    def test_run_with_duration_override(self, tmp_path: Path) -> None:
        """Test duration override flag."""
        config = tmp_path / "test.yaml"
        config.write_text("""
name: "Duration Test"
time_step: 60.0
duration: 86400.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")

        # Override to just 1 minute (0.0166 hours)
        result = runner.invoke(app, ["run", str(config), "-d", "0.0166", "-q"])

        assert result.exit_code == 0

    def test_run_with_timestep_override(self, tmp_path: Path) -> None:
        """Test time step override flag."""
        config = tmp_path / "test.yaml"
        config.write_text("""
name: "Timestep Test"
time_step: 1.0
duration: 120.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")

        result = runner.invoke(app, ["run", str(config), "-t", "60.0", "-q"])

        assert result.exit_code == 0

    def test_run_with_output_dir(self, tmp_path: Path) -> None:
        """Test output directory flag."""
        config = tmp_path / "test.yaml"
        config.write_text("""
name: "Output Test"
time_step: 60.0
duration: 120.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")
        output_dir = tmp_path / "results"

        result = runner.invoke(app, ["run", str(config), "-o", str(output_dir), "-q"])

        assert result.exit_code == 0
        assert output_dir.exists()
        assert (output_dir / "results.json").exists()

    def test_run_with_json_format(self, tmp_path: Path) -> None:
        """Test JSON output format."""
        config = tmp_path / "test.yaml"
        config.write_text("""
name: "JSON Test"
time_step: 60.0
duration: 120.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")
        output_dir = tmp_path / "json_results"

        result = runner.invoke(
            app, ["run", str(config), "-f", "json", "-o", str(output_dir), "-q"]
        )

        assert result.exit_code == 0
        json_file = output_dir / "results.json"
        assert json_file.exists()
        content = json_file.read_text()
        assert "steps_completed" in content

    def test_run_with_csv_format(self, tmp_path: Path) -> None:
        """Test CSV output format."""
        config = tmp_path / "test.yaml"
        config.write_text("""
name: "CSV Test"
time_step: 60.0
duration: 120.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")
        output_dir = tmp_path / "csv_results"

        result = runner.invoke(
            app, ["run", str(config), "-f", "csv", "-o", str(output_dir), "-q"]
        )

        assert result.exit_code == 0
        csv_file = output_dir / "results.csv"
        assert csv_file.exists()
        content = csv_file.read_text()
        assert "metric,value" in content

    def test_run_quiet_mode(self, tmp_path: Path) -> None:
        """Test quiet mode suppresses output."""
        config = tmp_path / "test.yaml"
        config.write_text("""
name: "Quiet Test"
time_step: 60.0
duration: 120.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")

        result = runner.invoke(app, ["run", str(config), "-q"])

        assert result.exit_code == 0
        # Quiet mode should produce minimal output
        assert "Running:" not in result.stdout

    def test_run_no_args_errors(self) -> None:
        """Test that run without args shows error."""
        result = runner.invoke(app, ["run"])

        assert result.exit_code == 1
        assert "Provide a config file" in result.stdout


class TestListCommand:
    """Tests for the list command."""

    def test_list_shows_scenarios(self) -> None:
        """Test list command shows scenario table."""
        result = runner.invoke(app, ["list"])

        # Should complete without error
        assert result.exit_code == 0
        assert "Available Scenarios" in result.stdout

    def test_list_shows_builtin_names(self) -> None:
        """Test that list shows built-in scenario names."""
        result = runner.invoke(app, ["list"])

        assert "basic" in result.stdout
        assert "full-climate" in result.stdout


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_valid_yaml(self, tmp_path: Path) -> None:
        """Test init command creates valid YAML file."""
        output = tmp_path / "new-scenario.yaml"

        result = runner.invoke(app, ["init", "Test Scenario", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()
        assert "Created:" in result.stdout

    def test_init_with_custom_output_path(self, tmp_path: Path) -> None:
        """Test init with custom output path."""
        output = tmp_path / "subdir" / "custom.yaml"

        result = runner.invoke(app, ["init", "Custom", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()

    def test_init_generated_config_validates(self, tmp_path: Path) -> None:
        """Test that generated config can be validated."""
        output = tmp_path / "generated.yaml"
        runner.invoke(app, ["init", "Generated", "-o", str(output)])

        # Validate the generated file
        result = runner.invoke(app, ["validate", str(output)])

        assert result.exit_code == 0
        assert "Valid:" in result.stdout

    def test_init_default_filename(self, tmp_path: Path) -> None:
        """Test init creates default filename from name."""
        # Change to tmp_path for the test
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["init", "My Greenhouse"])

            assert result.exit_code == 0
            assert (tmp_path / "my-greenhouse.yaml").exists()
        finally:
            os.chdir(original_cwd)


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_config(self, tmp_path: Path) -> None:
        """Test validate with valid config."""
        config = tmp_path / "valid.yaml"
        config.write_text("""
name: "Valid Config"
time_step: 60.0
duration: 3600.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")

        result = runner.invoke(app, ["validate", str(config)])

        assert result.exit_code == 0
        assert "Valid:" in result.stdout
        assert "Valid Config" in result.stdout

    def test_validate_invalid_config_exits_nonzero(self, tmp_path: Path) -> None:
        """Test validate with invalid config exits with error."""
        config = tmp_path / "invalid.yaml"
        config.write_text("""
name: "Invalid Config"
location:
  latitude: 200.0  # Invalid latitude
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
""")

        result = runner.invoke(app, ["validate", str(config)])

        assert result.exit_code == 1
        assert "Invalid:" in result.stdout

    def test_validate_missing_file_exits_nonzero(self) -> None:
        """Test validate with missing file exits with error."""
        result = runner.invoke(app, ["validate", "/nonexistent/path.yaml"])

        assert result.exit_code == 1
        assert "File not found" in result.stdout

    def test_validate_shows_component_counts(self, tmp_path: Path) -> None:
        """Test validate shows component summary."""
        config = tmp_path / "components.yaml"
        config.write_text("""
name: "Component Count Test"
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
components:
  sensors:
    - type: temperature
      name: temp_1
      location: interior
    - type: humidity
      name: hum_1
      location: interior
  actuators:
    - type: exhaust_fan
      name: fan_1
      max_flow_rate: 1.0
      power_consumption: 500.0
  controllers:
    - type: hysteresis
      name: ctrl_1
      process_variable: temp_1.temperature
      setpoint: 25.0
""")

        result = runner.invoke(app, ["validate", str(config)])

        assert result.exit_code == 0
        assert "Sensors: 2" in result.stdout
        assert "Actuators: 1" in result.stdout
        assert "Controllers: 1" in result.stdout


class TestNoCommand:
    """Tests for CLI behavior without commands."""

    def test_no_args_shows_help(self) -> None:
        """Test that no arguments shows help."""
        result = runner.invoke(app, [])

        # Should show help (no_args_is_help=True)
        assert "ASHRAE-compliant" in result.stdout or result.exit_code == 0
