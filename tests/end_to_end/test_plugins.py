import os

from zen_garden import Results, run

from tests.end_to_end.utils.test_helpers import (
    check_get_total_get_full_ts,
    check_sectoral_costs_emissions,
    compare_variables_results,
)


# All the tests
###############
def test_1a(fixtures_path):
    # add duals for this test

    # test also whether config and dataset can take just file name in cwd
    cwd = os.getcwd()
    os.chdir(fixtures_path)
    try:
        # run the test
        data_set_name = "test_1a"
        run(
            config="config_duals.yaml",
            dataset=data_set_name,
        )

        # read the results and check again
        res = Results(os.path.join("outputs", data_set_name))
        compare_variables_results(
            data_set_name, res, fixtures_path, "test_variables.yaml"
        )
        # test functions get_total() and get_full_ts()
        check_get_total_get_full_ts(res)
        # test sectoral costs and emissions
        check_sectoral_costs_emissions(res, spatially_resolved=True)
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    testcase_folder = os.path.join(os.path.dirname(__file__), "fixtures")
    test_1a(testcase_folder)
