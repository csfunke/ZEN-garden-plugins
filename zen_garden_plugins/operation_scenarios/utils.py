"""Dataset and result helpers for operation-only simulations."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from zen_garden import Results
from zen_garden.input.unit_converter import UnitConverter


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML mapping with contextual validation errors."""
    if path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(f"Expected a YAML file, got: {path}")
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse YAML file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a top-level mapping: {path}")
    return data


def find_yaml_file(directory: Path, stem: str) -> Path:
    """Find ``<stem>.yaml`` or ``<stem>.yml`` and reject JSON fallback."""
    for suffix in (".yaml", ".yml"):
        candidate = directory / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    json_path = directory / f"{stem}.json"
    if json_path.exists():
        raise ValueError(f"JSON input is not supported; convert {json_path} to YAML")
    raise FileNotFoundError(f"No {stem}.yaml or {stem}.yml found in {directory}")


def validate_yaml_dataset(dataset: Path) -> None:
    """Ensure required dataset definitions use the v3 YAML format."""
    find_yaml_file(dataset, "system")
    find_yaml_file(dataset / "energy_system", "base_units")
    legacy_scenarios = dataset / "scenarios.json"
    if legacy_scenarios.exists():
        raise ValueError(
            f"JSON input is not supported; convert {legacy_scenarios} to YAML"
        )
    legacy_attributes = list(dataset.rglob("attributes.json"))
    if legacy_attributes:
        raise ValueError(
            "JSON input is not supported; convert attribute files to YAML, "
            f"starting with {legacy_attributes[0]}"
        )
    for attributes in dataset.rglob("attributes.y*ml"):
        load_yaml_mapping(attributes)


def modify_yaml(file_path: Path, changes: dict[str, Any]) -> None:
    """Update a YAML mapping in place."""
    data = load_yaml_mapping(file_path)
    data.update(changes)
    with file_path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(data, stream, sort_keys=False)


def copy_dataset(
    old_dataset: Path,
    new_dataset: Path,
    scenarios: Path | None = None,
) -> None:
    """Copy a complete dataset and install only operational scenarios."""
    validate_yaml_dataset(old_dataset)
    if new_dataset.exists():
        shutil.rmtree(new_dataset)
    shutil.copytree(old_dataset, new_dataset)
    for name in ("scenarios.yaml", "scenarios.yml", "scenarios.json"):
        inherited_scenarios = new_dataset / name
        if inherited_scenarios.exists():
            inherited_scenarios.unlink()
    if scenarios is not None:
        load_yaml_mapping(scenarios)
        shutil.copy2(scenarios, new_dataset / "scenarios.yaml")


def load_results(out_dir: Path, scenario: str) -> dict[str, Any]:
    """Load and normalize capacity additions for one planning scenario."""
    results = Results(out_dir)
    if "capacity_addition" not in results.get_component_names(
        "variable", scenario_name=scenario
    ):
        raise ValueError("Results have no variable named capacity_addition")

    system = results.get_system(scenario_name=scenario)
    solver = results.get_solver(scenario_name=scenario)
    capacity_addition = results.get_total("capacity_addition", scenario_name=scenario)
    if not isinstance(capacity_addition, pd.DataFrame):
        raise TypeError("capacity_addition results must be a DataFrame")
    capacity_units = results.get_unit("capacity_addition", scenario_name=scenario)
    if not isinstance(capacity_units, pd.Series):
        raise TypeError("capacity_addition units must be an indexed Series")

    edges_result = results.get_total("set_nodes_on_edges", scenario_name=scenario)
    conversion_technologies = sorted(
        set(system.set_conversion_technologies)
        - set(system.set_retrofitting_technologies)
    )
    capacity_addition.columns.name = "year"
    capacity_addition = capacity_addition.stack().unstack("capacity_type")

    return {
        "capacity_addition": capacity_addition,
        "capacity_units": capacity_units,
        "solver": solver,
        "nodes": system.set_nodes,
        "edges": edges_result.index.values,
        "technologies": {
            "set_conversion_technologies": conversion_technologies,
            "set_transport_technologies": system.set_transport_technologies,
            "set_storage_technologies": system.set_storage_technologies,
            "set_retrofitting_technologies": system.set_retrofitting_technologies,
        },
    }


def get_element_location(
    element_name: str, raw_results: dict[str, Any]
) -> tuple[Any, str]:
    """Return valid locations and their CSV column name for a technology set."""
    if element_name == "set_transport_technologies":
        return raw_results["edges"], "edge"
    return raw_results["nodes"], "node"


def get_element_folder(dataset_op: Path, element_name: str, technology: str) -> Path:
    """Return the dataset directory for one technology."""
    if element_name == "set_retrofitting_technologies":
        return (
            dataset_op
            / "set_technologies"
            / "set_conversion_technologies"
            / element_name
            / technology
        )
    return dataset_op / "set_technologies" / element_name / technology


def convert_to_original_units(
    capacity: pd.DataFrame,
    capacity_units: pd.Series,
    capacity_type: str,
    unit_converter: UnitConverter,
    technology: str,
    technology_folder: Path,
    suffix: str,
) -> pd.DataFrame:
    """Convert capacity additions from model base units to dataset units."""
    output_unit = capacity_units.loc[(technology, capacity_type)]
    output_multiplier = unit_converter.get_unit_multiplier(output_unit, technology)
    if not np.isclose(output_multiplier, 1):
        raise AssertionError("Model output is not in base units")

    attributes_path = find_yaml_file(technology_folder, "attributes")
    attributes = load_yaml_mapping(attributes_path)
    parameter = f"capacity_existing{suffix}"
    try:
        input_unit = attributes[parameter]["unit"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"Missing unit for {parameter!r} in {attributes_path}"
        ) from exc
    multiplier = unit_converter.get_unit_multiplier(
        input_unit, parameter, path=attributes_path
    )
    capacity[parameter] = capacity[parameter] / multiplier
    return capacity


def round_capacity(results: dict[str, Any]) -> dict[str, Any]:
    """Discard capacity additions below the solver's unit tolerance."""
    capacity = results["capacity_addition"]
    tolerance = 10 ** (-results["solver"].rounding_decimal_points_units)
    keep = capacity["power"] > tolerance
    if "energy" in capacity.columns:
        keep |= (capacity["energy"] > tolerance) | capacity["energy"].isna()
    results["capacity_addition"] = capacity.loc[keep]
    return results


def add_capacity_additions(
    dataset_op: Path,
    results: dict[str, Any],
    element_name: str,
    capacity_type: str,
    unit_converter: UnitConverter,
) -> None:
    """Add one capacity type for a technology set to existing-capacity CSVs."""
    _, location_name = get_element_location(element_name, results)
    capacity_addition = results["capacity_addition"]
    suffix = "" if capacity_type == "power" else "_energy"
    parameter = f"capacity_existing{suffix}"

    for technology in results["technologies"][element_name]:
        if technology not in capacity_addition.index.get_level_values(0):
            continue
        technology_folder = get_element_folder(dataset_op, element_name, technology)
        capacity_file = technology_folder / f"{parameter}.csv"
        capacity = capacity_addition.loc[(technology, capacity_type)].reset_index()
        capacity = capacity.rename(
            columns={
                "location": location_name,
                capacity_type: parameter,
                "year": "year_construction",
            }
        )
        capacity = convert_to_original_units(
            capacity,
            results["capacity_units"],
            capacity_type,
            unit_converter,
            technology,
            technology_folder,
            suffix,
        )
        if capacity_file.exists():
            existing = pd.read_csv(capacity_file)
            capacity = pd.concat([existing, capacity], ignore_index=True)
        capacity = (
            capacity[[location_name, "year_construction", parameter]]
            .groupby([location_name, "year_construction"], as_index=False)
            .sum()
        )
        capacity.to_csv(capacity_file, index=False)


def capacity_addition_to_existing_capacity(
    out_dir: Path,
    dataset: Path,
    dataset_op: Path,
    scenario: str,
) -> None:
    """Transfer optimized additions into a copied dataset."""
    results = round_capacity(load_results(out_dir, scenario))
    unit_converter = UnitConverter(
        dataset / "energy_system",
        results["solver"].rounding_decimal_points_units,
    )
    for element_name in results["technologies"]:
        add_capacity_additions(
            dataset_op, results, element_name, "power", unit_converter
        )
    if "energy" in results["capacity_addition"].columns:
        add_capacity_additions(
            dataset_op,
            results,
            "set_storage_technologies",
            "energy",
            unit_converter,
        )
