"""
A template for a plugin.

Write functions that subscribe to an event in ZEN-garden. These functions are executed
when ZEN-garden reaches the trigger to the respective event.
"""

from zen_garden import (  # type: ignore[import-untyped]
    ConfigBase,
    Event,
    EventPublisher,
    ModelSchema,
)


# The config can be filled with parameters to be passed to the plugin. Define default
# parameters here. You can pass other values with the config in ZEN-garden.
class Config(ConfigBase):
    """Configuration for the plugin template."""

    any_setting: str = "value_of_any_setting"


# Choose the event that will trigger the function call
@EventPublisher.register(Event.after_model_schema_creation)
def function_to_be_called_at_test_event1(model_schema: ModelSchema) -> None:
    """This function will be called when the execution reaches the trigger to the event.

    You can implement e.g. new constraints or variables as a plugin which are added
    to the model.
    Make sure the function signature matches with event trigger in ZEN-garden:

    for e.g.:
    ``EventPublisher.trigger(Event.after_model_schema_creation,
    model_schema=model_schema)``

    the function definition has to be:
    ``def function_to_be_called_at_after_model_schema_creation(model_schema):``

    """
    config = model_schema.config.plugins["plugin_template"]
    print(
        "Hello. This is the plugin speaking. I am printing the"
        f" config setting 'any_setting': {config['any_setting']}"
    )
