=================
Local Development
=================

One of Gel's most powerful features is its seamless support for local development. The Gel CLI makes it incredibly easy to spin up a local instance, manage it, access GUI, and iterate on your schema quickly and safely. This guide outlines the flexible options available for your local development workflow.

If you're using JavaScript or Python, our client libraries will automatically handle the installation for you using tools like ``npx`` and ``uvx``. For other environments or to install the CLI globally, you can use one of the following methods:

.. include:: ./install_table.rst


Initialize your local instance
==============================

It's easy to get started with a local Gel instance. Navigate to the root of your project repository and run:

.. code-block:: bash

  $ gel init

This command takes care of several things for you:

* It downloads and installs the latest version of the Gel server.
* It configures a local Postgres cluster.
* It manages the instance through your operating system's background task launcher.

To conserve resources, Gel automatically puts inactive local development instances to sleep. This means you can have multiple instances running without them draining your system's resources when not in use.

Iterate on your schema
======================

Gel simplifies the process of evolving your data model. You can apply changes from your Gel schema files directly to your running local instance without needing to create a separate migration file for every minor adjustment.

There are two primary ways to apply schema changes during development:

1. **Automatic updates with** :gelcmd:`watch --migrate`
    For a hands-off approach, you can use the watch command. This starts a process that monitors your Gel schema files for changes and automatically migrates your local instance as soon as you save them:

    .. code-block:: bash

      $ gel watch --migrate

    This is ideal for rapid iteration when you want to see your schema changes reflected immediately.

2. **Manual updates with** :gelcmd:`migrate --dev-mode`
    If you prefer more explicit control, or don't want a background process running, you can apply schema changes manually:

    .. code-block:: bash

      $ gel migrate --dev-mode

    This command performs the same action as the watch --migrate mode—applying the current state of your schema files to the local instance—but only when you explicitly run it.

Finalizing changes
==================

Once you're satisfied with the schema changes you've made iteratively, you'll want to create a migration file which will be committed to version control and shared with others. This new migration file will encapsulate all the modifications made since your last migration.

1. **Create the migration file**
    .. code-block:: bash

      $ gel migration create

    This command inspects the differences between your last migration file and the current state of your database schema, then generates a new migration file reflecting these changes.

1. **Align your local instance**
    After creating the migration, run the following command to ensure your local instance's migration history is aligned with this new migration. You can do this by running:

    .. code-block:: bash

      $ gel migrate --dev-mode

    This command effectively "fast-forwards" your local instance. From its perspective, it will appear as though all the iterative changes were applied as part of this single, new migration. This keeps your local development environment consistent with the migration history you'll use in other environments (like staging or production).

Undoing destructive changes
===========================

Mistakes happen! You might accidentally make a destructive schema change. Fortunately, Gel has your back. Every time you migrate your schema (either via :gelcmd:`watch --migrate` or :gelcmd:`migrate --dev-mode`), a backup of your local instance is automatically taken.

If you need to roll back to a previous state:

1. **Stop any active migration processes**: Ensure :gelcmd:`watch --migrate` is not running.

2. **Find the backup ID**: Look through your shell's scrollback history. You'll find messages indicating backups were made, along with their IDs. Identify the ID of the backup created before the destructive change. You can also use the :gelcmd:`instance listbackups` command to list all backups for this instance.

3. **Restore the instance**
    .. code-block:: bash

      $ gel instance restore <backup-id> -I <your-local-instance-name>

    Replace <backup-id> with the actual ID and <your-local-instance-name> with the name of your instance (e.g., my_project). This will restore both your data and schema to the state at that backup point.

Once restored, you can make the intended schema changes and then restart :gelcmd:`watch --migrate` or use :gelcmd:`migrate --dev-mode` as preferred.

Keeping code in sync
====================

Many Gel language bindings offer code generation capabilities (e.g., query builders, typed query functions). This generated code needs to stay synchronized with your schema. Gel provides a system of hooks and watchers that you can configure in your |gel.toml| file to automate this.

These hooks can trigger codegen scripts when:

* The schema changes (using the "schema.change.after" hook).
* Specific files are edited (using watch scripts).

Here's an example |gel.toml| configuration for a TypeScript project. It runs a query builder generator and a queries generator at the appropriate times:

.. code-block:: toml

  [instance]
  server-version = "6.7"

  [hooks]
  "schema.change.after" = "npx @gel/generate edgeql-js && npx @gel/generate queries"

  [watch]
  "src/queries/**/*.edgeql" = "npx @gel/generate queries"

Explanation:

* ``[hooks] / "schema.change.after"``: When any schema change is successfully applied, we run the query builder generator (to reflect schema structure changes) and the queries generator (to update based on new or modified types).
* ``[watch] / "src/queries/**/*.edgeql"``: If any ``.edgeql`` files within the ``src/queries/`` directory (or its subdirectories) are modified, the command ``npx @gel/generate queries`` is executed. This ensures that your typed query functions are always up-to-date with your EdgeQL query definitions.

By configuring these hooks and watchers, you can maintain a smooth workflow where your generated code automatically adapts to changes in your schema and query files.
