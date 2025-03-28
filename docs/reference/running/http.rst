.. _ref_reference_http_api:

========
HTTP API
========

Gel provides HTTP endpoints that allow you to monitor the health and performance of your instance. You can use these endpoints to check if your instance is alive and ready to receive queries, as well as to collect metrics about its operation.

Your branch's URL takes the form of ``http://<hostname>:<port>``.

Here's how to determine your local Gel instance's HTTP server URL:

- The ``hostname`` will be ``localhost``

- Find the ``port`` by running :gelcmd:`instance list`. This will print a table of all Gel instances on your machine, including their associated port number.

To determine the URL of a remote instance you have linked with the CLI, you can get both the hostname and port of the instance from the "Port" column of the :gelcmd:`instance list` table (formatted as ``<hostname>:<port>``).

.. _ref_edgeql_http_health_checks:
.. _ref_reference_health_checks:
.. _ref_guide_deployment_health_checks:

Health Checks
=============

|Gel| exposes endpoints to check for aliveness and readiness of your database
instance.

Aliveness
---------

Check if your instance is alive.

.. code-block::

    http://<hostname>:<port>/server/status/alive

If your instance is alive, it will respond with a ``200`` status code and ``"OK"`` as the payload. Otherwise, it will respond with a ``50x`` or a network error.

Readiness
---------

Check if your instance is ready to receive queries.

.. code-block::

    http://<hostname>:<port>/server/status/ready

If your instance is ready, it will respond with a ``200`` status code and ``"OK"`` as the payload. Otherwise, it will respond with a ``50x`` or a network error.


.. _ref_observability:

Observability
=============

Retrieve instance metrics.

.. code-block::

    http://<hostname>:<port>/metrics

All Gel instances expose a Prometheus-compatible endpoint available via GET request. The following metrics are made available.

System
------

``compiler_process_spawns_total``
  **Counter.** Total number of compiler processes spawned.

``compiler_processes_current``
  **Gauge.** Current number of active compiler processes.

``branches_current``
  **Gauge.** Current number of branches.

Backend connections and performance
-----------------------------------

``backend_connections_total``
  **Counter.** Total number of backend connections established.

``backend_connections_current``
  **Gauge.** Current number of active backend connections.

``backend_connection_establishment_errors_total``
  **Counter.** Number of times the server could not establish a backend connection.

``backend_connection_establishment_latency``
  **Histogram.** Time it takes to establish a backend connection, in seconds.

``backend_query_duration``
  **Histogram.** Time it takes to run a query on a backend connection, in seconds.

Client connections
------------------

``client_connections_total``
  **Counter.** Total number of clients.

``client_connections_current``
  **Gauge.** Current number of active clients.

``client_connections_idle_total``
  **Counter.** Total number of forcefully closed idle client connections.

``client_connection_duration``
  **Histogram.** Time a client connection is open.

Queries and compilation
-----------------------

``edgeql_query_compilations_total``
  **Counter.** Number of compiled/cached queries or scripts since instance startup. A query is compiled and then cached on first use, increasing the ``path="compiler"`` parameter. Subsequent uses of the same query only use the cache, thus only increasing the ``path="cache"`` parameter.

``edgeql_query_compilation_duration``
  Deprecated in favor of ``query_compilation_duration[interface="edgeql"]``.

  **Histogram.** Time it takes to compile an EdgeQL query or script, in seconds.

``graphql_query_compilations_total``
  **Counter.** Number of compiled/cached GraphQL queries since instance startup. A query is compiled and then cached on first use, increasing the ``path="compiler"`` parameter. Subsequent uses of the same query only use the cache, thus only increasing the ``path="cache"`` parameter.

``sql_queries_total``
  **Counter.** Number of SQL queries since instance startup.

``sql_compilations_total``
  **Counter.** Number of SQL compilations since instance startup.

``query_compilation_duration``
  **Histogram.** Time it takes to compile a query or script, in seconds.

``queries_per_connection``
  **Histogram.** Number of queries per connection.

``query_size``
  **Histogram.** Number of bytes in a query, where the label ``interface=edgeql`` means the size of an EdgeQL query, ``=graphql`` for a GraphQL query, ``=sql`` for a readonly SQL query from the user, and ``=compiled`` for a backend SQL query compiled and issued by the server.

Auth Extension
--------------

``auth_api_calls_total``
  **Counter.** Number of API calls to the Auth extension.

``auth_ui_renders_total``
  **Counter.** Number of UI pages rendered by the Auth extension.

``auth_providers``
  **Histogram.** Number of Auth providers configured.

``auth_successful_logins_total``
  **Counter.** Number of successful logins in the Auth extension.

Errors
------

``background_errors_total``
  **Counter.** Number of unhandled errors in background server routines.

``transaction_serialization_errors_total``
  **Counter.** Number of transaction serialization errors.

``connection_errors_total``
  **Counter.** Number of network connection errors.