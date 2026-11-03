.. _available_plugins.operation_scenarios:

Operation-only scenarios
------------------------

The ``operation_scenarios`` extension tests completed capacity-expansion
solutions in operation-only ZEN-garden models. It copies each selected planning
solution's capacity additions into ``capacity_existing`` inputs, disables new
investment, and optionally applies a second set of operational scenarios.

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

The wrapper supports ZEN-garden v3 YAML datasets. JSON configuration,
attributes, and scenario files are rejected. A typical layout is:

.. code-block:: text

   data/
   |-- config.yaml
   `-- dataset/
       |-- energy_system/
       |   |-- attributes.yaml
       |   `-- base_units.yaml
       |-- set_carriers/
       |-- set_technologies/
       |-- scenarios_op.yaml
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

Run the planning model first, then invoke the wrapper against its results:

.. code-block:: shell

   zen-garden --config config.yaml --dataset dataset
   zen-operation --config config.yaml --dataset dataset \
       --scenarios_op scenarios_op.yaml

The command accepts:

``--dataset``
   Required path to the original planning dataset.

``--config``
   YAML configuration for operation-only runs. Defaults to ``config.yaml``.

``--folder_output``
   Directory containing planning results and receiving operation results.
   Defaults to ``outputs``.

``--job_index``
   Comma-separated planning-scenario indices. All scenarios run when omitted.

``--job_index_var``
   Environment variable used when ``--job_index`` is omitted. Defaults to
   ``SLURM_ARRAY_TASK_ID``.

``--scenarios_op``
   Operational-scenario YAML file. Relative paths are resolved from the
   planning dataset.

``--delete_data``
   Permanently delete each generated operation-only input dataset after its
   run, including when that run fails. Result folders are retained.

Running from Python
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from zen_garden import run
   from zen_garden_plugins.operation_scenarios import operation_scenarios

   run(config="config.yaml", dataset="dataset")
   operation_scenarios(
       config="config.yaml",
       dataset="dataset",
       scenarios_op="scenarios_op.yaml",
   )

Generated datasets and results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For planning dataset ``dataset`` and planning scenario ``scenario_name``, the
generated input dataset and result folder are named
``dataset_scenario_name__operation``. A planning run without explicit
scenarios uses ``none``, yielding ``dataset_none__operation``.

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

