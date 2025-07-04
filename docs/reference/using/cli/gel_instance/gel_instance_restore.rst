.. _ref_cli_gel_instance_restore:


====================
gel instance restore
====================

Restore a |Gel| instance from a backup.

.. cli:synopsis::

    gel instance restore [<options>]


Description
===========

:gelcmd:`instance restore` is a terminal command used to restore a Gel
instance from a backup created by the :ref:`ref_cli_gel_instance_backup`
:tool.


Options
=======

:cli:synopsis:`-I <name>, --instance=<name>`
    The |Gel| instance name to be restored. This is part of the common
    :ref:`connection options <ref_cli_gel_connopts>`.

:cli:synopsis:` --backup-id <backup_id>`
    The backup ID as indicated by the
    :ref:`ref_cli_gel_instance_listbackups`.

:cli:synopsis:`--latest`
    Restore the latest backup available for the instance.

:cli:synopsis:`--source-instance <source>`
    Name of source instance to restore the backup from.

:cli:synopsis:`--non-interactive`
    Restore the instance without asking for confirmation.

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