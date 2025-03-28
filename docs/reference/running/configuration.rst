.. _ref_admin_config:

=============
Configuration
=============

The behavior of the Gel server is configurable with sensible defaults. Some configuration can be set on the running instance using configuration parameters, while other configuration is set at startup using environment variables or command line arguments to the |gel-server| binary.

Configuration parameters
========================

|Gel| exposes a number of configuration parameters that affect its behavior.  In this section we review the ways to change the server configuration, as well as detail each available configuration parameter.

EdgeQL
------

The :eql:stmt:`configure` command can be used to set the configuration parameters using EdgeQL. For example, you can use the CLI REPL to set the ``listen_addresses`` parameter:

.. code-block:: edgeql-repl

  gel> configure instance set listen_addresses := {'127.0.0.1', '::1'};
  CONFIGURE: OK

CLI
---

The :ref:`ref_cli_gel_configure` command allows modifying the system configuration from a terminal or a script:

.. code-block:: bash

  $ gel configure set listen_addresses 127.0.0.1 ::1


Configuration parameters
========================

:edb-alt-title: Available Configuration Parameters

.. _ref_admin_config_connection:

Connection settings
-------------------

.. api-index:: listen_addresses, listen_port, cors_allow_origins

:eql:synopsis:`listen_addresses: multi str`
  Specifies the TCP/IP address(es) on which the server is to listen for connections from client applications. If the list is empty, the server does not listen on any IP interface at all.

:eql:synopsis:`listen_port: int16`
  The TCP port the server listens on; ``5656`` by default. Note that the same port number is used for all IP addresses the server listens on.

:eql:synopsis:`cors_allow_origins: multi str`
  Origins that will be calling the server that need Cross-Origin Resource Sharing (CORS) support. Can use ``*`` to allow any origin. When HTTP clients make a preflight request to the server, the origins allowed here will be added to the ``Access-Control-Allow-Origin`` header in the response.

Resource usage
--------------

.. api-index:: effective_io_concurrency, query_work_mem, shared_buffers

:eql:synopsis:`effective_io_concurrency: int64`
  Sets the number of concurrent disk I/O operations that can be executed simultaneously. Corresponds to the PostgreSQL configuration parameter of the same name.

:eql:synopsis:`query_work_mem: cfg::memory`
  The amount of memory used by internal query operations such as sorting. Corresponds to the PostgreSQL ``work_mem`` configuration parameter.

:eql:synopsis:`shared_buffers: cfg::memory`
  The amount of memory the database uses for shared memory buffers. Corresponds to the PostgreSQL configuration parameter of the same name. Changing this value requires server restart.


Query planning
--------------

.. api-index:: default_statistics_target, effective_cache_size

:eql:synopsis:`default_statistics_target: int64`
  Sets the default data statistics target for the planner.  Corresponds to the PostgreSQL configuration parameter of the same name.

:eql:synopsis:`effective_cache_size: cfg::memory`
  Sets the planner's assumption about the effective size of the disk cache that is available to a single query. Corresponds to the PostgreSQL configuration parameter of the same name.


Query cache
-----------

.. versionadded:: 5.0

.. api-index:: auto_rebuild_query_cache, query_cache_mode, cfg::QueryCacheMode

:eql:synopsis:`auto_rebuild_query_cache: bool`
  Determines whether to recompile the existing query cache to SQL any time DDL is executed.

:eql:synopsis:`query_cache_mode: cfg::QueryCacheMode`
  Allows the developer to set where the query cache is stored. Possible values:

  * ``cfg::QueryCacheMode.InMemory``- All query cache is lost on server restart. This mirrors pre-5.0 |EdgeDB| behavior.
  * ``cfg::QueryCacheMode.RegInline``- The in-memory query cache is also stored in the database as-is so it can be restored on restart.
  * ``cfg::QueryCacheMode.Default``- Allow the server to select the best caching option. Currently, it will select ``InMemory`` for arm64 Linux and ``RegInline`` for everything else.
  * ``cfg::QueryCacheMode.PgFunc``- Wraps queries into stored functions in Postgres and reduces backend request size and preparation time.

Query behavior
--------------

.. api-index:: allow_bare_ddl, cfg::AllowBareDDL, apply_access_policies,
           apply_access_policies_pg, force_database_error

:eql:synopsis:`allow_bare_ddl: cfg::AllowBareDDL`
  Allows for running bare DDL outside a migration. Possible values are ``cfg::AllowBareDDL.AlwaysAllow`` and ``cfg::AllowBareDDL.NeverAllow``.

  When you create an instance, this is set to ``cfg::AllowBareDDL.AlwaysAllow`` until you run a migration. At that point it is set to ``cfg::AllowBareDDL.NeverAllow`` because it's generally a bad idea to mix migrations with bare DDL.

.. _ref_std_cfg_apply_access_policies:

:eql:synopsis:`apply_access_policies: bool`
  Determines whether access policies should be applied when running queries.  Setting this to ``false`` effectively puts you into super-user mode, ignoring any access policies that might otherwise limit you on the instance.

  .. note::

    This setting can also be conveniently accessed via the "Config" dropdown menu at the top of the Gel UI (accessible by running the CLI command :gelcmd:`ui` from within a project). The setting will apply only to your UI session, so you won't have to remember to re-enable it when you're done.

:eql:synopsis:`apply_access_policies_pg -> bool`
  Determines whether access policies should be applied when running queries over SQL adapter. Defaults to ``false``.

:eql:synopsis:`force_database_error -> str`
  A hook to force all queries to produce an error. Defaults to 'false'.

  .. note::

    This parameter takes a ``str`` instead of a ``bool`` to allow more verbose messages when all queries are forced to fail. The database will attempt to deserialize this ``str`` into a JSON object that must include a ``type`` (which must be a Gel :ref:`error type <ref_protocol_errors>` name), and may also include ``message``, ``hint``, and ``details`` which can be set ad-hoc by the user.

    For example, the following is valid input:

    ``'{ "type": "QueryError",
    "message": "Did not work",
    "hint": "Try doing something else",
    "details": "Indeed, something went really wrong" }'``

    As is this:

    ``'{ "type": "UnknownParameterError" }'``

.. _ref_std_cfg_client_connections:

Client connections
------------------

.. api-index:: allow_user_specified_id, session_idle_timeout,
           session_idle_transaction_timeout, query_execution_timeout

:eql:synopsis:`allow_user_specified_id: bool`
  Makes it possible to set the ``.id`` property when inserting new objects.

  .. warning::

    Enabling this feature introduces some security vulnerabilities:

    1. An unprivileged user can discover ids that already exist in the database by trying to insert new values and noting when there is a constraint violation on ``.id`` even if the user doesn't have access to the relevant table.

    2. It allows re-using object ids for a different object type, which the application might not expect.

    Additionally, enabling can have serious performance implications as, on an ``insert``, every object type must be checked for collisions.

    As a result, we don't recommend enabling this. If you need to preserve UUIDs from an external source on your objects, it's best to create a new property to store these UUIDs. If you will need to filter on this external UUID property, you may add an :ref:`index <ref_datamodel_indexes>` or exclusive constraint on it.

:eql:synopsis:`session_idle_timeout -> std::duration`
  Sets the timeout for how long client connections can stay inactive before being forcefully closed by the server.

  Time spent on waiting for query results doesn't count as idling.  E.g. if the session idle timeout is set to 1 minute it would be OK to run a query that takes 2 minutes to compute; to limit the query execution time use the ``query_execution_timeout`` setting.

  The default is 60 seconds. Setting it to ``<duration>'0'`` disables the mechanism. Setting the timeout to less than ``2`` seconds is not recommended.

  Note that the actual time an idle connection can live can be up to two times longer than the specified timeout.

  This is a system-level config setting.

:eql:synopsis:`session_idle_transaction_timeout -> std::duration`
  Sets the timeout for how long client connections can stay inactive while in a transaction.

  The default is 10 seconds. Setting it to ``<duration>'0'`` disables the mechanism.

  .. note::

    For ``session_idle_transaction_timeout`` and ``query_execution_timeout``, values under 1ms are rounded down to zero, which will disable the timeout.  In order to set a timeout, please set a duration of 1ms or greater.

    ``session_idle_timeout`` can take values below 1ms.

:eql:synopsis:`query_execution_timeout -> std::duration`
  Sets a time limit on how long a query can be run.

  Setting it to ``<duration>'0'`` disables the mechanism.  The timeout isn't enabled by default.

  .. note::

    For ``session_idle_transaction_timeout`` and ``query_execution_timeout``, values under 1ms are rounded down to zero, which will disable the timeout.  In order to set a timeout, please set a duration of 1ms or greater.

    ``session_idle_timeout`` can take values below 1ms.

.. _ref_reference_environment:
.. _ref_reference_envvar_variants:

Environment variables
=====================

Certain behaviors of the Gel server are configured at startup. This configuration can be set with environment variables. The variables documented on this page are supported when using the |gel-server| binary or the official :ref:`Docker image <ref_guide_deployment_docker>`.

Some environment variables (noted below) support ``_FILE`` and ``_ENV`` variants.

- The ``_FILE`` variant expects its value to be a file name.  The file's contents will be read and used as the value.
- The ``_ENV`` variant expects its value to be the name of another environment variable. The value of the other environment variable is then used as the final value. This is convenient in deployment scenarios where relevant values are auto populated into fixed environment variables.

.. note::

   For |Gel| versions before 6.0 the prefix for all environment variables is ``EDGEDB_`` instead of ``GEL_``.

GEL_DEBUG_HTTP_INJECT_CORS
--------------------------

Set to ``1`` to have Gel send appropriate CORS headers with HTTP responses.

.. note::

    This is set to ``1`` by default for Gel Cloud instances.


.. _ref_reference_envvar_admin_ui:

GEL_SERVER_ADMIN_UI
-------------------

Set to ``enabled`` to enable the web-based admininstrative UI for the instance.

Maps directly to the |gel-server| flag ``--admin-ui``.


GEL_SERVER_ALLOW_INSECURE_BINARY_CLIENTS
----------------------------------------

.. warning:: Deprecated

    Use :gelenv:`SERVER_BINARY_ENDPOINT_SECURITY` instead.

Specifies the security mode of the server's binary endpoint. When set to ``1``,
non-TLS connections are allowed. Not set by default.

.. warning::

    Disabling TLS is not recommended in production.


GEL_SERVER_ALLOW_INSECURE_HTTP_CLIENTS
--------------------------------------

.. warning:: Deprecated

    Use :gelenv:`SERVER_HTTP_ENDPOINT_SECURITY` instead.

Specifies the security mode of the server's HTTP endpoint. When set to ``1``,
non-TLS connections are allowed. Not set by default.

.. warning::

    Disabling TLS is not recommended in production.


.. _ref_reference_docker_gel_server_backend_dsn:

GEL_SERVER_BACKEND_DSN / _FILE / _ENV
-------------------------------------

Specifies a PostgreSQL connection string in the `URI format`_.  If set, the
PostgreSQL cluster specified by the URI is used instead of the builtin
PostgreSQL server.  Cannot be specified alongside :gelenv:`SERVER_DATADIR`. Maps directly to the |gel-server| flag ``--backend-dsn``.

The ``_FILE`` and ``_ENV`` variants are also supported.

.. _URI format:
   https://www.postgresql.org/docs/13/libpq-connect.html#id-1.7.3.8.3.6

GEL_SERVER_MAX_BACKEND_CONNECTIONS
----------------------------------

The maximum NUM of connections this Gel instance could make to the backend
PostgreSQL cluster. If not set, Gel will detect and calculate the NUM:
RAM/100MiB for local Postgres, or pg_settings.max_connections for remote
Postgres minus the NUM of ``--reserved-pg-connections``.

GEL_SERVER_BINARY_ENDPOINT_SECURITY
-----------------------------------

Specifies the security mode of the server's binary endpoint. When set to
``optional``, non-TLS connections are allowed. Default is ``tls``.

.. warning::

    Disabling TLS is not recommended in production.


GEL_SERVER_BIND_ADDRESS / _FILE / _ENV
--------------------------------------

Specifies the network interface on which Gel will listen. Maps directly to the |gel-server| flag ``--bind-address``.

The ``_FILE`` and ``_ENV`` variants are also supported.


GEL_SERVER_BOOTSTRAP_COMMAND
----------------------------

Useful to fine-tune initial user creation and other initial setup. Maps directly to the |gel-server| flag ``--bootstrap-command``.

The ``_FILE`` and ``_ENV`` variants are also supported.

.. note::

    A create branch statement (i.e., :eql:stmt:`create empty branch`, :eql:stmt:`create schema branch`, or :eql:stmt:`create data branch`) cannot be combined in a block with any other statements. Since all statements in :gelenv:`SERVER_BOOTSTRAP_COMMAND` run in a single block, it cannot be used to create a branch and, for example, create a user on that branch.

    For Docker deployments, you can instead write :ref:`custom scripts to run before migrations <ref_guide_deployment_docker_custom_bootstrap_scripts>`.  These are placed in ``/gel-bootstrap.d/``. By writing your ``create branch`` statements in one ``.edgeql`` file each placed in ``/gel-bootstrap.d/`` and other statements in their own file, you can create branches and still run other EdgeQL statements to bootstrap your instance.

    Note that for |EdgeDB| versions prior to 5.0, paths contain "edgedb" instead of "gel", so ``/gel-bootstrap.d/`` becomes ``/edgedb-bootstrap.d/``.

GEL_SERVER_BOOTSTRAP_ONLY
-------------------------

When set, bootstrap the database cluster and exit. Not set by default.


.. _ref_reference_docker_gel_server_datadir:

GEL_SERVER_DATADIR
------------------

Specifies a path where the database files are located.  Default is
``/var/lib/gel/data``.  Cannot be specified alongside
:gelenv:`SERVER_BACKEND_DSN`.

Maps directly to the |gel-server| flag ``--data-dir``.


GEL_SERVER_DEFAULT_AUTH_METHOD / _FILE / _ENV
---------------------------------------------

Optionally specifies the authentication method used by the server instance.  Supported values are ``SCRAM`` (the default) and ``Trust``. When set to ``Trust``, the database will allow complete unauthenticated access for all who have access to the database port.

This is often useful when setting an admin password on an instance that lacks one.

Use at your own risk and only for development and testing.

The ``_FILE`` and ``_ENV`` variants are also supported.


GEL_SERVER_HTTP_ENDPOINT_SECURITY
---------------------------------

Specifies the security mode of the server's HTTP endpoint. When set to ``optional``, non-TLS connections are allowed. Default is ``tls``.

.. warning::

    Disabling TLS is not recommended in production.


GEL_SERVER_INSTANCE_NAME
------------------------

Specify the server instance name.


GEL_SERVER_JWS_KEY_FILE
-----------------------

Specifies a path to a file containing a public key in PEM format used to verify JWT signatures. The file could also contain a private key to sign JWT for local testing.


GEL_SERVER_LOG_LEVEL
--------------------

Set the logging level. Default is ``info``. Other possible values are ``debug``, ``warn``, ``error``, and ``silent``.


GEL_SERVER_PORT / _FILE / _ENV
------------------------------

Specifies the network port on which Gel will listen. Default is ``5656``. Maps directly to the |gel-server| flag ``--port``.

The ``_FILE`` and ``_ENV`` variants are also supported.


GEL_SERVER_RUNSTATE_DIR
-----------------------

Specifies a path where Gel will place its Unix socket and other transient files. Maps directly to the |gel-server| flag ``--runstate-dir``.


GEL_SERVER_SECURITY
-------------------

When set to ``insecure_dev_mode``, sets :gelenv:`SERVER_DEFAULT_AUTH_METHOD` to ``Trust``, and :gelenv:`SERVER_TLS_CERT_MODE` to ``generate_self_signed`` (unless an explicit TLS certificate is specified). Finally, if this option is set, the server will accept plaintext HTTP connections.  Maps directly to the |gel-server| flag ``--security``.

.. warning::

    Disabling TLS is not recommended in production.



GEL_SERVER_TLS_CERT_FILE
------------------------

The TLS certificate file, exclusive with :gelenv:`SERVER_TLS_CERT_MODE=generate_self_signed`. Maps directly to the |gel-server| flag ``--tls-cert-file``.

GEL_SERVER_TLS_KEY_FILE
-----------------------

The TLS private key file, exclusive with :gelenv:`SERVER_TLS_CERT_MODE=generate_self_signed`. Maps directly to the |gel-server| flag ``--tls-key-file``.


GEL_SERVER_TLS_CERT_MODE / _FILE / _ENV
---------------------------------------

Specifies what to do when the TLS certificate and key are either not specified or are missing.

- When set to ``require_file``, the TLS certificate and key must be specified in the :gelenv:`SERVER_TLS_CERT` and :gelenv:`SERVER_TLS_KEY` variables and both must exist.
- When set to ``generate_self_signed`` a new self-signed certificate and private key will be generated and placed in the path specified by :gelenv:`SERVER_TLS_CERT` and :gelenv:`SERVER_TLS_KEY`, if those are set.  Otherwise, the generated certificate and key are stored as ``edbtlscert.pem`` and ``edbprivkey.pem`` in :gelenv:`SERVER_DATADIR`, or, if :gelenv:`SERVER_DATADIR` is not set, they will be placed in ``/etc/ssl/gel``.

Default is ``generate_self_signed`` when :gelenv:`SERVER_SECURITY=insecure_dev_mode`. Otherwise, the default is ``require_file``.

Maps directly to the |gel-server| flag ``--tls-cert-mode``.

The ``_FILE`` and ``_ENV`` variants are also supported.

Docker image specific variables
===============================

These variables are only used by the Docker image. Setting these variables outside that context will have no effect.


GEL_DOCKER_ABORT_CODE
---------------------

If the process fails, the arguments are logged to stderr and the script is terminated with this exit code. Default is ``1``.


GEL_DOCKER_APPLY_MIGRATIONS
---------------------------

The container will attempt to apply migrations in ``dbschema/migrations`` unless this variable is set to ``never``.

**Values**: ``always`` (default), ``never``


GEL_DOCKER_BOOTSTRAP_TIMEOUT_SEC
--------------------------------

Sets the number of seconds to wait for instance bootstrapping to complete before timing out. Default is ``300``.


GEL_DOCKER_LOG_LEVEL
--------------------

Change the logging level for the docker container.

**Values**: ``trace``, ``debug``, ``info`` (default), ``warn``, ``error``


GEL_DOCKER_SHOW_GENERATED_CERT
------------------------------

Shows the generated TLS certificate in console output.

**Values**: ``always`` (default), ``never``


GEL_SERVER_BINARY
-----------------

Sets the Gel server binary to run. Default is |gel-server|.


GEL_SERVER_BOOTSTRAP_COMMAND_FILE
---------------------------------

Run the script when initializing the database. The script is run by the default user within the default |branch|. May be used with or without :gelenv:`SERVER_BOOTSTRAP_ONLY`.


GEL_SERVER_COMPILER_POOL_MODE
-----------------------------

Choose a mode for the compiler pool to scale. ``fixed`` means the pool will not scale and sticks to :gelenv:`SERVER_COMPILER_POOL_SIZE`, while ``on_demand`` means the pool will maintain at least 1 worker and automatically scale up (to :gelenv:`SERVER_COMPILER_POOL_SIZE` workers ) and down to the demand.

**Values**: ``fixed``, ``on_demand``

Default is ``fixed`` in production mode and ``on_demand`` in development mode.


GEL_SERVER_COMPILER_POOL_SIZE
-----------------------------

When :gelenv:`SERVER_COMPILER_POOL_MODE` is ``fixed``, this setting is the exact size of the compiler pool. When :gelenv:`SERVER_COMPILER_POOL_MODE` is ``on_demand``, this will serve as the maximum size of the compiler pool.


GEL_SERVER_EMIT_SERVER_STATUS
-----------------------------

Instruct the server to emit changes in status to *DEST*, where *DEST* is a URI specifying a file (``file://<path>``), or a file descriptor (``fd://<fileno>``).  If the URI scheme is not specified, ``file://`` is assumed.


GEL_SERVER_EXTRA_ARGS
---------------------

Additional arguments to pass when starting the Gel server.


GEL_SERVER_PASSWORD / _FILE / _ENV
----------------------------------

The password for the default superuser account (or the user specified in :gelenv:`SERVER_USER`) will be set to this value. If no value is provided, a password will not be set, unless set via :gelenv:`SERVER_BOOTSTRAP_COMMAND`. (If a value for :gelenv:`SERVER_BOOTSTRAP_COMMAND` is provided, this variable will be ignored.)

The ``_FILE`` and ``_ENV`` variants are also supported.


GEL_SERVER_PASSWORD_HASH / _FILE / _ENV
---------------------------------------

A variant of :gelenv:`SERVER_PASSWORD`, where the specified value is a hashed password verifier instead of plain text.

If :gelenv:`SERVER_BOOTSTRAP_COMMAND` is set, this variable will be ignored.

The ``_FILE`` and ``_ENV`` variants are also supported.


GEL_SERVER_TENANT_ID
--------------------

Specifies the tenant ID of this server when hosting multiple Gel instances on one Postgres cluster. Must be an alphanumeric ASCII string, maximum 10 characters long.


GEL_SERVER_UID
--------------

Specifies the ID of the user which should run the server binary. Default is ``1``.


GEL_SERVER_USER
---------------

If set to anything other than the default username |admin|, the username specified will be created. The user defined here will be the one assigned the password set in :gelenv:`SERVER_PASSWORD` or the hash set in :gelenv:`SERVER_PASSWORD_HASH`.
