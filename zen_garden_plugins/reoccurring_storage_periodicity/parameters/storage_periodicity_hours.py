"""Storage-periodicity input parameter."""

from zen_garden.model.component_types.parameter import GenericParameter


class StoragePeriodicityHours(GenericParameter):
    """Number of hours between equal storage states for one technology.

    A value of zero disables the additional intra-year periodicity constraint.
    Missing input is inserted with the explicit unit ``hour`` before delegating
    to ZEN-garden's standard parameter loader.
    """

    name = "storage_periodicity_hrs"
    indices = ("set_storage_technologies",)
    doc = "Hours between recurring equal storage states and zero disables it"
    unit_category = {"time": 1}
    default_value = 0
    # GenericParameter requires a peer attribute name here. store_input_data
    # inserts the requested literal default unit before this fallback is used.
    default_unit = "energy_to_power_ratio_min"

