.. _ref_clients_index:

================
Client Libraries
================

.. toctree::
    :maxdepth: 2
    :glob:
    :hidden:

    connection
    js/index
    python/index
    go/index
    http/index
    graphql/index

To connect your application to a |Gel| instance, you can use one of our official client libraries that speaks the Gel binary protocol. The client libraries are higher level than typical database drivers, and are designed [something something something].

* Connect by convention
* Connection pooling
* Automatic transaction retries
* Layered client configration

Connection
==========

Typical database drivers require you to figure out how to pass the correct connection string (called a DSN, or data source name) to the driver. This is a bit of a pain, and is error prone.

Our client libraries take a different approach. Instead of needing to pass a DSN into our client creation function, the client libraries use a convention to discover the connection information in a way that allows you to not have to vary the code you write based on where you run your application.

* Local development: We suggest using our :ref:`projects <ref_guide_using_projects>` feature to manage your local instance. We handle creating credentials, and clients automatically know how to resolve the connection information for projects initialized in your project directory. We also support Docker Compose.
* Production: For production, we recommend using environment variables to set specify connection information. You can either specify the full DSN using :gelenv:`DSN`, or use environment variables that configure the various parts of the DSN. Each part of the DSN has a fallback default, so in many cases you don't need to set all of the possible environment variables.

This approach allows you to write code that does not need to contain any error-prone conditional logic. The various parts of the DSN and client connection behavior are also layered in a way that allows you to provide overrides in certain unusual scenarios giving maximum flexibility.

DSN
---

The DSN is a string that contains the connection information for the Gel server instance. It has the following format:

.. code-block:: text

    gel://user:password@host:port/branch

The defaults and environment variables for each part of the DSN are as follows:

.. list-table:: DSN Parameters
   :header-rows: 1

   * - DSN Parameter
     - CLI flag
     - Environment Variable
     - createClient property
   * - ``user``
     - ``--user``
     - :gelcmd:`USER`
     - ``user``
   * - ``password``
     - ``--password``
     - :gelenv:`PASSWORD`
     - ``password``
   * - ``host``
     - ``--host`` or ``-h``
     - :gelenv:`HOST`
     - ``host``
   * - ``port``
     - ``--port`` or ``-p``
     - :gelenv:`PORT`
     - ``port``
   * - ``branch``
     - ``--branch`` or ``-b``
     - :gelenv:`BRANCH`
     - ``branch``

Additional client configuration
-------------------------------

In addition to the DSN, there are a few additional configuration options that can be set to configure client behavior. When specifying these options as part of the DSN string directly, they are specified as query parameters.

.. list-table:: Additional Client Configuration
   :header-rows: 1

   * - DSN query parameter
     - CLI flag
     - Environment Variable
     - createClient property
   * - ``tls_ca_file``
     - ``--tls-ca-file``
     - :gelenv:`TLS_CA_FILE`
     - ``tlsCAFile``
   * - ``tls_server_name``
     - ``--tls-server-name``
     - :gelenv:`TLS_SERVER_NAME`
     - ``tlsServerName``
   * - ``tls_security``
     - ``--tls-security``
     - :gelenv:`CLIENT_TLS_SECURITY`
     - ``tlsSecurity``
   * - (empty)
     - (empty)
     - :gelenv:`CLIENT_SECURITY`
     - (empty)
   * - ``secret_key``
     - ``--secret-key``
     - :gelenv:`SECRET_KEY`
     - ``secretKey``
   * - ``wait_until_available``
     - ``--wait-until-available``
     - :gelenv:`WAIT_UNTIL_AVAILABLE`
     - ``waitUntilAvailable``
   * - ``connect_timeout``
     - ``--connect-timeout``
     - :gelenv:`CONNECT_TIMEOUT`
     - ``timeout``

* :gelcmd:`TLS_CA_FILE`
  TLS is required to connect to any Gel instance. To do so, the client needs a reference to the root certificate of your instance's certificate chain. Typically this will be handled for you when you create a local instance or link a remote one.

  If you're using a globally trusted CA like Let's Encrypt, the root certificate will almost certainly exist already in your system's global certificate pool. In this case, you won't need to specify this path; it will be discovered automatically by the client.

  If you're self-issuing certificates, you must download the root certificate and provide a path to its location on the filesystem. Otherwise TLS will fail to connect.
* :gelcmd:`TLS_SERVER_NAME`
  If for some reason target instance IP address can't be resolved from the hostname, you can provide the SNI (server name indication) to use for TLS connections.
* :gelenv:`CLIENT_TLS_SECURITY`

  Sets the TLS security mode. Determines whether certificate and hostname
  verification is enabled. Possible values:

  - ``"strict"`` (**default**) — certificates and hostnames will be verified
  - ``"no_host_verification"`` — verify certificates but not hostnames
  - ``"insecure"`` — client libraries will trust self-signed TLS certificates.
    Useful for self-signed or custom certificates.

  This setting defaults to ``"strict"`` unless a custom certificate is
  supplied, in which case it is set to ``"no_host_verification"``.

* :gelenv:`CLIENT_SECURITY`

  Provides some simple "security presets".

  Currently there is only one valid value: ``insecure_dev_mode``. Setting
  :gelenv:`CLIENT_SECURITY=insecure_dev_mode` disables all TLS security
  measures. Currently it is equivalent to setting
  :gelenv:`CLIENT_TLS_SECURITY=insecure` but it may encompass additional
  configuration settings later.  This is most commonly used when developing
  locally with Docker.

* :gelenv:`SECRET_KEY`
  Specifies the secret key to use for authentication with |Gel| Cloud instances. This is not required when connecting to your own |Gel| Cloud instance if you have logged in with :gelcmd:`cloud login`.

* :gelenv:`WAIT_UNTIL_AVAILABLE`
  In case the connection can't be established, keep retrying up to the given timeout value. The timeout value must be given using time units (e.g. ``1hr``, ``10min``, ``30sec``, ``500ms``, etc.).

* :gelenv:`CONNECT_TIMEOUT`
  Specifies a timeout period. In the event Gel doesn't respond in this period, the command will fail (or retry if --wait-until-available is also specified). The timeout value must be given using time units (e.g. hr, min, sec, ms, etc.). The default value is 10s.

Connection pooling
==================

When you create a client instance, the library will automatically create a pool of connections to the Gel server instance.

Transactions
============

Transactions are an important part of working with databases, and our client libraries are designed with a higher-level API for working with transactions that will automatically retry failures for certain classes of transaction errors. For instance, one common failure mode is a serialization error, which can happen when two transactions that are trying to modify the same data attempt to commit at the same time. The database will pick one of the transactions to commit, and the other will fail. In typical database drivers, you would need to handle this in your application code, but in our client libraries, you don't need to worry about it: we will simply retry the transaction for you in this case.

The behavior of transaction retries can be customized in the client configuration, which we will detail in full in the documentation for each client library.

Layered client configuration
============================

Each client library has a number of configuration options that you can set to customize the behavior of the client. Instead of needing to manage multiple pools across multiple client instances, the methods used for configuring the client will return an instance that shares the same connection pool and configuration as the base client instance. This is useful if different parts of your application need to configure the client differently at runtime, such as setting globals, disabling access policies, setting a longer query timeout, etc.

Alternative Protocols
=====================

In addition to our official client libraries, you can also connect to a running |Gel| instance over HTTP or GraphQL. This can be helpful for languages that are not yet supported, or in certain constrained environments.

* :ref:`EdgeQL over HTTP <ref_edgeql_http>`
* :ref:`GraphQL <ref_graphql_protocol>`