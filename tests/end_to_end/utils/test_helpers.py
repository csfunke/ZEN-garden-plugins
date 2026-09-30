import os
import warnings
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
import yaml
from zen_garden import Results


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
