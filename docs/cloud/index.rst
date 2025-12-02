.. _ref_guide_cloud:

=====
Cloud
=====

:edb-alt-title: Using Gel Cloud

|Gel| Cloud is shutting down. Signups are closed and new instances cannot be
created. If you have an existing hosted instance, use the steps below to dump
your data and restore it to your own deployment.

Export your data
================

1. Log in with the CLI so your credentials are available locally.

   .. code-block:: bash

      $ gel cloud login

2. Dump everything from your hosted instance to a local directory:

   .. code-block:: bash

      $ gel dump --all --format dir -I <org>/<instance> backup/

3. Set up a self-managed Gel instance using any of the guides in
   :ref:`ref_guide_deployment`.

4. Restore the dump into your new instance:

   .. code-block:: bash

      $ gel restore --all --dsn <your-new-dsn> backup/

   Make sure the target database is empty before restoring.

Need help?
==========

If you run into issues exporting your data, please reach out through your
existing support channels so we can help you wind down safely.
