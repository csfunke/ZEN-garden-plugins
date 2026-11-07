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
    planning_results: Path | str,
    planning_scenario: str,
    config: Path | str,
    folder_output: Path | str | None,
    job_index: Iterable[int] | None,
) -> tuple[Path, Path, str, Path, Path, list[int] | None]:
    """Validate and normalize wrapper inputs.

    Args:
        dataset: Operational input dataset directory.
        planning_results: Completed capacity-expansion results directory.
        planning_scenario: Planning scenario whose capacities should be used.
        config: ZEN-garden YAML configuration file.
        folder_output: Directory receiving the operation-only results.
        job_index: Optional operational-scenario indices to process.

    Returns:
        Normalized dataset, planning results, planning scenario, config, output
        directory, and operational-scenario indices.

    Raises:
        FileNotFoundError: If an input or the planning results do not exist.
        TypeError: If a job index is not an integer.
        ValueError: If a required configuration file is not YAML or the planning
            scenario does not exist.
    """
    dataset_path = Path(dataset).resolve()
    if not dataset_path.is_dir():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    utils.validate_yaml_dataset(dataset_path)

    config_path = _require_yaml_file(Path(config).resolve(), "Config")
    output_path = Path(folder_output or "./outputs").resolve()

    results_path = Path(planning_results).resolve()
    if not results_path.is_dir():
        raise FileNotFoundError(f"Planning results not found: {results_path}")
    available_scenarios = list(Results(results_path).scenarios)
    if planning_scenario not in available_scenarios:
        available = ", ".join(repr(scenario) for scenario in available_scenarios)
        raise ValueError(
            f"Planning scenario {planning_scenario!r} not found in {results_path}. "
            f"Available scenarios: {available or 'none'}"
        )

    if job_index is None:
        job_indices = None
    else:
        job_indices = list(job_index)
        if not all(isinstance(index, int) for index in job_indices):
            raise TypeError("job_index must be an iterable of integers")

    return (
        dataset_path,
        results_path,
        planning_scenario,
        config_path,
        output_path,
        job_indices,
    )


def _operation_dataset_path(
    dataset: Path, planning_results: Path, scenario: str
) -> Path:
    """Build and validate the generated sibling dataset path."""
    if Path(scenario).name != scenario or scenario in {".", ".."}:
        raise ValueError(f"Unsafe scenario name in results: {scenario!r}")
    planning_dataset = planning_results.name
    if not planning_dataset:
        raise ValueError(
            f"Planning results must identify a dataset directory: {planning_results}"
        )
    path = dataset.parent / (
        f"{dataset.name}--{planning_dataset}-{scenario}__operation"
    )
    if path.parent.resolve() != dataset.parent.resolve():
        raise ValueError(f"Unsafe operational dataset path: {path}")
    return path


def prepare_operational_dataset(
    dataset: Path,
    dataset_op: Path,
    planning_results: Path,
    scenario: str,
) -> None:
    """Create an operation-only dataset for one planning scenario."""
    utils.copy_dataset(dataset, dataset_op)
    utils.capacity_addition_to_existing_capacity(
        planning_results, dataset, dataset_op, scenario
    )
    system_path = utils.find_yaml_file(dataset_op, "system")
    utils.modify_yaml(
        system_path,
        {"allow_investment": False},
    )


def run_operational_simulation(
    dataset_op: Path,
    config: Path,
    folder_output: Path,
    job_index: list[int] | None,
) -> None:
    """Run ZEN-garden for a prepared operation-only dataset."""
    run(
        dataset=dataset_op,
        config=config,
        folder_output=folder_output,
        job_index=job_index,
    )


def operation_scenarios(
    dataset: Path | str,
    planning_results: Path | str,
    planning_scenario: str,
    config: Path | str = Path("./config.yaml"),
    folder_output: Path | str = Path("./outputs"),
    job_index: Iterable[int] | None = None,
    delete_data: bool = False,
) -> None:
    """Run operation-only models derived from capacity-expansion results.

    The wrapper creates a sibling copy of the operational input dataset,
    transfers optimized capacity additions from the selected planning scenario
    to existing-capacity files, disables investment, and runs ZEN-garden again.

    Args:
        dataset: Operational input dataset to copy and augment.
        planning_results: Completed capacity-expansion results directory.
        planning_scenario: Planning scenario whose capacities should be used.
        config: YAML configuration used for the operation-only run.
        folder_output: Directory receiving operation-only results.
        job_index: Optional operational-scenario indices from the dataset's
            scenario definition. All are run by default.
        delete_data: Permanently delete generated input datasets after each
            run. Cleanup also occurs when an operational run fails.
    """
    (
        dataset_path,
        results_path,
        selected_scenario,
        config_path,
        output_path,
        job_indices,
    ) = validate_inputs(
        dataset,
        planning_results,
        planning_scenario,
        config,
        folder_output,
        job_index,
    )

    dataset_op = _operation_dataset_path(dataset_path, results_path, selected_scenario)
    try:
        prepare_operational_dataset(
            dataset_path,
            dataset_op,
            results_path,
            selected_scenario,
        )
        run_operational_simulation(dataset_op, config_path, output_path, job_indices)
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
    parser.add_argument(
        "--dataset", required=True, help="Operational input dataset path."
    )
    parser.add_argument(
        "--planning_results",
        required=True,
        help="Completed capacity-expansion results directory.",
    )
    parser.add_argument(
        "--planning_scenario",
        required=True,
        help="Planning scenario whose capacities should be used.",
    )
    parser.add_argument("--config", default="./config.yaml", help="YAML config path.")
    parser.add_argument(
        "--folder_output",
        default="./outputs",
        help="Operational results directory.",
    )
    parser.add_argument(
        "--job_index",
        default=None,
        help="Comma-separated operational-scenario indices.",
    )
    parser.add_argument(
        "--job_index_var",
        default="SLURM_ARRAY_TASK_ID",
        help="Environment variable used when --job_index is omitted.",
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
        planning_results=args.planning_results,
        planning_scenario=args.planning_scenario,
        config=args.config,
        folder_output=args.folder_output,
        job_index=job_index,
        delete_data=args.delete_data,
    )


if __name__ == "__main__":
    create_zen_operation_cli()
