"""
A template for a plugin.

Write functions that subscribe to an event in ZEN-garden. These functions are executed
when ZEN-garden reaches the trigger to the respective event.
"""

from typing import Any

from zen_garden import (  # type: ignore[import-untyped]
    Event,
    EventPublisher,
    ModelSchema,
)

# The config can be filled with parameters to be passed to the plugin. Define default
# parameters here. You can pass other values with the config in ZEN-garden.
config: dict[str, Any] = {}


# Choose the event that will trigger the function call
@EventPublisher.register(Event.after_model_schema_creation)
def add_domestic_production_requirements(model_schema: ModelSchema) -> None:

    print(
        f"Hello. This is the plugin speaking. I am printing the"
        f" config setting 'any_setting': {config['any_setting']}"
    )
