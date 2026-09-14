import os
import warnings
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
import yaml
from zen_garden import Results, compare_configs, compare_model_values


def compare_variables_results(
    test_model: str,
    results: Results,
    folder_path: str,
    test_variables_file_name: str,
):
    """
    Compares the variables of a Results object from the test run to precomputed
    values.

    Args:
        test_model: The model to test (name of the data set)
        results: The Results object
        folder_path: The path to the folder containing the file with the
            correct variables
        test_variables_file_name: The name of the file containing the correct
            variables
    """
    with open(os.path.join(folder_path, test_variables_file_name)) as f:
        test_variables = yaml.safe_load(f)
    failed_variables: defaultdict[str, dict[Any, Any]] = defaultdict(dict)
    compare_counter = 0
    if test_model in test_variables:
        for s in test_variables[test_model]:
            if s in results.scenarios:
                scenario = results.scenarios[s]
                test_values = test_variables[test_model][s]
                for c in test_values:
                    if c in scenario.components:
                        values = results.get_unprocessed_result(c, scenario_name=s)
                        assert isinstance(values, pd.Series)
                        for test_value in test_values[c]:
                            if isinstance(test_value["index"], list):
                                if len(test_value["index"]) == 1:
                                    test_index = test_value["index"][0]
                                else:
                                    test_index = tuple(test_value["index"])
                            else:
                                test_index = test_value["index"]
                            if test_index in values.index:
                                if not np.isclose(
                                    values[test_index], test_value["value"], rtol=1e-3
                                ):
                                    failed_variables[c][test_index] = {
                                        "computed_values": values[test_index],
                                        "test_value": test_value["value"],
                                    }
                                compare_counter += 1
                            else:
                                print(
                                    f"Index {test_value['index']} not found in "
                                    f"results for component {c}"
                                )
                    else:
                        print(f"Component {c} not found in results")
            else:
                print(f"Scenario {s} not found in results")
    assertion_string = ""
    for failed_var, failed_value in failed_variables.items():
        assertion_string += f"\n{failed_var}: {failed_value}"

    assert (
        len(failed_variables) == 0
    ), f"The variables {assertion_string} don't match their test values"
    if compare_counter == 0:
        warnings.warn(
            UserWarning(
                f"No variables have been compared in {test_model}. If not "
                f"intended, check the {test_variables_file_name} file."
            ),
            stacklevel=2,
        )


def check_get_total_get_full_ts(
    results: Results,
    specific_scenario=False,
    year=None,
    discount_to_first_step=True,
    get_doc=False,
):
    """Tests the Results methods get_total() and get_full_ts()."""
    test_variables = ["demand", "capacity", "storage_level", "capacity_limit"]
    scenario = None
    if specific_scenario:
        scenario = next(iter(results.scenarios.keys()))
    for test_variable in test_variables:
        results.get_total(test_variable, scenario_name=scenario, year=year)
        if test_variable != "capacity_limit":
            results.get_full_ts(
                test_variable,
                scenario_name=scenario,
                year=year,
                discount_to_first_step=discount_to_first_step,
            )
    if get_doc:
        results.get_doc(test_variables[0])


def check_comparison_functions(results: list[Results], scenarios: list[str]):
    """Tests the Results comparison functions."""
    compare_configs(results, scenarios)
    compare_model_values(results, component_type="parameter", scenarios=scenarios)
    compare_model_values(
        results, component_type="variable", scenarios=scenarios, compare_total=False
    )


def check_sectoral_costs_emissions(
    results: Results,
    scenario_name: str | None = None,
    spatially_resolved: bool = False,
):
    """Tests the Results methods get_sectoral_costs() and get_sectoral_emissions()."""
    costs, direct_costs = results.get_sectoral_costs(
        scenario_name=scenario_name,
        spatially_resolved=spatially_resolved,
        overwrite=True,
    )
    emissions, direct_emissions = results.get_sectoral_emissions(
        scenario_name=scenario_name,
        spatially_resolved=spatially_resolved,
        overwrite=True,
    )
    if "cost_total" in results.get_component_names("variable"):
        total_costs = results.get_total("cost_total", scenario_name=scenario_name)
        assert np.isclose(
            total_costs, costs.sum(), rtol=1e-3
        ).all(), "Total costs do not match the sum of sectoral costs"
    if "carbon_emissions_annual" in results.get_component_names("variable"):
        total_emissions = results.get_total(
            "carbon_emissions_annual", scenario_name=scenario_name
        )
        assert np.isclose(
            total_emissions, emissions.sum(), rtol=1e-3
        ).all(), "Total emissions do not match the sum of sectoral emissions"
