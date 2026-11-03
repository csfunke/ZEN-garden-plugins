"""Run operation-only models from completed capacity-expansion results.

This module is packaged alongside ZEN-garden plugins, but it is deliberately a
standalone extension. It is invoked through the ``zen-operation`` command or
the :func:`operation_scenarios` Python API and is not registered with
``zen_garden.plugins``.
"""

from __future__ import annotations

import argparse
import os
import shutil
from collections.abc import Iterable
from pathlib import Path

from zen_garden import Results, run

from zen_garden_plugins.operation_scenarios import utils


def _require_yaml_file(path: Path, description: str) -> Path:
    """Validate that an existing path is a YAML file."""
    if path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(f"{description} must be a YAML file: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"{description} not found: {path}")
    return path


def validate_inputs(
    dataset: Path | str,
    config: Path | str,
    folder_output: Path | str | None,
    job_index: Iterable[int] | None,
    scenarios_op: Path | str | None,
) -> tuple[Path, Path, Path, list[int] | None, Path | None]:
    """Validate and normalize wrapper inputs.

    Args:
        dataset: Capacity-expansion dataset directory.
        config: ZEN-garden YAML configuration file.
        folder_output: Directory containing the completed planning results.
        job_index: Optional planning-scenario indices to process.
        scenarios_op: Optional operational-scenario YAML file.

    Returns:
        Normalized dataset, config, output directory, job indices, and
        operational-scenario file.

    Raises:
        FileNotFoundError: If an input or the planning results do not exist.
        TypeError: If a job index is not an integer.
        ValueError: If a required configuration file is not YAML.
    """
    dataset_path = Path(dataset).resolve()
    if not dataset_path.is_dir():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    utils.validate_yaml_dataset(dataset_path)

    config_path = _require_yaml_file(Path(config).resolve(), "Config")
    output_path = Path(folder_output or "./outputs").resolve()
    results_path = output_path / dataset_path.name
    if not results_path.is_dir():
        raise FileNotFoundError(
            f"Results for dataset {dataset_path.name!r} do not exist in "
            f"{output_path}."
        )

    if job_index is None:
        job_indices = None
    else:
        job_indices = list(job_index)
        if not all(isinstance(index, int) for index in job_indices):
            raise TypeError("job_index must be an iterable of integers")

    scenario_path = None
    if scenarios_op is not None:
        candidate = Path(scenarios_op)
        if not candidate.is_absolute():
            candidate = dataset_path / candidate
        scenario_path = _require_yaml_file(candidate.resolve(), "Operational scenarios")
        utils.load_yaml_mapping(scenario_path)

    return dataset_path, config_path, output_path, job_indices, scenario_path


def load_scenarios(results_path: Path, job_index: list[int] | None) -> list[str]:
    """Return selected planning-scenario names from completed results."""
    scenarios = list(Results(results_path).scenarios)
    if not scenarios:
        raise ValueError("No scenarios found in simulation results")
    if job_index:
        try:
            return [scenarios[index] for index in job_index]
        except IndexError as exc:
            raise IndexError(
                f"job_index contains an index outside 0..{len(scenarios) - 1}"
            ) from exc
    return scenarios


def _operation_dataset_path(dataset: Path, scenario: str) -> Path:
    """Build and validate the generated sibling dataset path."""
    if Path(scenario).name != scenario or scenario in {".", ".."}:
        raise ValueError(f"Unsafe scenario name in results: {scenario!r}")
    path = dataset.parent / f"{dataset.name}_{scenario}__operation"
    if path.parent.resolve() != dataset.parent.resolve():
        raise ValueError(f"Unsafe operational dataset path: {path}")
    return path


def prepare_operational_dataset(
    dataset: Path,
    dataset_op: Path,
    planning_results: Path,
    scenario: str,
    scenarios_op: Path | None,
) -> None:
    """Create an operation-only dataset for one planning scenario."""
    utils.copy_dataset(dataset, dataset_op, scenarios_op)
    utils.capacity_addition_to_existing_capacity(
        planning_results, dataset, dataset_op, scenario
    )
    system_path = utils.find_yaml_file(dataset_op, "system")
    utils.modify_yaml(
        system_path,
        {
            "allow_investment": False,
            "conduct_scenario_analysis": scenarios_op is not None,
        },
    )


def run_operational_simulation(
    dataset_op: Path,
    config: Path,
    folder_output: Path,
) -> None:
    """Run ZEN-garden for a prepared operation-only dataset."""
    run(dataset=dataset_op, config=config, folder_output=folder_output)


def operation_scenarios(
    dataset: Path | str,
    config: Path | str = Path("./config.yaml"),
    folder_output: Path | str = Path("./outputs"),
    job_index: Iterable[int] | None = None,
    scenarios_op: Path | str | None = None,
    delete_data: bool = False,
) -> None:
    """Run operation-only models derived from capacity-expansion results.

    For every selected planning scenario, the wrapper creates a sibling copy
    of the input dataset, transfers optimized capacity additions to existing
    capacity files, disables investment, and runs ZEN-garden again.

    Args:
        dataset: Dataset used for the completed capacity-expansion run.
        config: YAML configuration used for the operation-only run.
        folder_output: Directory containing planning results and receiving
            operation-only results.
        job_index: Optional planning-scenario indices. All are run by default.
        scenarios_op: Optional YAML file containing operational scenarios. A
            relative path is resolved within ``dataset``.
        delete_data: Permanently delete generated input datasets after each
            run. Cleanup also occurs when an operational run fails.
    """
    (
        dataset_path,
        config_path,
        output_path,
        job_indices,
        scenario_path,
    ) = validate_inputs(dataset, config, folder_output, job_index, scenarios_op)
    planning_results = output_path / dataset_path.name

    for scenario in load_scenarios(planning_results, job_indices):
        dataset_op = _operation_dataset_path(dataset_path, scenario)
        try:
            prepare_operational_dataset(
                dataset_path,
                dataset_op,
                planning_results,
                scenario,
                scenario_path,
            )
            run_operational_simulation(dataset_op, config_path, output_path)
        finally:
            if delete_data and dataset_op.exists():
                shutil.rmtree(dataset_op)


def resolve_job_index(job_index: str | None, job_index_var: str) -> list[int] | None:
    """Resolve comma-separated or environment-provided scenario indices."""
    value = job_index if job_index is not None else os.environ.get(job_index_var)
    if value is None or value == "":
        return None
    return [int(index.strip()) for index in value.split(",")]


def build_parser() -> argparse.ArgumentParser:
    """Build the ``zen-operation`` command-line parser."""
    parser = argparse.ArgumentParser(
        prog="zen-operation",
        description=(
            "Run operation-only scenarios from completed ZEN-garden "
            "capacity-expansion results."
        ),
    )
    parser.add_argument("--dataset", required=True, help="Planning dataset path.")
    parser.add_argument("--config", default="./config.yaml", help="YAML config path.")
    parser.add_argument(
        "--folder_output",
        default="./outputs",
        help="Planning and operational results directory.",
    )
    parser.add_argument(
        "--job_index", default=None, help="Comma-separated planning-scenario indices."
    )
    parser.add_argument(
        "--job_index_var",
        default="SLURM_ARRAY_TASK_ID",
        help="Environment variable used when --job_index is omitted.",
    )
    parser.add_argument(
        "--scenarios_op",
        default=None,
        help="Operational-scenario YAML file, relative to the dataset by default.",
    )
    parser.add_argument(
        "--delete_data",
        action="store_true",
        help="Delete generated operation-only input datasets after each run.",
    )
    return parser


def create_zen_operation_cli() -> None:
    """Run :func:`operation_scenarios` from command-line arguments."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        job_index = resolve_job_index(args.job_index, args.job_index_var)
    except ValueError as exc:
        parser.error(f"Invalid job index: {exc}")
    operation_scenarios(
        dataset=args.dataset,
        config=args.config,
        folder_output=args.folder_output,
        job_index=job_index,
        scenarios_op=args.scenarios_op,
        delete_data=args.delete_data,
    )


if __name__ == "__main__":
    create_zen_operation_cli()
