"""Tests for the standalone operation-scenarios wrapper."""

from __future__ import annotations

import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import yaml
from zen_garden import Results, run

from zen_garden_plugins.operation_scenarios import plugin, utils


@pytest.fixture
def operation_workspace(fixtures_path: str):
    """Yield an isolated workspace that is removed even after test failures."""
    with tempfile.TemporaryDirectory(prefix="zen-operation-test-") as directory:
        workspace = Path(directory)
        fixture_root = Path(fixtures_path)
        shutil.copy2(fixture_root / "config_operations.yaml", workspace / "config.yaml")
        yield workspace, fixture_root


def compare_historical_results(
    expected_name: str, results: Results, fixture_root: Path
) -> None:
    """Compare a historical case, treating omitted sparse zeros as zero."""
    expected_models = yaml.safe_load(
        (fixture_root / "operations_test_variables.yaml").read_text(encoding="utf-8")
    )
    expected_scenarios = expected_models[expected_name]
    for scenario_name, components in expected_scenarios.items():
        assert scenario_name in results.scenarios
        available_components = results.scenarios[scenario_name].components
        for component_name, expected_values in components.items():
            assert component_name in available_components
            values = results.get_unprocessed_result(
                component_name, scenario_name=scenario_name
            )
            assert isinstance(values, pd.Series)
            for expected in expected_values:
                raw_index = expected["index"]
                index = tuple(raw_index) if len(raw_index) > 1 else raw_index[0]
                actual = values[index] if index in values.index else 0.0
                assert np.isclose(actual, expected["value"], rtol=1e-3), (
                    f"{expected_name}.{scenario_name}.{component_name}{index}: "
                    f"expected {expected['value']}, got {actual}"
                )


@pytest.mark.parametrize("dataset_name", ["test_1j", "test_7b"])
def test_historical_operation_cases(
    operation_workspace: tuple[Path, Path], dataset_name: str
) -> None:
    """Preserve the planning and operation results of the legacy wrapper cases."""
    workspace, fixture_root = operation_workspace
    dataset = workspace / dataset_name
    outputs = workspace / "outputs"
    shutil.copytree(fixture_root / dataset_name, dataset)

    run(config=workspace / "config.yaml", dataset=dataset, folder_output=outputs)
    plugin.operation_scenarios(
        config=workspace / "config.yaml",
        dataset=dataset,
        folder_output=outputs,
        delete_data=True,
    )

    operation_name = f"{dataset_name}_none__operation"
    compare_historical_results(
        f"{dataset_name}_capacity",
        Results(outputs / dataset_name),
        fixture_root,
    )
    compare_historical_results(
        f"{dataset_name}_operation",
        Results(outputs / operation_name),
        fixture_root,
    )
    assert not (workspace / operation_name).exists()


def test_copy_dataset_installs_only_yaml_operational_scenarios(
    operation_workspace: tuple[Path, Path],
) -> None:
    """An operational copy drops planning scenarios and canonicalizes YAML."""
    workspace, fixture_root = operation_workspace
    source = workspace / "test_1j"
    destination = workspace / "test_1j_operation"
    shutil.copytree(fixture_root / "test_1j", source)
    (source / "scenarios.yaml").write_text("planning: {}\n", encoding="utf-8")
    scenarios_op = source / "scenarios_op.yml"
    scenarios_op.write_text("full_year:\n  system: {}\n", encoding="utf-8")

    utils.copy_dataset(source, destination, scenarios_op)

    assert yaml.safe_load((destination / "scenarios.yaml").read_text()) == {
        "full_year": {"system": {}}
    }
    assert not (destination / "scenarios.yml").exists()
    assert not (destination / "scenarios.json").exists()


def test_json_configuration_is_rejected(
    operation_workspace: tuple[Path, Path],
) -> None:
    """The wrapper does not silently fall back to legacy JSON inputs."""
    workspace, fixture_root = operation_workspace
    dataset = workspace / "test_1j"
    shutil.copytree(fixture_root / "test_1j", dataset)
    outputs = workspace / "outputs" / dataset.name
    outputs.mkdir(parents=True)
    json_config = workspace / "config.json"
    json_config.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a YAML file"):
        plugin.validate_inputs(dataset, json_config, outputs.parent, None, None)


def test_load_scenarios_applies_job_indices(monkeypatch: pytest.MonkeyPatch) -> None:
    """Planning scenarios are selected in result order."""

    class FakeResults:
        def __init__(self, _path: Path) -> None:
            self.scenarios = {"scenario_a": object(), "scenario_b": object()}

    monkeypatch.setattr(plugin, "Results", FakeResults)
    assert plugin.load_scenarios(Path("unused"), [1, 0]) == [
        "scenario_b",
        "scenario_a",
    ]


def test_delete_data_cleans_generated_dataset_after_failure(
    operation_workspace: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requested input cleanup runs even when the operational solve fails."""
    workspace, fixture_root = operation_workspace
    dataset = workspace / "test_1j"
    shutil.copytree(fixture_root / "test_1j", dataset)
    (workspace / "outputs" / dataset.name).mkdir(parents=True)
    generated = workspace / "test_1j_none__operation"

    monkeypatch.setattr(plugin, "load_scenarios", lambda *_args: ["none"])

    def fake_prepare(*_args: Any, **_kwargs: Any) -> None:
        generated.mkdir()

    def fail_run(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("deliberate failure")

    monkeypatch.setattr(plugin, "prepare_operational_dataset", fake_prepare)
    monkeypatch.setattr(plugin, "run_operational_simulation", fail_run)

    with pytest.raises(RuntimeError, match="deliberate failure"):
        plugin.operation_scenarios(
            dataset=dataset,
            config=workspace / "config.yaml",
            folder_output=workspace / "outputs",
            delete_data=True,
        )
    assert not generated.exists()


def test_cli_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """The console function forwards parsed options to the Python API."""
    received: dict[str, Any] = {}
    monkeypatch.setattr(
        plugin, "operation_scenarios", lambda **kwargs: received.update(kwargs)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "zen-operation",
            "--dataset",
            "dataset",
            "--config",
            "config.yaml",
            "--job_index",
            "2,0",
            "--scenarios_op",
            "scenarios_op.yaml",
            "--delete_data",
        ],
    )

    plugin.create_zen_operation_cli()

    assert received == {
        "dataset": "dataset",
        "config": "config.yaml",
        "folder_output": "./outputs",
        "job_index": [2, 0],
        "scenarios_op": "scenarios_op.yaml",
        "delete_data": True,
    }


def test_console_entry_point_is_declared() -> None:
    """Package metadata exposes the standalone command, not a runtime plugin."""
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    target = "zen_garden_plugins.operation_scenarios.plugin:create_zen_operation_cli"
    assert project["scripts"]["zen-operation"] == target
    assert "operation_scenarios" not in project["entry-points"]["zen_garden.plugins"]
