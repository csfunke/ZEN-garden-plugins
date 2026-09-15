from zen_garden.model.component_types.parameter import GenericParameter


class WinterLimit(GenericParameter):
    """
    Parameter to limit the transport in to a region.
    """

    name = "winter_limit"
    indices = ("set_carriers", "set_nodes", "set_years")
    doc = (
        "Parameter which specifies the maximum difference between demand"
        "and domestic generation potential in the node over the course of"
        "of a year."
    )
    unit_category = {"energy_quantity": 1}
    time_series = False
    default_value = "inf"
    default_unit = "availability_import_yearly"
