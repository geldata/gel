.. _ref_migrate_from:

=======================================
Migrating from Gel Cloud to Self-Hosted
=======================================

:edb-alt-title: Migrating from Gel Cloud to Self-Hosted Gel

|Gel| Cloud is sunsetting at the end of January 2026. To ensure your
applications continue to run smoothly, you should migrate your data to a
self-hosted |Gel| instance.

This guide outlines the process of migrating your production data. We strongly
recommend performing a "dry run" with your staging or development environment
first to familiarize yourself with the workflow.


Phase 1: Preparation
====================

1. Spin up your self-hosted deployment
--------------------------------------

While you can host |Gel| on any infrastructure that supports Docker or binary
installations, we recommend using a managed cloud provider (such as Fly.io,
AWS, or GCP with managed Postgres) for production reliability.

See our :ref:`self-hosted deployment guides <ref_guide_deployment>` for
step-by-step instructions on deploying to various platforms.

Ensure your new instance is:

* Running the same version of |Gel| as your Cloud instance (or newer).
* Configured with a persistent volume for data or connected to a managed
  Postgres instance.

2. Retrieve connection parameters
---------------------------------

Once your new instance is live, you need its DSN (Data Source Name) or
individual connection parameters. Each :ref:`deployment guide
<ref_guide_deployment>` outlines the best way to retrieve the various
connection parameters from your specific setup. You will typically need:

* **Host**: The domain or IP of your new instance.
* **Port**: Default is ``5656``.
* **User**: Default is |admin|.
* **Password**: The password you set during initialization.
* **TLS CA**: The certificate used to secure the connection (unless using a
  public CA or ``--trust-tls-cert``).

The DSN format is:

.. code-block:: text

    gel://<user>:<password>@<host>:<port>/<branch>

All components except the scheme are optional. See :ref:`ref_reference_connection_dsn`
for more details.


Phase 2: The Migration (Cutover)
================================

To ensure data consistency, you must prevent new writes to your database
during the transfer.

1. Enable maintenance mode
--------------------------

Before touching the data, put your application into maintenance mode. This
ensures that no new records are created in |Gel| Cloud after you've started
the dump.

* **Web Apps**: Point your load balancer to a static "Maintenance" page.
* **Background Jobs**: Stop all workers, cron jobs, or queues that interact
  with the database.

2. Perform the migration
------------------------

You can use the |Gel| CLI to move data directly from your Cloud instance to
your new self-hosted instance.

.. code-block:: bash

    # 1. Dump from Gel Cloud to directory
    $ gel dump --instance <org-name>/<instance-name> \
      --all --format=dir \
      production_dump

    # 2. Restore to self-hosted from dump
    $ gel restore --dsn <new_self_hosted_dsn> --all production_dump

.. note::

    If your self-hosted instance uses a self-signed TLS certificate, you may
    need to add ``--tls-security insecure`` to the restore command, or first
    retrieve the TLS certificate and set it via :gelenv:`TLS_CA`.


Phase 3: Verification and Go-Live
=================================

1. Update application environment variables
-------------------------------------------

Update your application's configuration to point to the new instance. Replace
the Gel Cloud specific connection environment variables :gelenv:`INSTANCE` and
:gelenv:`SECRET_KEY` variables with the new connection details:

* :gelenv:`DSN`: :geluri:`user:password@host:port/branch`
* :gelenv:`TLS_CA`: The TLS certificate content (if your instance uses a
  self-signed certificate)
* :gelenv:`CLIENT_TLS_SECURITY`: Set to ``insecure`` if you need to skip TLS
  verification (not recommended for production)

2. Sanity check
---------------

Before turning off maintenance mode:

* Run a few :gelcmd:`query` commands against the new instance to verify data
  integrity.
* Check that your schema migrated correctly: :gelcmd:`migrate --status`.
* Launch a local instance of your app connected to the new production DB to
  ensure connection logic is sound.

3. Disable maintenance mode
---------------------------

Once verified, restart your application servers and background workers.
Monitor your logs closely for any connection or permission errors.


Post-Migration Note
===================

Once you are 100% certain your data is safe and your app is stable on the new
host, you can de-provision your |Gel| Cloud instance. Remember that all |Gel|
Cloud data will be deleted after the January 2026 deadline.
