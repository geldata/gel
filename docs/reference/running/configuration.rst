.. _ref_admin_config:

====================
Server configuration
====================

|Gel| exposes a number of configuration parameters that affect its behavior.  In this section we review the ways to change the server configuration, as well as detail each available configuration parameter.


Setting configuration parameters
================================

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
