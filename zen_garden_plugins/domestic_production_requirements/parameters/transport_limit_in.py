from zen_garden.model.component_types.parameter import GenericParameter


class TransportLimitIn(GenericParameter):
    """
    Parameter to limit the transport in to a region.
    """

    name = "transport_limit_in"
    indices = ("set_carriers", "set_nodes", "set_time_steps_yearly")
    description = (
        "Parameter which specifies the net transport limit in to the "
        "node over the course of a year"
    )
    unit_category = {"energy_quantity": 1}
    time_series = False
    default_value = "inf"
    default_unit = "availability_import_yearly"
