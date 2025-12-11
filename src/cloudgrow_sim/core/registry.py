"""Component registry for plugin-based discovery and registration.

This module implements a decorator-based registration system for greenhouse
simulation components. Components register themselves with the registry
at import time using the @register_component decorator.

Usage:
    @register_component("sensor", "temperature")
    class TemperatureSensor(Sensor):
        ...

    # Later, retrieve the component class
    registry = get_registry()
    sensor_class = registry.get("sensor", "temperature")
    sensor = sensor_class(name="main_sensor")
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from cloudgrow_sim.core.base import Component

T = TypeVar("T", bound="Component")

# Global registry instance
_registry: ComponentRegistry | None = None


class ComponentRegistry:
    """Registry for simulation components.

    The registry maintains a hierarchical structure:
    - Category (e.g., "sensor", "actuator", "controller")
      - Type (e.g., "temperature", "exhaust_fan", "pid")
        - Component class

    Attributes:
        components: Nested dict of category -> type -> class.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._components: dict[str, dict[str, type[Component]]] = defaultdict(dict)
        self._instances: dict[str, Component] = {}

    def register(
        self,
        category: str,
        component_type: str,
        component_class: type[T],
    ) -> type[T]:
        """Register a component class.

        Args:
            category: Component category (e.g., "sensor", "actuator").
            component_type: Specific type within category (e.g., "temperature").
            component_class: The component class to register.

        Returns:
            The registered class (for use as decorator).

        Raises:
            ValueError: If a different component with the same category/type
                is already registered.
        """
        if component_type in self._components[category]:
            existing = self._components[category][component_type]
            # Allow idempotent registration (same class re-registering after reload)
            # Check by class name since reloaded modules create new class objects
            if existing.__name__ == component_class.__name__:
                # Same class being re-registered, allow it
                self._components[category][component_type] = component_class
                return component_class
            msg = (
                f"Component '{category}/{component_type}' already registered "
                f"as {existing.__name__}"
            )
            raise ValueError(msg)

        self._components[category][component_type] = component_class
        return component_class

    def get(
        self,
        category: str,
        component_type: str,
    ) -> type[Component]:
        """Get a registered component class.

        Args:
            category: Component category.
            component_type: Specific type within category.

        Returns:
            The registered component class.

        Raises:
            KeyError: If the component is not registered.
        """
        if category not in self._components:
            msg = f"Unknown category: {category}"
            raise KeyError(msg)

        if component_type not in self._components[category]:
            available = list(self._components[category].keys())
            msg = f"Unknown type '{component_type}' in category '{category}'. Available: {available}"
            raise KeyError(msg)

        return self._components[category][component_type]

    def get_or_none(
        self,
        category: str,
        component_type: str,
    ) -> type[Component] | None:
        """Get a registered component class or None if not found.

        Args:
            category: Component category.
            component_type: Specific type within category.

        Returns:
            The registered component class, or None.
        """
        try:
            return self.get(category, component_type)
        except KeyError:
            return None

    def list_categories(self) -> list[str]:
        """List all registered categories.

        Returns:
            List of category names.
        """
        return list(self._components.keys())

    def list_types(self, category: str) -> list[str]:
        """List all registered types in a category.

        Args:
            category: Component category.

        Returns:
            List of type names in the category.
        """
        if category not in self._components:
            return []
        return list(self._components[category].keys())

    def list_all(self) -> dict[str, list[str]]:
        """List all registered components.

        Returns:
            Dict mapping categories to lists of types.
        """
        return {cat: list(types.keys()) for cat, types in self._components.items()}

    def create(
        self,
        category: str,
        component_type: str,
        name: str,
        **kwargs: Any,
    ) -> Component:
        """Create a component instance.

        Args:
            category: Component category.
            component_type: Specific type within category.
            name: Instance name (must be unique).
            **kwargs: Additional arguments passed to component constructor.

        Returns:
            New component instance.

        Raises:
            ValueError: If an instance with this name already exists.
        """
        if name in self._instances:
            msg = f"Component instance '{name}' already exists"
            raise ValueError(msg)

        component_class = self.get(category, component_type)
        instance = component_class(name=name, **kwargs)
        self._instances[name] = instance
        return instance

    def get_instance(self, name: str) -> Component | None:
        """Get a component instance by name.

        Args:
            name: Instance name.

        Returns:
            Component instance, or None if not found.
        """
        return self._instances.get(name)

    def remove_instance(self, name: str) -> bool:
        """Remove a component instance from the registry.

        Args:
            name: Instance name.

        Returns:
            True if removed, False if not found.
        """
        if name in self._instances:
            del self._instances[name]
            return True
        return False

    def clear_instances(self) -> None:
        """Remove all component instances."""
        self._instances.clear()

    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._components.clear()
        self._instances.clear()


def get_registry() -> ComponentRegistry:
    """Get the global component registry.

    Creates the registry on first call.

    Returns:
        The global ComponentRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = ComponentRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry.

    Primarily useful for testing.
    """
    global _registry
    if _registry is not None:
        _registry.clear()
    _registry = None


def register_component(
    category: str,
    component_type: str,
) -> Any:  # Returns Callable[[type[T]], type[T]] but mypy struggles with this
    """Decorator to register a component class.

    Usage:
        @register_component("sensor", "temperature")
        class TemperatureSensor(Sensor):
            ...

    Args:
        category: Component category (e.g., "sensor", "actuator", "controller").
        component_type: Specific type within category.

    Returns:
        Decorator function that registers the class.
    """

    def decorator(cls: type[T]) -> type[T]:
        registry = get_registry()
        return registry.register(category, component_type, cls)

    return decorator


def list_components() -> dict[str, list[str]]:
    """List all registered components.

    Returns:
        Dict mapping categories to lists of component types.
    """
    return get_registry().list_all()


def create_component(
    category: str,
    component_type: str,
    name: str,
    **kwargs: Any,
) -> Component:
    """Create a component instance.

    Convenience function wrapping registry.create().

    Args:
        category: Component category.
        component_type: Specific type within category.
        name: Instance name.
        **kwargs: Additional arguments for component constructor.

    Returns:
        New component instance.
    """
    return get_registry().create(category, component_type, name, **kwargs)
