from zen_garden.model.component_types.parameter import GenericParameter


class TransportLimitNet(GenericParameter):
    """
    Parameter to limit the net transport out of a region.
    """

    name = "transport_limit_net"
    indices = ("set_carriers", "set_nodes", "set_time_steps_yearly")
    description = (
        "Parameter which specifies the net transport limit out of the node "
        "over the course of a year"
    )
    unit_category = {"energy_quantity": 1}
    time_series = False
    default_value = "inf"
    default_unit = "availability_import_yearly"
