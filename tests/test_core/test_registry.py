"""Tests for component registry."""

from __future__ import annotations

import pytest

from cloudgrow_sim.core.base import Sensor
from cloudgrow_sim.core.registry import (
    ComponentRegistry,
    get_registry,
    register_component,
    reset_registry,
)
from cloudgrow_sim.core.state import GreenhouseState


class TestComponentRegistry:
    """Tests for ComponentRegistry class."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()

    def test_register_and_get(self) -> None:
        """Register and retrieve a component."""
        registry = ComponentRegistry()

        class TestSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        registry.register("sensor", "test", TestSensor)
        retrieved = registry.get("sensor", "test")
        assert retrieved is TestSensor

    def test_duplicate_registration_error(self) -> None:
        """Error on duplicate registration with different class."""
        registry = ComponentRegistry()

        class TestSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        class AnotherSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 1.0}

        registry.register("sensor", "test", TestSensor)

        # Same class can be re-registered (idempotent for module reloading)
        registry.register("sensor", "test", TestSensor)

        # But different class with same type should error
        with pytest.raises(ValueError, match="already registered"):
            registry.register("sensor", "test", AnotherSensor)

    def test_get_nonexistent(self) -> None:
        """Error when getting non-existent component."""
        registry = ComponentRegistry()

        with pytest.raises(KeyError):
            registry.get("sensor", "nonexistent")

    def test_get_or_none(self) -> None:
        """get_or_none returns None for non-existent."""
        registry = ComponentRegistry()
        result = registry.get_or_none("sensor", "nonexistent")
        assert result is None

    def test_list_categories(self) -> None:
        """List registered categories."""
        registry = ComponentRegistry()

        class TestSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        registry.register("sensor", "test", TestSensor)
        registry.register("actuator", "test", TestSensor)

        categories = registry.list_categories()
        assert "sensor" in categories
        assert "actuator" in categories

    def test_list_types(self) -> None:
        """List types in a category."""
        registry = ComponentRegistry()

        class TestSensor1(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        class TestSensor2(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        registry.register("sensor", "type1", TestSensor1)
        registry.register("sensor", "type2", TestSensor2)

        types = registry.list_types("sensor")
        assert "type1" in types
        assert "type2" in types

    def test_create_instance(self) -> None:
        """Create component instance."""
        registry = ComponentRegistry()

        class TestSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        registry.register("sensor", "test", TestSensor)
        instance = registry.create("sensor", "test", "my_sensor")

        assert instance.name == "my_sensor"
        assert isinstance(instance, TestSensor)

    def test_get_instance(self) -> None:
        """Retrieve created instance by name."""
        registry = ComponentRegistry()

        class TestSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        registry.register("sensor", "test", TestSensor)
        created = registry.create("sensor", "test", "my_sensor")
        retrieved = registry.get_instance("my_sensor")

        assert retrieved is created

    def test_clear_instances(self) -> None:
        """Clear all instances."""
        registry = ComponentRegistry()

        class TestSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        registry.register("sensor", "test", TestSensor)
        registry.create("sensor", "test", "sensor1")
        registry.create("sensor", "test", "sensor2")

        registry.clear_instances()

        assert registry.get_instance("sensor1") is None
        assert registry.get_instance("sensor2") is None


class TestRegisterDecorator:
    """Tests for @register_component decorator."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()

    def test_decorator_registers(self) -> None:
        """Decorator registers class."""

        @register_component("sensor", "decorated_test")
        class DecoratedSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        registry = get_registry()
        cls = registry.get("sensor", "decorated_test")
        assert cls is DecoratedSensor

    def test_decorator_preserves_class(self) -> None:
        """Decorator returns original class."""

        @register_component("sensor", "preserved_test")
        class PreservedSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        # Class should still be usable
        instance = PreservedSensor("test")
        assert instance.name == "test"


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()

    def test_get_registry_singleton(self) -> None:
        """get_registry returns same instance."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_reset_registry(self) -> None:
        """reset_registry creates new instance."""
        reg1 = get_registry()

        class TestSensor(Sensor):
            def read(self, state: GreenhouseState) -> dict[str, float]:
                del state  # Unused in test
                return {"value": 0.0}

        reg1.register("sensor", "test", TestSensor)

        reset_registry()
        reg2 = get_registry()

        # New registry shouldn't have the registration
        assert reg2.get_or_none("sensor", "test") is None
