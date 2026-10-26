"""Recurring intra-year storage-state constraint."""

import logging
import math
from collections.abc import Hashable
from typing import Any

import numpy as np
import xarray as xr
from linopy.expressions import LinearExpression
from linopy.variables import Variable
from zen_garden.model.component_types.constraint import GenericConstraint

logger = logging.getLogger(__name__)

Expression = LinearExpression | Variable


class RecurringStoragePeriodicityConstraint(GenericConstraint):
    """Equate storage states at fixed elapsed-hour boundaries within each year."""

    constraint_name = "constraint_recurring_storage_periodicity"

    @classmethod
    def build(cls, model_constructor: Any) -> None:
        """Construct technology-specific intra-year periodicity constraints.

        Args:
            model_constructor: Active storage-technology model constructor.
        """
        model = model_constructor.optimization_model
        technologies = list(model.sets["set_storage_technologies"])
        if not technologies:
            return

        periods = model.parameters.storage_periodicity_hrs
        enabled = {
            technology: cls._validated_period(
                periods.sel(set_storage_technologies=technology).item(), technology
            )
            for technology in technologies
            if periods.sel(set_storage_technologies=technology).item() != 0.0
        }
        if not enabled:
            return

        if not model_constructor.config.system.storage_periodicity:
            logger.warning(
                "Ignoring storage_periodicity_hrs for %s because "
                "system.storage_periodicity is false.",
                ", ".join(map(str, enabled)),
            )
            return

        constraints: dict[tuple[Hashable, Hashable, int], Any] = {}
        for technology, period in enabled.items():
            for year in model.sets["set_years"]:
                year_positions = cls._year_positions(model_constructor, year)
                year_length = len(year_positions)
                if period >= year_length:
                    continue
                initial_state = cls._year_initial_state(
                    model_constructor, technology, year_positions
                )
                for elapsed_hours in range(period, year_length, period):
                    state = cls._state_at_boundary(
                        model_constructor,
                        technology,
                        year,
                        year_positions,
                        elapsed_hours,
                    )
                    valid = cls._valid_nodes(initial_state, state)
                    constraint = state - initial_state == xr.where(valid, 0.0, np.nan)
                    constraints[(technology, year, elapsed_hours)] = constraint

        cls.add_constraint(
            model_constructor,
            cls.constraint_name,
            constraints,
            doc=(
                "Storage state equals its year-start state at each configured "
                "intra-year hour boundary"
            ),
        )

    @staticmethod
    def _validated_period(value: float, technology: Hashable) -> int:
        """Return a valid whole-hour period.

        Args:
            value: Period converted to ZEN-garden's base time unit.
            technology: Technology name used in validation errors.

        Returns:
            Positive period as an integer number of hours.

        Raises:
            ValueError: If the enabled value is not a positive whole number.
        """
        if not math.isfinite(value) or value <= 0 or not float(value).is_integer():
            raise ValueError(
                "storage_periodicity_hrs for storage technology "
                f"{technology!r} must be zero or a positive whole number of "
                f"hours; received {value!r}."
            )
        return int(value)

    @staticmethod
    def _year_positions(model_constructor: Any, year: Hashable) -> np.ndarray:
        """Return physical-hour positions belonging to one modeled year."""
        sequence_years = np.asarray(
            model_constructor.time_steps.sequence_time_steps_yearly
        )
        positions = np.flatnonzero(sequence_years == year)
        if positions.size == 0:
            raise ValueError(f"Modeled year {year!r} has no physical time steps.")
        if positions.size > 1 and np.any(np.diff(positions) != 1):
            raise ValueError(
                f"Physical time steps for modeled year {year!r} are not contiguous."
            )
        return positions

    @staticmethod
    def _year_initial_state(
        model_constructor: Any,
        technology: Hashable,
        year_positions: np.ndarray,
    ) -> Variable:
        """Return the cyclic state immediately before the year's first hour."""
        storage_sequence = np.asarray(
            model_constructor.time_steps.sequence_time_steps_storage
        )
        final_storage_step = storage_sequence[year_positions[-1]]
        return model_constructor.optimization_model.variables["storage_level"].sel(
            set_storage_technologies=technology,
            set_time_steps_storage=final_storage_step,
        )

    @classmethod
    def _state_at_boundary(
        cls,
        model_constructor: Any,
        technology: Hashable,
        year: Hashable,
        year_positions: np.ndarray,
        elapsed_hours: int,
    ) -> Expression:
        """Return the state after exactly ``elapsed_hours`` in a year."""
        position = int(year_positions[elapsed_hours - 1])
        storage_sequence = np.asarray(
            model_constructor.time_steps.sequence_time_steps_storage
        )
        storage_step = storage_sequence[position]
        at_block_end = (
            position == len(storage_sequence) - 1
            or storage_sequence[position + 1] != storage_step
        )
        if at_block_end:
            return model_constructor.optimization_model.variables["storage_level"].sel(
                set_storage_technologies=technology,
                set_time_steps_storage=storage_step,
            )

        block_start = position
        while block_start > 0 and storage_sequence[block_start - 1] == storage_step:
            block_start -= 1
        hours_in_block = position - block_start + 1
        previous_position = block_start - 1
        if previous_position < int(year_positions[0]):
            previous_position = int(year_positions[-1])
        previous_storage_step = storage_sequence[previous_position]
        return cls._reconstructed_state(
            model_constructor,
            technology,
            year,
            storage_step,
            previous_storage_step,
            hours_in_block,
        )

    @staticmethod
    def _reconstructed_state(
        model_constructor: Any,
        technology: Hashable,
        year: Hashable,
        storage_step: Hashable,
        previous_storage_step: Hashable,
        elapsed_hours: int,
    ) -> LinearExpression:
        """Reconstruct an intermediate state inside an aggregated storage block."""
        model = model_constructor.optimization_model
        previous_state = model.variables["storage_level"].sel(
            set_storage_technologies=technology,
            set_time_steps_storage=previous_storage_step,
        )
        operation_step = model_constructor.time_steps.convert_time_step_energy2power(
            storage_step
        )
        self_discharge = model.parameters.self_discharge.sel(
            set_storage_technologies=technology
        )
        retention = 1.0 - self_discharge
        retained_state = previous_state * retention**elapsed_hours

        efficiency_charge = model.parameters.efficiency_charge.sel(
            set_storage_technologies=technology,
            set_years=year,
        )
        efficiency_discharge = model.parameters.efficiency_discharge.sel(
            set_storage_technologies=technology,
            set_years=year,
        )
        net_flow = (
            model.variables["flow_storage_charge"].sel(
                set_storage_technologies=technology,
                set_time_steps_operation=operation_step,
            )
            * efficiency_charge
            - model.variables["flow_storage_discharge"]
            .sel(
                set_storage_technologies=technology,
                set_time_steps_operation=operation_step,
            )
            .to_linexpr()
            / efficiency_discharge
            + model.parameters.flow_storage_inflow.sel(
                set_storage_technologies=technology,
                set_time_steps_operation=operation_step,
            )
            - model.variables["flow_storage_spillage"].sel(
                set_storage_technologies=technology,
                set_time_steps_operation=operation_step,
            )
        )
        nonzero_self_discharge = self_discharge != 0
        safe_self_discharge = self_discharge.where(nonzero_self_discharge, 1.0)
        geometric_sum = ((1.0 - retention**elapsed_hours) / safe_self_discharge).where(
            nonzero_self_discharge,
            float(elapsed_hours),
        )
        return retained_state + net_flow * geometric_sum

    @staticmethod
    def _valid_nodes(initial_state: Variable, state: Expression) -> xr.DataArray:
        """Return nodes for which both boundary expressions contain variables."""
        initial_valid = initial_state.labels >= 0
        if isinstance(state, Variable):
            return initial_valid & (state.labels >= 0)
        return initial_valid & (state.vars >= 0).any("_term")
