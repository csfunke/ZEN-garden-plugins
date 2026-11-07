.. _available_plugins.operation_scenarios:

Operation-only scenarios
------------------------

The ``operation_scenarios`` extension tests completed capacity-expansion
solutions in operation-only ZEN-garden models. It copies one selected planning
solution's capacity additions into ``capacity_existing`` inputs of a separate
operational dataset and disables new investment. Operational scenarios are
defined by that dataset's existing scenario file.

Although the implementation lives in a module named ``plugin.py`` for package
consistency, this extension is a standalone command. Do **not** add it to the
``plugins`` section of ``config.yaml``.

Installation
^^^^^^^^^^^^

Install this repository in the same environment as ZEN-garden:

.. code-block:: shell

   pip install -e path/to/ZEN-garden-plugins --no-deps

This installs the ``zen-operation`` command.

Input files
^^^^^^^^^^^

The wrapper supports ZEN-garden v3 datasets. Configuration and attribute files
must use YAML; scenario definitions may use ``scenarios.yaml``,
``scenarios.yml``, or ``scenarios.json``. A typical layout is:

.. code-block:: text

   data/
   |-- config.yaml
   `-- dataset/
       |-- energy_system/
       |   |-- attributes.yaml
       |   `-- base_units.yaml
       |-- set_carriers/
       |-- set_technologies/
       |-- scenarios.yaml
       `-- system.yaml

An operational scenario uses the regular ZEN-garden scenario syntax. For
example, this runs the operation model without time-series aggregation:

.. code-block:: yaml

   full_year:
     system:
       conduct_time_series_aggregation: false
       aggregated_time_steps_per_year: 8760

Running from the command line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run the planning model first, then invoke the wrapper with the exact result
folder, planning scenario name, and operational input dataset:

.. code-block:: shell

   zen-garden --config config.yaml --dataset planning_dataset
   zen-operation --config config.yaml --dataset operational_dataset \
       --planning_results outputs/planning_dataset \
       --planning_scenario planning_case

The command accepts:

``--dataset``
   Required path to the operational input dataset. This dataset is copied and
   remains unchanged.

``--planning_results``
   Required path to the completed capacity-expansion results directory.

``--planning_scenario``
   Required exact name of the planning-results scenario whose capacity
   additions should be used.

``--config``
   YAML configuration for operation-only runs. Defaults to ``config.yaml``.

``--folder_output``
   Directory receiving operation results. Defaults to ``outputs``.

``--job_index``
   Comma-separated operational-scenario indices from the input dataset's
   scenario definition. All operational scenarios run when omitted.

``--job_index_var``
   Environment variable used when ``--job_index`` is omitted. Defaults to
   ``SLURM_ARRAY_TASK_ID``.

``--delete_data``
   Permanently delete each generated operation-only input dataset after its
   run, including when that run fails. Result folders are retained.

Running from Python
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from zen_garden import run
   from zen_garden_plugins.operation_scenarios import operation_scenarios

   run(config="config.yaml", dataset="planning_dataset")
   operation_scenarios(
       config="config.yaml",
       dataset="operational_dataset",
       planning_results="outputs/planning_dataset",
       planning_scenario="planning_case",
   )

Generated datasets and results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For operational input ``operational_dataset`` and planning scenario
``scenario_name``, the generated input dataset and result folder are named
``operational_dataset_scenario_name__operation``.

The wrapper replaces an existing generated input dataset with the same name.
Use ``--delete_data`` when the copied inputs are not needed after execution.
This deletion is permanent and intentionally does not remove result folders,
which may contain useful diagnostics or share a parent with the planning
results.

Module documentation
^^^^^^^^^^^^^^^^^^^^

.. automodule:: zen_garden_plugins.operation_scenarios.plugin
   :members:
   :undoc-members:

