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

from zen_garden_plugins.domestic_production_requirements.constraints import (
    NetTransportLimitConstraint,
)
from zen_garden_plugins.domestic_production_requirements.parameters import (
    TransportLimitIn,
    TransportLimitNet,
    TransportLimitOut,
)

# The config can be filled with parameters to be passed to the plugin. Define default
# parameters here. You can pass other values with the config in ZEN-garden.
config: dict[str, Any] = {"test_setting": "default_value"}


# Choose the event that will trigger the function call
@EventPublisher.register(Event.after_model_schema_creation)
def add_domestic_production_requirements(model_schema: ModelSchema) -> None:

    model_schema.element_type_classes["Carrier"].own_parameters.append(TransportLimitIn)
    model_schema.element_type_classes["Carrier"].own_parameters.append(TransportLimitOut)
    model_schema.element_type_classes["Carrier"].own_parameters.append(TransportLimitNet)
    model_schema.element_type_classes["Carrier"].parameters.append(TransportLimitIn)
    model_schema.element_type_classes["Carrier"].parameters.append(TransportLimitOut)
    model_schema.element_type_classes["Carrier"].parameters.append(TransportLimitNet)
    model_schema.element_type_classes["Carrier"].constraints.append(NetTransportLimitConstraint)

    print(
        f"Hello. This is the plugin speaking. I am printing the"
        f" config setting 'test_setting': {config['test_setting']}"
    )
