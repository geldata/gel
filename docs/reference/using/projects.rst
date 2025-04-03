.. _ref_guide_using_projects:

========
Projects
========

A Gel project represents a codebase that shares a single Gel database instance. Projects make local development simpler by automatically managing database connections without requiring you to specify credentials each time you run a command.

**Key concepts:**

* A project is marked by a |gel.toml| file in your codebase's root directory
* Projects are "linked" to a specific Gel database instance
* This link stores connection information in Gel's config directory
* When you run Gel commands within a project directory, they automatically connect to the linked instance
* All client libraries use the same mechanism to auto-connect inside project directories

**Benefits of projects:**

* Run CLI commands without connection flags (e.g., use :gelcmd:`migrate` instead of :gelcmd:`-I my_instance migrate`)
* Make applications portable - teammates can quickly set up matching database instances
* Separate connection details from code - no hard-coded credentials needed or complex conditional environment-based connection logic

.. note::

  Projects are intended only for local development. In production environments, you should provide instance credentials using environment variables. See :ref:`Connection parameters <ref_reference_connection>` for details.

Creating a new Gel project
==========================

To get started, navigate to the root directory of your codebase in a shell and run :gelcmd:`project init`. You'll see something like this:

.. code-block:: bash

  $ gel project init
  No `gel.toml` found in this repo or above.
  Do you want to initialize a new project? [Y/n]
  > Y
  Checking Gel versions...
  Specify the version of Gel to use with this project [6.4]:
  > # left blank for default
  Specify the name of Gel instance to use with this project:
  > my_instance
  Initializing Gel instance...
  Bootstrap complete. Server is up and running now.
  Project initialialized.

This process:

1. Asks you to specify a Gel version (defaulting to the latest stable version)
2. Prompts for an instance name (creating a new instance if needed)
3. Links your current directory to that instance by storing connection metadata in Gel's :ref:`config directory <ref_cli_gel_paths>`
4. Creates a |gel.toml| file marking this directory as a Gel project
5. Sets up a ``dbschema`` directory with a :dotgel:`dbschema/default` schema file if they don't already exist

Working with existing projects
==============================

If you've cloned a repository that already contains a |gel.toml| file, simply run :gelcmd:`project init` in the project directory. This will:

1. Install the required Gel version if needed
2. Create a new local instance with the appropriate name
3. Apply any existing migrations
4. Link the project to the new instance

This makes it easy to begin working with Gel-backed applications without manual configuration.

Unlinking a project
===================

To remove the link between your project and its instance, run :gelcmd:`project unlink` anywhere inside the project. This doesn't affect the instance itself, which continues running. After unlinking, you can run :gelcmd:`project init` again to link to a different instance.

Using projects with remote instances
====================================

You can also link a project to a non-local Gel instance (such as a shared staging database). First, create a link to the remote instance:

.. code-block:: bash

  $ gel instance link
  Specify the host of the server [default: localhost]:
  > 192.168.4.2
  Specify the port of the server [default: 5656]:
  > 10818
  Specify the database user [default: admin]:
  > admin
  Specify the branch name [default: main]:
  > main
  Unknown server certificate: SHA1:c38a7a90429b033dfaf7a81e08112a9d58d97286. Trust? [y/N]
  > y
  Password for 'admin':
  Specify a new instance name for the remote server [default: 192_168_4_2_10818]:
  > staging_db
  Successfully linked to remote instance. To connect run:
    gel -I staging_db

Then run :gelcmd:`project init` and specify ``staging_db`` as the instance name.

.. note::

  When using an existing instance, make sure that the project source tree is in sync with the current migration revision of the instance. If the current revision in the database doesn't exist under ``dbschema/migrations/``, it'll raise an error when trying to migrate or create new migrations. In this case, update your local source tree to the revision that matches the current revision of the database.

.. _ref_reference_gel_toml:

gel.toml
========

The |gel.toml| file is created in the project root after running :ref:`ref_cli_gel_project_init`. If this file is present in a directory, it signals to the CLI and client bindings that the directory is an instance-linked |Gel| project. It supports the following configuration settings:

Example
-------

.. code-block:: toml

    [instance]
    server-version = "6.0"

    [project]
    schema-dir = "db/schema"

    [hooks]
    project.init.after = "setup_dsn.sh"
    branch.switch.after = "setup_dsn.sh"
    schema.update.after = "gel-orm sqlalchemy --mod compat --out compat"

    [[watch]]
    files = ["queries/*.edgeql"]
    script = "npx @edgedb/generate queries"


[instance] table
----------------

.. versionchanged:: 6.0

    For versions of |Gel| prior to 6.0 use ``[edgedb]`` table instead of ``[instance]``.

- ``server-version``- version of Gel server to use with this project.

  .. note::

      The version specification is assumed to be **a minimum version**, but the CLI will *not* upgrade to subsequent major versions. This means if the version specified is ``6.1`` and versions 6.2 and 6.3 are available, 6.3 will be installed, even if version 7.0 is also available.

      To specify an exact version, prepend with ``=`` like this: ``=6.1``. We support `all of the same version specifications as Cargo`_, Rust's package manager.



[project] table
---------------

- ``schema-dir``- directory where schema files will be stored.
  Defaults to ``dbschema``.


.. _ref_reference_gel_toml_hooks:

[hooks] table
-------------

.. versionadded:: 6

This table may contain the following keys, all of which are optional:

- ``project.init.before``
- ``project.init.after``
- ``branch.switch.before``
- ``branch.wipe.before``
- ``migration.apply.before``
- ``schema.update.before``
- ``branch.switch.after``
- ``branch.wipe.after``
- ``migration.apply.after``
- ``schema.update.after``

Each key represents a command hook that will be executed together with a CLI
command. All keys have a string value which is going to be executed as a shell
command when the corresponding hook is triggered.

Hooks are divided into two categories: ``before`` and ``after`` as indicated
by their names. All of the ``before`` hooks are executed prior to their
corresponding commands, so they happen before any changes are made. All of the
``after`` hooks run after the CLI command and thus the effects from the
command are already in place. Any error during the hook script execution will
terminate the CLI command (thus ``before`` hooks are able to prevent their
commands from executing if certain conditions are not met).

Overall, when multiple hooks are triggered they all execute sequentially in
the order they are listed above.

Here is a breakdown of which command trigger which hooks:

- :ref:`ref_cli_gel_project_init` command triggers the ``project.init.before``
  and ``project.init.after`` hook. If the migrations are applied at the end of
  the initialization, then the ``migration.apply.before``,
  ``schema.update.before``, ``migration.apply.after``, and
  ``schema.update.after`` hooks are also triggered.
- :ref:`ref_cli_gel_branch_switch` command triggers ``branch.switch.before``,
  ``schema.update.before``, ``branch.switch.after``, and ``schema.update.after``
  hooks in that relative order.
- :ref:`ref_cli_gel_branch_wipe` command triggers the ``branch.wipe.before``,
  ``schema.update.before``, ``branch.wipe.after``, and ``schema.update.after``
  hooks in that relative order.
- :ref:`ref_cli_gel_branch_rebase` and :ref:`ref_cli_gel_branch_merge`
  commands trigger ``migration.apply.before``, ``schema.update.before``,
  ``migration.apply.after``, and ``schema.update.after`` hooks in that
  relative order. Notice that although these are branch commands, but they do
  not change the current branch, instead they modify and apply migrations.
  That's why they trigger the ``migration.apply`` hooks.
- :ref:`ref_cli_gel_migration_apply` command triggers
  ``migration.apply.before``, ``schema.update.before``,
  ``migration.apply.after``, and ``schema.update.after`` hooks in that
  relative order.

  .. note::

    All of these hooks are intended as project management tools. For this
    reason they will only be triggered by the CLI commands that *don't
    override* default project settings. Any CLI command that uses
    :ref:`connection options <ref_cli_gel_connopts>` will not trigger any
    hooks.

This is implementing `RFC 1028 <rfc1028_>`_.

[[watch]] table array
---------------------

.. versionadded:: 6

Each element of this table array may contain the following required keys:

- ``files = ["<path-string>", ...]`` - specify file(s) being watched.

  The paths must use ``/`` (\*nix-style) as path separators. They can also contain glob pattrens (``*``, ``**``, ``?``, etc.) in order to specify multiple files at one.

- ``script = "<command>"`` - command to be executed by the shell.

The watch mode can be activated by the :ref:`ref_cli_gel_watch` command.

This is implementing `RFC 1028 <rfc1028_>`_.

.. _all of the same version specifications as Cargo:
   https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-dependencies

.. _rfc1028:
    https://github.com/edgedb/rfcs/blob/master/text/1028-cli-hooks.rst
