.. _ref_guide_cloud_cli:

===
CLI
===

:edb-alt-title: Using Gel Cloud via the CLI

Gel Cloud is shutting down and new instances cannot be created. Use the CLI
only to log in and export data from your existing hosted instance:

.. code-block:: bash

   $ gel cloud login
   $ gel dump --all --format dir -I <org>/<instance> backup/

If you need a new secret key to automate the dump, generate one with
:ref:`ref_cli_gel_cloud_secretkey_create`. Restore your backup into a
self-managed deployment using :gelcmd:`restore` and a DSN for your new
instance.
