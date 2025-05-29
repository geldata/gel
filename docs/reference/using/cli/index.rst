.. _ref_cli_overview:

===
CLI
===

:edb-alt-title: The Gel CLI

The |gelcmd| command-line interface (CLI) provides an idiomatic way to spin up local instances, open a REPL, execute queries, manage auth roles, introspect schema, create migrations, and more.

If you're using JavaScript or Python, our client libraries will handle downloading and running the CLI for you using tools like ``npx`` and ``uvx``.

For everyone else, or if you wish to install the CLI globally, you can install using our bash installer or your operating system's package manager.

.. tabs::

  .. code-tab:: bash
    :caption: bash

    $ curl https://www.geldata.com/sh --proto "=https" -sSf1 | sh

  .. code-tab:: powershell
    :caption: Powershell

    PS> irm https://www.geldata.com/ps1 | iex

  .. code-tab:: bash
    :caption: Homebrew

    $ brew install geldata/tap/gel-cli

  .. code-tab:: bash
    :caption: Nixpkgs

    $ nix-shell -p gel

  .. code-tab:: bash
    :caption: JavaScript

    $ npx gel --version

  .. code-tab:: bash
    :caption: Python

    $ uvx gel --version

.. rubric:: Connection options

All commands respect a common set of
:ref:`connection options <ref_cli_gel_connopts>`, which let you specify
a target instance. This instance can be local to your machine or hosted
remotely.


.. _ref_cli_gel_uninstall:

.. rubric:: Uninstallation

Command-line tools contain just one binary, so to remove it on Linux or
macOS run:

.. code-block:: bash

   $ rm "$(which gel)"

To remove all configuration files, run :gelcmd:`info` to list the directories
where |Gel| stores data, then use ``rm -rf <dir>`` to delete those
directories.

If the command-line tool was installed by the user (recommended) then it
will also remove the binary.

If you've used ``gel`` commands you can also delete
:ref:`instances <ref_cli_gel_instance_destroy>` and :ref:`server
<ref_cli_gel_server_uninstall>` packages, prior to removing the
tool:

.. code-block:: bash

   $ gel instance destroy <instance_name>

To list instances and server versions use the following commands
respectively:

.. code-block:: bash

   $ gel instance status
   $ gel server list-versions --installed-only


.. _ref_cli_gel_config:

.. rubric:: Configure CLI and REPL

You can customize the behavior of the |gelcmd| CLI and REPL with a
global configuration file. The file is called ``cli.toml`` and its
location differs between operating systems. Use
:ref:`ref_cli_gel_info` to find the "Config" directory on your
system.

The ``cli.toml`` has the following structure. All fields are optional:

.. code-block::

    [shell]
    expand-strings = true         # Stop escaping newlines in quoted strings
    history-size = 10000          # Set number of entries retained in history
    implicit-properties = false   # Print implicit properties of objects
    limit = 100                   # Set implicit LIMIT
                                  # Defaults to 100, specify 0 to disable
    input-mode = "emacs"          # Set input mode. One of: vi, emacs
    output-format = "default"     # Set output format.
                                  # One of: default, json, json-pretty,
                                  # json-lines
    print-stats = "off"           # Print statistics on each query.
                                  # One of: off, query, detailed
    verbose-errors = false        # Print all errors with maximum verbosity


:ref:`Notes on network usage <ref_cli_gel_network>`


.. toctree::
    :maxdepth: 3
    :hidden:

    gel_connopts
    network
    gel
    gel_project/index
    gel_ui
    gel_watch
    gel_migrate
    gel_migration/index
    gel_cloud/index
    gel_branch/index
    gel_dump
    gel_restore
    gel_configure
    gel_query
    gel_analyze
    gel_list
    gel_info
    gel_cli_upgrade
    gel_extension/index
    gel_server/index
    gel_describe/index
    gel_instance/index
    gel_database/index
