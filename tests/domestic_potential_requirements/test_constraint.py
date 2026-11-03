from types import SimpleNamespace

import numpy as np
import xarray as xr

from zen_garden_plugins.domestic_potential_requirements.constraints import (
    DomesticPotentialRequirementConstraint,
)


def model_constructor_with_config(time_steps, start_hour=8016, end_hour=1416):
    return SimpleNamespace(
        time_steps=time_steps,
        model_schema=SimpleNamespace(
            config=SimpleNamespace(
                plugins={
                    "domestic_potential_requirements": {
                        "start_hour": start_hour,
                        "end_hour": end_hour,
                    }
                }
            )
        ),
    )


def test_winter_durations_count_only_winter_occurrences():
    representative_times = xr.DataArray(
        [10, 20],
        dims="set_time_steps_operation",
        coords={"set_time_steps_operation": [10, 20]},
    )
    years = xr.DataArray([0], dims="set_years", coords={"set_years": [0]})
    sequence = np.full(8760, 20)
    sequence[:1000] = 10
    sequence[2000:3000] = 10

    model_constructor = model_constructor_with_config(
        SimpleNamespace(
            sequence_time_steps_operation=sequence,
            sequence_time_steps_yearly=np.zeros(8760, dtype=int),
        )
    )

    year_time_step_duration = xr.DataArray(
        [[2000, 6760]],
        dims=["set_years", "set_time_steps_operation"],
        coords={"set_years": years, "set_time_steps_operation": representative_times},
    )
    durations = (
        DomesticPotentialRequirementConstraint._get_winter_representative_durations(
            model_constructor, representative_times, year_time_step_duration
        )
    )

    assert durations.sel(set_years=0, set_time_steps_operation=10).item() == 1000
    assert durations.sel(set_years=0, set_time_steps_operation=20).item() == 1160


def test_winter_durations_are_calculated_per_year():
    representative_times = xr.DataArray(
        [10, 20],
        dims="set_time_steps_operation",
        coords={"set_time_steps_operation": [10, 20]},
    )
    years = xr.DataArray([0, 1], dims="set_years", coords={"set_years": [0, 1]})
    sequence = np.concatenate((np.full(8760, 10), np.full(8760, 20)))
    sequence_years = np.repeat([0, 1], 8760)

    model_constructor = model_constructor_with_config(
        SimpleNamespace(
            sequence_time_steps_operation=sequence,
            sequence_time_steps_yearly=sequence_years,
        )
    )

    year_time_step_duration = xr.DataArray(
        [[8760, 0], [0, 8760]],
        dims=["set_years", "set_time_steps_operation"],
        coords={"set_years": years, "set_time_steps_operation": representative_times},
    )
    durations = (
        DomesticPotentialRequirementConstraint._get_winter_representative_durations(
            model_constructor, representative_times, year_time_step_duration
        )
    )

    assert durations.sel(set_years=0, set_time_steps_operation=10).item() == 2160
    assert durations.sel(set_years=0, set_time_steps_operation=20).item() == 0
    assert durations.sel(set_years=1, set_time_steps_operation=10).item() == 0
    assert durations.sel(set_years=1, set_time_steps_operation=20).item() == 2160


def test_winter_durations_use_plugin_start_and_end_hours():
    representative_times = xr.DataArray(
        [10, 20],
        dims="set_time_steps_operation",
        coords={"set_time_steps_operation": [10, 20]},
    )
    years = xr.DataArray([0], dims="set_years", coords={"set_years": [0]})
    sequence = np.full(8760, 20)
    sequence[:150] = 10
    model_constructor = model_constructor_with_config(
        SimpleNamespace(
            sequence_time_steps_operation=sequence,
            sequence_time_steps_yearly=np.zeros(8760, dtype=int),
        ),
        start_hour=100,
        end_hour=200,
    )
    year_time_step_duration = xr.DataArray(
        [[150, 8610]],
        dims=["set_years", "set_time_steps_operation"],
        coords={"set_years": years, "set_time_steps_operation": representative_times},
    )

    durations = (
        DomesticPotentialRequirementConstraint._get_winter_representative_durations(
            model_constructor, representative_times, year_time_step_duration
        )
    )

    assert durations.sel(set_years=0, set_time_steps_operation=10).item() == 50
    assert durations.sel(set_years=0, set_time_steps_operation=20).item() == 50


def test_initial_storage_uses_storage_step_at_winter_start():
    model_constructor = model_constructor_with_config(
        SimpleNamespace(
            sequence_time_steps_storage=np.array([7, 3, 9, 2]),
            sequence_time_steps_yearly=np.array([0, 0, 1, 1]),
            get_time_steps_year2storage=lambda year: np.array([2, 9]),
        ),
        start_hour=1,
    )

    storage_time = (
        DomesticPotentialRequirementConstraint._get_winter_start_storage_time(
            model_constructor, 1
        )
    )

    assert storage_time == 2
