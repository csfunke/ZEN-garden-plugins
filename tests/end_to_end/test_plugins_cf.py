import os

from zen_garden import Results, run

from tests.end_to_end.utils.test_helpers import compare_variables_results


def test_cf_net_import(fixtures_cf_path):
    # run the test
    data_set_name = "test_cf_net_import"
    run(
        config=os.path.join(fixtures_cf_path, "config_test_cf_net_import.yaml"),
        dataset=os.path.join(fixtures_cf_path, data_set_name),
        folder_output=os.path.join(fixtures_cf_path, "outputs"),
    )
    # read the results and check again
    results = Results(os.path.join(fixtures_cf_path, "outputs", data_set_name))
    compare_variables_results(
        data_set_name, results, fixtures_cf_path, "test_variables_cf.yaml"
    )