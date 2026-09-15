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
    ConfigBase,
)

from zen_garden_plugins.domestic_potential_requirements.constraints import (
    DomesticPotentialRequirementConstraint,
)
from zen_garden_plugins.domestic_potential_requirements.parameters import (
    BackupPotential,
    WinterLimit,
)

# The config can be filled with parameters to be passed to the plugin. Define default
# parameters here. You can pass other values with the config in ZEN-garden.
# The config can be filled with parameters to be passed to the plugin. Define default
# parameters here. You can pass other values with the config in ZEN-garden.
class Config(ConfigBase):
    """
    Configuration for the domestic potential requirements plugin.
    """

    start_hour: int = 8016
    end_hour: int = 1416

# config: dict[str, Any] = {"start_hour": 8016, 
#                           "end_hour"  : 1416}

# Declare that a config will exist. This is added by the plugin system when the 
# plugin is loaded.
config: Config

# Choose the event that will trigger the function call
@EventPublisher.register(Event.after_model_schema_creation)
def add_domestic_production_requirements(model_schema: ModelSchema) -> None:

    model_schema.element_type_classes["Carrier"].own_parameters.append(WinterLimit)
    model_schema.element_type_classes["Carrier"].parameters.append(WinterLimit)

    model_schema.element_type_classes["Carrier"].own_parameters.append(BackupPotential)
    model_schema.element_type_classes["Carrier"].parameters.append(BackupPotential)
    model_schema.element_type_classes["Carrier"].constraints.append(
        DomesticPotentialRequirementConstraint
    )
