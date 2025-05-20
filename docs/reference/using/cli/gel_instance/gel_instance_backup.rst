.. _ref_cli_gel_instance_backup:


===================
gel instance backup
===================

Backup a |Gel| instance to disk.

.. cli:synopsis::

    gel instance backup [<options>]


Description
===========

The :gelcmd:`instance backup` command creates a backup of the specified
insatnce. This backup can be restored using the
:ref:`ref_cli_gel_instance_restore` command.

The tool will automatically determine whether to perform a full or an
incremental backup. The goal is to balance the backup size with the restore
speed. So the rule of thumb is that an incremental backup will be created if
the most recent full backup is no more than a few days old and if the five
most recent backups aren't all incremental, too.

To view all available backups for an instance use
:ref:`ref_cli_gel_instance_listbackups` command.


Options
=======

:cli:synopsis:`-I <name>, --instance=<name>`
    The |Gel| instance name. This is part of the common :ref:`connection
    options <ref_cli_gel_connopts>`.

:cli:synopsis:`--non-interactive`
    Backup the instance without asking for confirmation.

Cloud-related options:

:cli:synopsis:`--cloud-api-endpoint <URL>`
    Specify the API endpoint. Defaults to the current logged-in server, or
    ``https://api.g.aws.edgedb.cloud`` if unauthorized.

:cli:synopsis:`--cloud-secret-key <secret_key>`
    Specify the API secret key to use instead of loading key from a remembered
    authentication.

:cli:synopsis:`--cloud-profile <profile>`
    Specify the authenticated profile. Defaults to "default".

Docker-related options:

:cli:synopsis:`--docker`
    Connect to a docker instance. If ``docker-compose.yaml`` is present, the
    instance will be automatically detected. Otherwise,
    :cli:synopsis:`--container` must be specified.

:cli:synopsis:`--container <container>`
    Connect to a specific docker container.

Other connection options can be found :ref:`here <ref_cli_gel_connopts>`.