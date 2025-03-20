.. _ref_clients_index:

================
Client Libraries
================

.. toctree::
    :maxdepth: 2
    :glob:
    :hidden:

    js/index
    python/index
    Go <https://pkg.go.dev/github.com/geldata/gel-go>
    Rust <https://docs.rs/gel-tokio/latest/gel_tokio/>
    http/index
    graphql/index

Client philosophy
=================

To connect your application to a |Gel| instance, you can use one of our official client libraries that speaks the Gel binary protocol. The client libraries are higher level than typical database drivers, and are designed to provide a fully-featured API for working with |Gel| instances.

* Connect by convention
* Connection pooling
* Automatic transaction retries
* Layered client configration

Connection
----------

Typical database drivers require you to figure out how to pass the correct connection string (called a DSN, or data source name) to the driver. This is a bit of a pain, and is error prone.

Our client libraries take a different approach. Instead of needing to pass a DSN into our client creation function, the client libraries use a convention to discover the connection information in a way that allows you to not have to vary the code you write based on where you run your application.

* Local development: We suggest using our :ref:`projects <ref_guide_using_projects>` feature to manage your local instance. We handle creating credentials, and clients automatically know how to resolve the connection information for projects initialized in your project directory. We also support Docker Compose.
* Production: For production, we recommend using environment variables to specify connection information to your |Gel| Cloud instance or remote self-hosted instance.

This approach allows you to write code that does not need to contain any error-prone conditional logic. For more information on how to configure your connection for development and production, see :ref:`the reference for connection environments <ref_reference_connection_environments>`.

Connection pooling
------------------

When you create a client instance, the library will automatically create a pool of connections to the Gel server instance to maximize parallelism and throughput. We use the safest isolation level of ``SERIALIZABLE`` to ensure consistent results across high-concurrency scenarios.

Transactions
------------

Transactions are an important part of working with databases, and our client libraries are designed with a higher-level API for working with transactions that will automatically retry failures for certain classes of transaction errors. For instance, one common failure mode is a serialization error, which can happen when two transactions that are trying to modify the same data attempt to commit at the same time. The database will pick one of the transactions to commit, and the other will fail. In typical database drivers, you would need to handle this in your application code, but in our client libraries, you don't need to worry about it: we will simply retry the transaction for you in this case.

The behavior of transaction retries can be customized in the client configuration, which we will detail in full in the documentation for each client library.

Layered client configuration
----------------------------

Each client library has a number of configuration options that you can set to customize the behavior of the client. Instead of needing to manage multiple pools across multiple client instances, the methods used for configuring the client will return an instance that shares the same connection pool and configuration as the base client instance. This is useful if different parts of your application need to configure the client differently at runtime, such as setting globals, disabling access policies, setting a longer query timeout, etc.

Alternative Protocols
=====================

In addition to our official client libraries, you can also connect to a running |Gel| instance over HTTP or GraphQL. This can be helpful for languages that are not yet supported, or in certain constrained environments.

* :ref:`EdgeQL over HTTP <ref_edgeql_http>`
* :ref:`GraphQL <ref_graphql_protocol>`