.. _gel-js-generators:

===============
Code Generation
===============

The ``@gel/generate`` package provides a set of code generation tools that are useful when developing a Gel-backed applications with TypeScript/JavaScript.

Setup
=====

To install the ``@gel/generate`` package, run the following command.

.. tabs::

    .. code-tab:: bash
      :caption: npm

      $ npm install --save-dev @gel/generate

    .. code-tab:: bash
      :caption: yarn

      $ yarn add --dev @gel/generate

    .. code-tab:: bash
      :caption: pnpm

      $ pnpm add --save-dev @gel/generate

    .. code-tab:: bash
      :caption: bun

      $ bun add --dev @gel/generate

    .. code-tab:: bash
      :caption: deno

      $ deno add --dev npm:@gel/generate

Since the generators work by connecting to the database to introspect your schema and analyze queries, you'll need to have a database connection available when running the generators and to rerun generators any time the schema changes.

Like the CLI, the generators use the connection details from your initialized project, environment, or :ref:`connection flags <ref_cli_gel_connopts>` to connect to the database. See :ref:`the connection parameters reference <ref_reference_connection_parameters>` for more details.

You can ensure that the generators are always up-to-date locally by adding them to your |gel.toml|'s :ref:`schema.update.after hook <ref_reference_gel_toml_hooks>` as in this example:

.. code-block:: toml
  :caption: gel.toml

  [instance]
  server-version = "6.4"

  [hooks]
  schema.update.after = "npx @gel/generate queries --file"


Basic usage
===========

Run a generator with the following command.

.. tabs::

  .. code-tab:: bash
    :caption: npm

    $ npx @gel/generate <generator> [options]

  .. code-tab:: bash
    :caption: yarn

    $ yarn run -B generate <generator> [options]

  .. code-tab:: bash
    :caption: pnpm

    $ pnpm exec generate <generator> [options]

  .. code-tab:: bash
    :caption: Deno

    $ deno run \
      --allow-all \
      npm:@gel/generate <generator> [options]

  .. code-tab:: bash
    :caption: bun

    $ bunx @gel/generate <generator> [options]

The value of ``<generator>`` should be one of the following:

.. list-table::
   :class: funcoptable

   * - ``edgeql-js``
     - Generates the query builder which provides a **code-first** way to write **fully-typed** EdgeQL queries with TypeScript. We recommend it for TypeScript users, or anyone who prefers writing queries with code.
     - :ref:`docs <gel-js-qb>`

   * - ``queries``
     - Scans your project for ``*.edgeql`` files and generates functions that allow you to execute these queries in a typesafe way.
     - :ref:`docs <gel-js-queries>`

   * - ``interfaces``
     - Introspects your schema and generates file containing *TypeScript interfaces* that correspond to each object type. This is useful for writing typesafe code to interact with |Gel|.
     - :ref:`docs <gel-js-interfaces>`

.. _gel_qb_target:

Targets
-------

All generators look at your environment and guess what kind of files to generate (``.ts`` vs ``.js + .d.ts``) and what module system to use (CommonJS vs ES modules). You can override this with the ``--target`` flag.

.. list-table::

  * - ``--target ts``
    - Generate TypeScript files (``.ts``)
  * - ``--target mts``
    - Generate TypeScript files (``.mts``) with extensioned ESM imports
  * - ``--target esm``
    - Generate ``.js`` with ESM syntax and ``.d.ts`` declaration files
  * - ``--target cjs``
    - Generate JavaScript with CommonJS syntax and and ``.d.ts`` declaration files
  * - ``--target deno``
    - Generate TypeScript files with Deno-style ESM imports

Help
----

To see helptext for the ``@gel/generate`` command, run the following.

.. code-block:: bash

  $ npx @gel/generate --help
