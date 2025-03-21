.. _ref_upgrading:

=================
Upgrading from v5
=================

With the release of Gel v6, we have introduced a number of changes that affect your workflow. The most obvious change is that the CLI and client libraries are now named after Gel, not EdgeDB. But, there are a number of other smaller changes and enhancements that are worth understanding as you bring your EdgeDB database up-to-date with the latest release.

CLI
===

.. lint-off

For a few versions we've been shipping an alias to the ``edgedb`` CLI named ``gel`` as we've been working on the rename. For the most part, you can now just use ``gel`` instead of ``edgedb`` as the CLI name. Make sure you are using the latest version of the CLI by running :gelcmd:`cli upgrade`. If you see a note about not being able to upgrade, you can try running ``edgedb cli upgrade`` and then after that :gelcmd:`cli upgrade`.

Don't forget to update any scripts that use the ``edgedb`` CLI to use ``gel`` instead.

.. lint-on

Project Configuration File
==========================

.. lint-off

Gel CLI and client libraries use a configuration file configure various things about your project, such as the location of the schema directory, and the target version of the Gel server. Previously, this file was named ``edgedb.toml``, but it is now named |gel.toml|.

.. lint-on

In addition to the name change, we have also renamed the TOML table for configuring the server version from ``[edgedb]`` to ``[instance]``.

.. tabs::

  .. code-tab:: toml
    :caption: (Before) edgedb.toml

    [edgedb]
    server-version = "5.7"

  .. code-tab:: toml-diff
    :caption: (After) gel.toml

    - [edgedb]
    + [instance]
      server-version = "5.7"

We continue to support the old file and table name, but we recommend updating to the new name as soon as possible.

There are also a number of useful new workflow features in the CLI that are configured in this file that are worth exploring as well. See the `announcement blog post <https://www.geldata.com/blog/gel-s-new-edgeql-features-and-cli-workflows>`_ for more details.

Client Libraries
================

We've started publishing our various client libraries under Gel-flavored names, and will only be publishing to these new packages going forward.

.. list-table::
  :header-rows: 1

  * - Language
    - New Package
  * - Python
    - `gel on PyPI <https://pypi.org/project/gel/>`_
  * - TypeScript
    - `gel on npm <https://www.npmjs.com/package/gel>`_
  * - Go
    - `gel-go on GitHub <https://github.com/geldata/gel-go>`_
  * - Rust
    - `gel-rust on GitHub <https://github.com/geldata/gel-rust>`_

If you're using the TypeScript client library, you can use our codemod to automatically update your codebase to point at the new packages:

.. code-block:: bash

  $ npx @gel/codemod@latest

Code generation
===============

Some of the languages we support include code generation tools that can generate code from your schema. Here is a table of how those tools have been renamed:

.. list-table::
  :header-rows: 1

  * - Language
    - Previous
    - Current
  * - Python
    - ``edgedb-py``
    - ``gel-py``
  * - TypeScript
    - ``@edgedb/generate``
    - ``@gel/generate``

Check your project task runners and update them accordingly.

Upgrading instances
===================

To take advantage of the new features in Gel v6, you'll need to upgrade your instances to the latest version.

Cloud instances
---------------

If you're using a hosted instance on Gel Cloud, you can upgrade your instance by clicking on the "Upgrade" button in the Gel Cloud console, or with the CLI.

.. code-block:: bash

  $ gel instance upgrade <my-org/my-instance-name> --to-latest

Local instances
---------------

If you have local instances that you've intialized with the CLI using :gelcmd:`project init`, you can upgrade them easily with the CLI.

.. code-block:: bash

  gel project upgrade --to-latest

This will upgrade the project instance to the latest version of Gel and also update the |gel.toml| server-version value to the latest version.

Remote instances
----------------

To upgrade a remote instance, we recommend the following dump-and-restore process:

1. Gel v6.0 supports PostgreSQL 14 or above. Verify your PostgreSQL version before upgrading Gel. If you're using Postgres 13 or below, upgrade Postgres first.

2. Spin up an empty 6.0 instance. You can use one of our :ref:`deployment guides <ref_guide_deployment>`.

   For Debian/Ubuntu, when adding the Gel package repository, use this command:

   .. code-block:: bash

       $ echo deb [signed-by=/usr/local/share/keyrings/gel-keyring.gpg] \
           https://packages.geldata.com/apt \
           $(grep "VERSION_CODENAME=" /etc/os-release | cut -d= -f2) main \
           | sudo tee /etc/apt/sources.list.d/gel.list
       $ sudo apt-get update && sudo apt-get install gel-6

   For CentOS/RHEL, use this installation command:

   .. code-block:: bash

       $ sudo yum install gel-6

   In any required ``systemctl`` commands, replace ``edgedb-server-5`` with ``gel-server-6``.

   For Docker setups, use the ``6`` or other appropriate tag.

   .. note::

     The new instance will have a different DSN, including a different port number. Take note of the full DSN of the new instance as you'll need it to restore your database, and update your application to use the new DSN in further steps.

3. Take your application offline, then dump your v5.x database with the CLI:

   .. code-block:: bash

       $ gel dump --dsn <old dsn> --all --format dir my_database.dump/

   This will dump the schema and contents of your current database to a directory on your local disk called ``my_database.dump``. The directory name isn't important.

4. Restore to the new, empty v6 instance from the dump:

   .. code-block:: bash

       $ gel restore --all my_database.dump/ --dsn <new dsn>

   Once the restore is complete, update your application to connect to the new instance.

   This process will involve some downtime, specifically during steps 2 and 3.

GitHub Action
=============

We publish a GitHub action for accessing a Gel instance in your GitHub Actions workflows. This action has been updated to work with Gel v6. If you're using the action in your workflow, update it to use the latest version.

.. code-block:: yaml-diff

  - - uses: edgedb/setup-edgedb@v1
  + - uses: geldata/setup-gel@v1
  - - run: edgedb query 'select sys::get_version_as_str()'
  + - run: gel query 'select sys::get_version_as_str()'
