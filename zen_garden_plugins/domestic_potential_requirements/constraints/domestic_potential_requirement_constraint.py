import numpy as np
import xarray as xr
from linopy import merge
from zen_garden.model.component_types.constraint import GenericConstraint


class DomesticPotentialRequirementConstraint(GenericConstraint):
    """Ensure winter generation potential covers domestic demand."""

    @classmethod
    def build(cls, model_constructor):
        optimization_model = model_constructor.optimization_model
        parameters = optimization_model.parameters
        variables = optimization_model.variables
        times = parameters.max_load.coords["set_time_steps_operation"]
        year_time_step_duration = cls.get_year_time_step_duration_array(
            model_constructor
        )
        winter_duration = cls._get_winter_representative_durations(
            model_constructor, times, year_time_step_duration
        )

        carriers = parameters.demand.coords["set_carriers"]
        nodes = parameters.demand.coords["set_nodes"]
        conversion_technologies = optimization_model.sets["set_conversion_technologies"]
        storage_technologies = optimization_model.sets["set_storage_technologies"]
        potential_terms = []
        demand_terms = []
        time_step_year = xr.DataArray(
            [
                model_constructor.time_steps.convert_time_step_operation2year(t)
                for t in times.data
            ],
            coords=[times],
        )
        for carrier in carriers.data:
            output_technologies = [
                technology
                for technology in conversion_technologies
                if carrier in optimization_model.sets["set_output_carriers"][technology]
            ]
            storage_for_carrier = [
                technology
                for technology in storage_technologies
                if carrier
                in optimization_model.sets["set_reference_carriers"][technology]
            ]
            if output_technologies:
                capacity_potential = (
                    parameters.max_load.loc[output_technologies, nodes, :]
                    * variables["capacity"].loc[
                        output_technologies, "power", nodes, time_step_year
                    ]
                )
                # The dimensions intentionally differ: winter_duration is zero for
                # operational time steps that do not belong to a given year.
                capacity_potential = (capacity_potential * winter_duration).sum(
                    "set_time_steps_operation"
                )
                capacity_potential = capacity_potential.sum("set_technologies")
            else:
                zero_by_node_and_year = xr.DataArray(
                    0.0,
                    dims=["set_nodes", "set_years"],
                    coords={
                        "set_nodes": nodes.data,
                        "set_years": winter_duration.coords["set_years"].data,
                    },
                )
                capacity_potential = optimization_model.lp_model.linexpr(
                    zero_by_node_and_year
                )

            if storage_for_carrier:
                inflow_potential = parameters.flow_storage_inflow.loc[
                    storage_for_carrier, nodes, :
                ]
                inflow_potential = (inflow_potential * winter_duration).sum(
                    "set_time_steps_operation"
                )
                inflow_potential = inflow_potential.sum("set_storage_technologies")

                initial_storage_terms = []
                for year in optimization_model.sets["set_years"]:
                    initial_storage_time = cls._get_winter_start_storage_time(
                        model_constructor, year
                    )
                    initial_storage_terms.append(
                        variables["storage_level"]
                        .loc[storage_for_carrier, nodes, initial_storage_time]
                        .sum("set_storage_technologies")
                        .expand_dims(set_years=[year])
                    )
                initial_storage = merge(initial_storage_terms, dim="set_years")
            else:
                inflow_potential = capacity_potential * 0
                initial_storage = capacity_potential * 0

            potential_terms.append(
                (capacity_potential + inflow_potential + initial_storage).expand_dims(
                    set_carriers=[carrier]
                )
            )
            demand_terms.append(
                (parameters.demand.loc[carrier, nodes, :] * winter_duration)
                .sum("set_time_steps_operation")
                .expand_dims(set_carriers=[carrier])
            )

        potential = merge(potential_terms, dim="set_carriers")
        demand = xr.concat(demand_terms, dim="set_carriers")
        winter_limit = parameters.winter_limit
        backup_potential = parameters.backup_potential
        active_constraint = np.isfinite(winter_limit) & np.isfinite(backup_potential)
        lhs = potential.where(active_constraint)
        rhs = (demand - winter_limit - backup_potential).where(active_constraint)
        optimization_model.add_constraint(
            "constraint_domestic_potential_requirement", lhs >= rhs
        )

    @staticmethod
    def _get_winter_representative_durations(
        model_constructor, representative_times, year_time_step_duration
    ):
        """Return the winter duration of each representative hour per model year.

        A representative hour can stand for both winter and non-winter hours. Its
        winter duration is therefore the number of its occurrences that fall in
        winter, rather than its full annual duration or a Boolean winter mask.
        """
        sequence_time_steps = model_constructor.time_steps.sequence_time_steps_operation
        sequence_years = model_constructor.time_steps.sequence_time_steps_yearly
        operation_time_dimension = representative_times.dims[0]
        config = model_constructor.model_schema.config.plugins[
            "domestic_potential_requirements"
        ]
        start_hour = config["start_hour"]
        end_hour = config["end_hour"]

        if sequence_time_steps is None or sequence_years is None:
            raise RuntimeError("The code for this feature has not been tested yet")

        sequence_time_steps = np.asarray(sequence_time_steps)
        sequence_years = np.asarray(sequence_years)
        years = year_time_step_duration.coords["set_years"]
        durations = np.zeros((len(years), len(representative_times)), dtype=float)

        for year_index, year in enumerate(years.data):
            year_sequence = sequence_time_steps[sequence_years == year]
            hours = np.arange(len(year_sequence))
            assert len(hours) == 8760, "The number of hours in a year should be 8760."
            if start_hour <= end_hour:
                actual_winter = (hours >= start_hour) & (hours < end_hour)
            else:
                actual_winter = (hours >= start_hour) | (hours < end_hour)
            winter_times, winter_counts = np.unique(
                year_sequence[actual_winter], return_counts=True
            )
            counts_by_time = dict(zip(winter_times, winter_counts, strict=True))
            durations[year_index] = [
                counts_by_time.get(time, 0) for time in representative_times.data
            ]

        return xr.DataArray(
            durations,
            dims=["set_years", operation_time_dimension],
            coords={
                "set_years": years,
                operation_time_dimension: representative_times,
            },
        )

    @staticmethod
    def _get_winter_start_storage_time(model_constructor, year):
        """Return the storage time step at the configured winter start hour."""

        time_steps = model_constructor.time_steps
        sequence_storage = time_steps.sequence_time_steps_storage
        sequence_years = time_steps.sequence_time_steps_yearly
        if sequence_storage is None or sequence_years is None:
            raise RuntimeError("Storage sequences are required to locate winter start")

        year_positions = np.flatnonzero(np.asarray(sequence_years) == year)
        if not len(year_positions):
            raise ValueError(f"No operational hours found for year {year}.")
        config = model_constructor.model_schema.config.plugins[
            "domestic_potential_requirements"
        ]
        start_hour = config["start_hour"]
        if not 0 <= start_hour < len(year_positions):
            raise ValueError(
                f"start_hour {start_hour} is outside year {year}, which has "
                f"{len(year_positions)} hours."
            )
        return np.asarray(sequence_storage)[year_positions[start_hour]]
