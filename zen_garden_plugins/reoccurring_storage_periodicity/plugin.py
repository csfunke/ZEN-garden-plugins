"""Register the recurring-storage-periodicity plugin components."""

from zen_garden import ConfigBase, Event, EventPublisher, ModelSchema
from zen_garden.elements.storage_technology import StorageTechnology

from zen_garden_plugins.reoccurring_storage_periodicity.constraints import (
    RecurringStoragePeriodicityConstraint,
)
from zen_garden_plugins.reoccurring_storage_periodicity.parameters import (
    StoragePeriodicityHours,
)


class Config(ConfigBase):
    """Configuration namespace for the plugin."""


@EventPublisher.register(Event.after_model_schema_creation)
def add_reoccurring_storage_periodicity_constraint(model_schema: ModelSchema) -> None:
    """Register the parameter and constraint on storage technologies.

    Args:
        model_schema: Mutable model blueprint supplied by ZEN-garden.
    """
    storage_technology = model_schema.element_type_classes["StorageTechnology"]
    if not issubclass(storage_technology, StorageTechnology):
        raise TypeError(
            "Expected the 'StorageTechnology' schema entry to contain a "
            "StorageTechnology subclass."
        )
    storage_technology.own_parameters.append(StoragePeriodicityHours)
    storage_technology.parameters.append(StoragePeriodicityHours)
    storage_technology.constraints.append(RecurringStoragePeriodicityConstraint)
