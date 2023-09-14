###########
JSON schema
###########

Some of the YAML configuration files used by Phalanx have published JSON schemas, generated from their Pydantic_ models.

.. _Pydantic: https://docs.pydantic.dev/latest/

These schemas are used by the check-jsonschema_ pre-commit hook to validate changes to those files before commit.
If the underlying model changes, the schema will be detected as out-of-date by the Phalanx test suite.
A schema for the current model can be generated with the appropriate Phalanx command-line invocation, as documented below.

.. _check-jsonschema: https://check-jsonschema.readthedocs.io/en/latest/

.. list-table::

   * - Schema
     - Command
   * - :download:`environment values files </extras/schemas/environment.json>`
     - :command:`phalanx environment schema`
   * - :download:`secrets.yaml files </extras/schemas/secrets.json>`
     - :command:`phalanx secrets schema`
