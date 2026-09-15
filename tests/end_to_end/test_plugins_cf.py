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


def test_cf_potential_limit(fixtures_cf_path):
    # run the test
    dataset_path = "C:/Users/funkec/Documents/GITHUB/01_Models/01_ZEN_universe/03_ZEN_data/Reg4Fuels"
    dataset_name = "Reg4Fuels_V15"
    run(
        config=os.path.join(dataset_path, "config.yaml"),
        dataset=os.path.join(dataset_path, dataset_name),
        folder_output=os.path.join(fixtures_cf_path, "outputs"),
    )
    # read the results and check again
    results = Results(os.path.join(fixtures_cf_path, "outputs", dataset_name))
    compare_variables_results(
        dataset_name, results, fixtures_cf_path, "test_variables_cf.yaml"
    )
