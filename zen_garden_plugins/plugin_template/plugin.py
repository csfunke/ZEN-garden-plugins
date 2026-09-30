"""
Template plugin for ZEN-garden.

This is a minimal working example showing how to:
- Set up plugin configuration
- Register a function to an event
- Access plugin settings
- Access the model and modify it

Copy this file as a starting point for your own plugin!
"""

from zen_garden import (  # type: ignore[import-untyped]
    ConfigBase,
    Event,
    EventPublisher,
    ModelSchema,
)

# ============================================================================
# Configuration: Define what settings your plugin accepts
# ============================================================================


class Config(ConfigBase):
    """Configuration for the plugin template.

    Users can override these defaults in their config.yaml:

        plugins:
          plugin_template:
            example_setting: "custom_value"
            example_number: 42
    """

    example_setting: str = "default_value"
    example_number: int = 100


# ============================================================================
# Event Handler: Register a function to run at a specific point
# ============================================================================


@EventPublisher.register(Event.after_model_schema_creation)
def extend_model(model_schema: ModelSchema) -> None:
    """
    This function runs after ZEN-garden creates the model schema.

    At this point, you can:
    - Add new variables or constraints
    - Modify existing ones
    - Access the configuration
    - Access the energy system information

    Args:
        model_schema: The model schema object provided by ZEN-garden

    Example of what you can do:
        - model_schema.add_variable(...)
        - model_schema.add_constraint(...)
        - Access model_schema.config.plugins["plugin_template"]
    """
    # Get your plugin's configuration
    config = model_schema.config.plugins["plugin_template"]

    # Access settings from config.yaml
    example_setting = config["example_setting"]
    example_number = config["example_number"]

    # Print to verify the plugin ran and received the config
    print(f"[Plugin Template] Example setting: {example_setting}")
    print(f"[Plugin Template] Example number: {example_number}")
    print("[Plugin Template] Plugin loaded successfully!")
