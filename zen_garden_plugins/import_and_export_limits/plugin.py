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

from zen_garden_plugins.import_and_export_limits.constraints import (
    NetImportConstraint,
)
from zen_garden_plugins.import_and_export_limits.parameters import (
    TransportLimitIn,
    TransportLimitNet,
    TransportLimitOut,
)


# The config can be filled with parameters to be passed to the plugin. Define default
# parameters here. You can pass other values with the config in ZEN-garden.
class Config(ConfigBase):
    """Configuration for the import and export limits plugin."""

    start_hour: int = 8016
    end_hour: int = 1416


# Choose the event that will trigger the function call
@EventPublisher.register(Event.after_model_schema_creation)
def add_import_and_export_limits(model_schema: ModelSchema) -> None:

    model_schema.element_type_classes["Carrier"].own_parameters.append(TransportLimitIn)
    model_schema.element_type_classes["Carrier"].parameters.append(TransportLimitIn)

    model_schema.element_type_classes["Carrier"].own_parameters.append(
        TransportLimitOut
    )
    model_schema.element_type_classes["Carrier"].parameters.append(TransportLimitOut)

    model_schema.element_type_classes["Carrier"].own_parameters.append(
        TransportLimitNet
    )
    model_schema.element_type_classes["Carrier"].parameters.append(TransportLimitNet)

    model_schema.element_type_classes["Carrier"].constraints.append(NetImportConstraint)
