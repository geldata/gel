.. _ref_cli_gel_instance_listbackups:


=========================
gel instance list-backups
=========================

List backups for an instance. The list specifies the backup ID, creation
timestamp, as well as other information regarding the completion status,
server version, whether the backup was incremental or not, etc.

.. cli:synopsis::

    gel instance list-backups [<options>]

This is useful to find the backup ID needed by the
:ref:`ref_cli_gel_instance_restore` command.


Options
=======

:cli:synopsis:`-I <name>, --instance=<name>`
    The |Gel| instance name. This is part of the common :ref:`connection
    options <ref_cli_gel_connopts>`.

:cli:synopsis:`--json`
    Format output as JSON.

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