"""
A template for a plugin.

Write functions that subscribe to an event in ZEN-garden. These functions are executed
when ZEN-garden reaches the trigger to the respective event.
"""

from typing import Any, cast

from zen_garden import (  # type: ignore[import-untyped]
    ConfigBase,
    Event,
    EventPublisher,
    ModelSchema,
)

from zen_garden_plugins.net_survival_limit.constraints import NetSurvivalLimitConstraint
from zen_garden_plugins.net_survival_limit.parameters import (
    BackupPotential,
    WinterLimit,
)


# The config can be filled with parameters to be passed to the plugin. Define default
# parameters here. You can pass other values with the config in ZEN-garden.
# The config can be filled with parameters to be passed to the plugin. Define default
# parameters here. You can pass other values with the config in ZEN-garden.
class Config(ConfigBase):
    """
    Configuration for the net survival limit plugin.
    """

    start_hour: int = 8016
    end_hour: int = 1416
    include_endogenous_demand: bool = True


# config: dict[str, Any] = {"start_hour": 8016,
#                           "end_hour"  : 1416}


# Choose the event that will trigger the function call
@EventPublisher.register(Event.after_model_schema_creation)
def add_net_survival_limit(model_schema: ModelSchema) -> None:
    carrier = cast(Any, model_schema.element_type_classes["Carrier"])

    carrier.own_parameters.append(WinterLimit)
    carrier.parameters.append(WinterLimit)

    carrier.own_parameters.append(BackupPotential)
    carrier.parameters.append(BackupPotential)
    carrier.constraints.append(NetSurvivalLimitConstraint)
