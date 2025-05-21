.. _gel-python-client:

.. py:currentmodule:: gel


======
Client
======

The ``gel.Client`` class implements the basic functionality required to establish a pool of connections to your database, execute queries with some context and parameters, manage transactions, and decode results into Python types.

We provide both a :ref:`blocking <gel-python-blocking-api-client>` and an :ref:`asyncio <gel-python-async-api-client>` implementation of the client. For the following examples we will use the :ref:`asyncio <gel-python-async-api-client>` implementation, but the blocking API is fundamentally identical.

Creating a client
=================

The ``gel`` package exposes a :py:func:`~gel.create_async_client` function that can be used to create a new :py:class:`~gel.AsyncIOClient` instance. This client instance manages a pool of connections to the database which it discovers automatically from either being in a :gelcmd:`project init` directory or being provided connection details via Environment Variables. See :ref:`the environment section of the connection reference <ref_reference_connection_environments>` for more details and options.

.. note::

  If you're using |Gel| Cloud to host your development instance, you can use the :gelcmd:`cloud login` command to authenticate with |Gel| Cloud and then use the :gelcmd:`project init --server-instance <instance-name>` command to create a local project-linked instance that is linked to an Gel Cloud instance. For more details, see :ref:`the Gel Cloud guide <ref_guide_cloud>`.

.. code-block:: python

  import asyncio
  import gel

  client = gel.create_async_client()

Checking connection status
--------------------------

The client maintains a dynamically sized *pool* of connections under the hood.  These connections are initialized *lazily*, so no connection will be established until the first time you execute a query.

If you want to explicitly ensure that the client is connected without running a query, use the ``.ensure_connected()`` method. This can be useful to catch any errors resulting from connection mis-configuration by triggering the first connection attempt explicitly.

.. code-block:: python

  import asyncio
  import gel

  client = gel.create_async_client()

  async def main():
    await client.ensure_connected()

Running queries
===============

The ``gel.Client`` class provides a number of methods for running queries. The simplest is ``query``, which runs a query and returns the result as a list of results.

.. code-block:: python

  import asyncio
  import gel

  client = gel.create_async_client()

  async def main():
    await client.ensure_connected()
    result = await client.query("select 2 + 2;")
    print(result)

  asyncio.run(main())

  # Output:
  # [4]

Parameters
----------

If your query contains parameters (e.g. ``$foo``), you can pass in values. Positional parameters are passed as positional arguments, and named parameters are passed as keyword arguments. You cannot mix positional and named parameters in the same query.

.. code-block:: python

  import asyncio
  import gel

  client = gel.create_async_client()

  async def main():
    await client.ensure_connected()
    result = await client.query("select 2 + $addend;", addend=2)
    print(result)

  asyncio.run(main())

  # Output:
  # [4]

.. note::

  Parameters can only be scalars or arrays of scalars. See :ref:`parameters <ref_eql_params>` for more details.

Cardinality
-----------

The ``query`` method always returns a list of results. It places no constraints on cardinality.

.. code-block:: python

  await client.query("select 2 + 2;") # list[int64]: [4]
  await client.query("select <int64>{};") # list[int64]: []
  await client.query("select {1, 2, 3};") # list[int64]: [1, 2, 3]

If you know your query will only return a single element, you can tell |Gel| to expect a *singleton result* by using the ``query_single`` method. This is intended for queries that return *zero or one* elements. If the query returns a set with more than one elements, the ``Client`` will raise a runtime error.

.. note::

  Remember that arrays and tuples are considered an element of the result set, so if you're returning exactly one array or tuple, the result will be an array.

.. code-block:: python

  await client.query_single("select 2 + 2;") # int64 | None: 4
  await client.query_single("select [1, 2, 3];") # list[int64] | None: [1, 2, 3]
  await client.query_single("select <int64>{};") # int64 | None: None
  await client.query_single("select {1, 2, 3};") # Raises a ResultCardinalityMismatchError

Use ``query_required_single`` for queries that return *exactly one* element. If the query returns an empty set or a set with multiple elements, the ``Client`` will raise a runtime error.

.. code-block:: python

  await client.query_required_single("select 2 + 2;") # int64: 4
  await client.query_required_single("select <int64>{};") # Raises a NoDataError
  await client.query_required_single("select {1, 2, 3};") # Raises a ResultCardinalityMismatchError

If you do not need or expect a result, you can use ``execute`` which will return ``None``. This is often useful for mutations where you do not need to retrieve a result.

.. code-block:: python

  await client.execute("insert Movie { title := 'Iron Man' }") # None

JSON results
------------

The ``Client`` provides additional methods for running queries and retrieving results as a *serialized JSON string*. This serialization happens inside the database and is typically more performant than running ``JSON.stringify`` yourself.


.. code-block:: python

  await client.query_json("select 2 + 2;")
  # "[4]"

  await client.query_single_json("select <int64>{};")
  # "null"

  await client.query_required_single_json("select 3.14;")
  # "3.14"

  await client.query_required_json("select 3.14;")
  # "3.14"

.. warning::

  Caution is advised when reading ``decimal`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` number can be losslessly represented in JSON. However, the default JSON decoder in Python will read all such numbers as ``float`` values, which may result in errors or precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as ``Decimal``.

SQL queries
-----------

.. versionadded:: 6.0

The ``querySQL`` method allows you to run a SQL query and return the result as list of dictionaries.

.. code-block:: python

  await client.query_sql("select 2 + 2;")
  # [{'col~1': 4}]

  await client.query_sql("select 42 as a;")
  # [{'a': 42}]

Scripts
-------

Both ``execute`` and the ``query*`` methods support scripts (queries containing multiple statements). The statements, like all queries, are run in an implicit transaction (unless already in an explicit transaction), so the whole script remains atomic. For the ``query*`` methods only the result of the final statement in the script will be returned.

.. code-block:: python

  result = await client.query("""
    insert Movie { title := 'Iron Man' };
    insert Person { name := 'Robert Downey Jr.' };
  """)
  print(result)
  # [{"id": "00000000-0000-0000-0000-000000000000"}]

For more fine grained control of atomic exectution of multiple statements, use the :py:meth:`transaction() <gel.AsyncIOClient.transaction>` API.

Transactions
------------

We execute queries on the ``tx`` object given in for expression, rather than on the original ``client`` object.

.. code-block:: python

  async for tx in client.transaction():
      async with tx:
          await tx.execute("insert Movie { title := 'Iron Man' }")
          await tx.execute("insert Person { name := 'Robert Downey Jr.' }")

The ``transaction()`` API guarantees that:

1. Transactions are executed atomically;
2. If a transaction fails due to retryable error (like a network failure or a concurrent update error), the transaction would be retried;
3. If any other, non-retryable error occurs, the transaction is rolled back and the ``transaction()`` block throws.

The transaction object exposes the same ``query`` and ``execute`` methods as the ``Client`` object, with the only difference that queries will run within the current transaction and can be retried automatically.

.. warning::

  In transactions, the entire nested code block can be re-run, including any non-querying Python code. In general, the code inside the transaction block **should not have side effects or run for a significant amount of time**. Consider the following example:

  .. code-block:: python
    :caption: Don't do this

      email = "timmy@example.com";

      async for tx in client.transaction():
          async with tx:
              await tx.execute(
                  'insert User { email := <str>$email }',
                  email=email,
              )

              await sendWelcomeEmail(email)

              await tx.execute(
                  """
                  insert LoginHistory {
                    user := (select User filter .email = <str>$email),
                    timestamp := datetime_current()
                  }
                  """,
                  email=email
              )

  In the above example, the welcome email may be sent multiple times if the transaction block is retried. Additionally, transactions allocate expensive server resources. Having too many concurrently running long-running transactions will negatively impact the performance of the DB server.

To rollback a transaction that is in progress raise an exception.

.. code-block:: python

   class RollBack(Exception):
       "A user defined exception."

   try:
       for tx in client.transaction():
           with tx:
               raise RollBack
   except RollBack:
       pass

See also:

* RFC1004_
* :py:meth:`Client.transaction()`

Configuring clients
===================

Clients can be configured using a set of methods that start with ``with``. One you'll likely use often in application code is the ``with_globals`` which sets the global variables in the query.

.. code-block:: python

    client = gel.create_async_client()
    await client.with_globals(
        current_user_id="00000000-0000-0000-0000-000000000000",
    ).query_single(
        "select User { * } filter .id ?= global current_user_id;"
    )

.. note::

  These methods return a *new Client instance* that *shares a connection pool* with the original client. This is important. Each call to ``create_async_client`` instantiates a new connection pool, so in typical usage you should create a single shared client instance and configure it at runtime as needed.


.. _gel-python-blocking-api-reference:

Blocking client reference
=========================


.. _gel-python-blocking-api-client:

Client
------

.. py:function:: create_client(dsn=None, *, \
            host=None, port=None, \
            user=None, password=None, \
            secret_key=None, \
            database=None, \
            timeout=60, \
            concurrency=None)

    Create a blocking client with a lazy connection pool.

    The connection parameters may be specified either as a connection URI in *dsn*, or as specific keyword arguments, or both.  If both *dsn* and keyword arguments are specified, the latter override the corresponding values parsed from the connection URI.

    If no connection parameter is specified, the client will try to search in environment variables and then the current project, see :ref:`Client Library Connection <gel_client_connection>` docs for more information.

    Returns a new :py:class:`Client` object.

    :param dsn:
        If this parameter does not start with |geluri| then this is interpreted as the :ref:`name of a local instance <ref_reference_connection_instance_name>`.

        Otherwise it specifies a single string in the following format: :geluri:`user:password@host:port/database?option=value`.  The following options are recognized: host, port, user, database, password. For a complete reference on DSN, see the :ref:`DSN Specification <ref_dsn>`.

    :param host:
        Database host address as an IP address or a domain name;

        If not specified, the following will be tried, in order:

        - host address(es) parsed from the *dsn* argument,
        - the value of the :gelenv:`HOST` environment variable,
        - ``"localhost"``.

    :param port:
        Port number to connect to at the server host. If multiple host addresses were specified, this parameter may specify a sequence of port numbers of the same length as the host sequence, or it may specify a single port number to be used for all host addresses.

        If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`PORT` environment variable, or ``5656`` if neither is specified.

    :param user:
        The name of the database role used for authentication.

        If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`USER` environment variable, or the operating system name of the user running the application.

    :param database:
        The name of the database to connect to.

        If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`DATABASE` environment variable, or the operating system name of the user running the application.

    :param password:
        Password to be used for authentication, if the server requires one. If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`PASSWORD` environment variable.  Note that the use of the environment variable is discouraged as other users and applications may be able to read it without needing specific privileges.

    :param secret_key:
        Secret key to be used for authentication, if the server requires one. If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`SECRET_KEY` environment variable.  Note that the use of the environment variable is discouraged as other users and applications may be able to read it without needing specific privileges.

    :param float timeout:
        Connection timeout in seconds.

    :return: An instance of :py:class:`Client`.

    The APIs on the returned client instance can be safely used by different threads, because under the hood they are checking out different connections from the pool to run the queries:

    * :py:meth:`Client.query()`
    * :py:meth:`Client.query_single()`
    * :py:meth:`Client.query_required_single()`
    * :py:meth:`Client.query_json()`
    * :py:meth:`Client.query_single_json()`
    * :py:meth:`Client.query_required_single_json()`
    * :py:meth:`Client.execute()`
    * :py:meth:`Client.transaction()`

    .. code-block:: python

        client = gel.create_client()
        client.query('SELECT {1, 2, 3}')

    The same for transactions:

    .. code-block:: python

        client = gel.create_client()
        for tx in client.transaction():
            with tx:
                tx.query('SELECT {1, 2, 3}')



.. py:class:: Client

    A thread-safe blocking client with a connection pool.

    Blocking clients are created by calling :py:func:`create_client`.


    .. py:method:: query(query, *args, **kwargs)

        Acquire a connection and use it to run a query and return the results as an :py:class:`gel.Set` instance. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            An instance of :py:class:`gel.Set` containing the query result.

        Note that positional and named query arguments cannot be mixed.


    .. py:method:: query_single(query, *args, **kwargs)

        Acquire a connection and use it to run an optional singleton-returning query and return its element. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            Query result.

        The *query* must return no more than one element.  If the query returns more than one element, an ``gel.ResultCardinalityMismatchError`` is raised, if it returns an empty set, ``None`` is returned.

        Note, that positional and named query arguments cannot be mixed.


    .. py:method:: query_required_single(query, *args, **kwargs)

        Acquire a connection and use it to run a singleton-returning query and return its element. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            Query result.

        The *query* must return exactly one element.  If the query returns more than one element, an ``gel.ResultCardinalityMismatchError`` is raised, if it returns an empty set, an ``gel.NoDataError`` is raised.

        Note, that positional and named query arguments cannot be mixed.


    .. py:method:: query_json(query, *args, **kwargs)

        Acquire a connection and use it to run a query and return the results as JSON. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            A JSON string containing an array of query results.

        Note, that positional and named query arguments cannot be mixed.

        .. note::

            Caution is advised when reading ``decimal`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` number can be losslessly represented in JSON. However, the default JSON decoder in Python will read all such numbers as ``float`` values, which may result in errors or precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as ``Decimal``.


    .. py:method:: query_single_json(query, *args, **kwargs)

        Acquire a connection and use it to run an optional singleton-returning query and return its element in JSON. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            Query result encoded in JSON.

        The *query* must return no more than one element.  If the query returns more than one element, an ``gel.ResultCardinalityMismatchError`` is raised, if it returns an empty set, ``"null"`` is returned.

        Note, that positional and named query arguments cannot be mixed.

        .. note::

            Caution is advised when reading ``decimal`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` number can be losslessly represented in JSON. However, the default JSON decoder in Python will read all such numbers as ``float`` values, which may result in errors or precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as ``Decimal``.


    .. py:method:: query_required_single_json(query, *args, **kwargs)

        Acquire a connection and use it to run a singleton-returning query and return its element in JSON. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            Query result encoded in JSON.

        The *query* must return exactly one element.  If the query returns more than one element, an ``gel.ResultCardinalityMismatchError`` is raised, if it returns an empty set, an ``gel.NoDataError`` is raised.

        Note, that positional and named query arguments cannot be mixed.

        .. note::

            Caution is advised when reading ``decimal`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` number can be losslessly represented in JSON. However, the default JSON decoder in Python will read all such numbers as ``float`` values, which may result in errors or precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as ``Decimal``.


    .. py:method:: execute(query)

        Acquire a connection and use it to execute an EdgeQL command (or commands).  The temporary connection is automatically returned back to the pool.

        :param str query: Query text.

        The commands must take no arguments.

        Example:

        .. code-block:: pycon

            >>> client.execute('''
            ...     CREATE TYPE MyType {
            ...         CREATE PROPERTY a -> int64
            ...     };
            ...     FOR x IN {100, 200, 300}
            ...     UNION INSERT MyType { a := x };
            ... ''')

        .. note::
            If the results of *query* are desired, :py:meth:`query`, :py:meth:`query_single` or :py:meth:`query_required_single` should be used instead.

    .. py:method:: transaction()

        Open a retryable transaction loop.

        This is the preferred method of initiating and running a database transaction in a robust fashion.  The ``transaction()`` transaction loop will attempt to re-execute the transaction loop body if a transient error occurs, such as a network error or a transaction serialization error.

        Returns an instance of :py:class:`Retry`.

        See :ref:`gel-python-blocking-api-transaction` for more details.

        Example:

        .. code-block:: python

            for tx in client.transaction():
                with tx:
                    value = tx.query_single("SELECT Counter.value")
                    tx.execute(
                        "UPDATE Counter SET { value := <int64>$value }",
                        value=value + 1,
                    )

        Note that we are executing queries on the ``tx`` object rather than on the original connection.

        .. note::
            The transaction starts lazily. A connection is only acquired from the pool when the first query is issued on the transaction instance.


    .. py:method:: close(timeout=None)

        Attempt to gracefully close all connections in the pool.

        Wait until all pool connections are released, close them and shut down the pool.  If any error (including timeout) occurs in ``close()`` the pool will terminate by calling :py:meth:`~gel.Client.terminate`.

        :param float timeout: Seconds to wait, ``None`` for wait forever.


    .. py:method:: terminate()

        Terminate all connections in the pool.


    .. py:method:: ensure_connected()

        If the client does not yet have any open connections in its pool, attempts to open a connection, else returns immediately.

        Since the client lazily creates new connections as needed (up to the configured ``concurrency`` limit), the first connection attempt will only occur when the first query is run on a client. ``ensureConnected`` can be useful to catch any errors resulting from connection mis-configuration by triggering the first connection attempt explicitly.

    .. py:method:: with_transaction_options(options=None)

        Returns a shallow copy of the client with adjusted transaction options.

        :param TransactionOptions options:
            Object that encapsulates transaction options.

        See :ref:`gel-python-transaction-options` for details.

    .. py:method:: with_retry_options(options=None)

        Returns a shallow copy of the client with adjusted retry options.

        :param RetryOptions options: Object that encapsulates retry options.

        See :ref:`gel-python-retry-options` for details.

    .. py:method:: with_state(state)

        Returns a shallow copy of the client with adjusted state.

        :param State state: Object that encapsulates state.

        See :ref:`gel-python-state` for details.

    .. py:method:: with_default_module(module=None)

        Returns a shallow copy of the client with adjusted default module.

        This is equivalent to using the ``set module`` command, or using the ``reset module`` command when giving ``None``.

        :type module: str or None
        :param module: Adjust the *default module*.

        See :py:meth:`State.with_default_module` for details.

    .. py:method:: with_module_aliases(aliases_dict=None, /, **aliases)

        Returns a shallow copy of the client with adjusted module aliases.

        This is equivalent to using the ``set alias`` command.

        :type aliases_dict: dict[str, str] or None
        :param aliases_dict: This is an optional positional-only argument.

        :param dict[str, str] aliases:
            Adjust the module aliases after applying ``aliases_dict`` if set.

        See :py:meth:`State.with_module_aliases` for details.

    .. py:method:: without_module_aliases(*aliases)

        Returns a shallow copy of the client without specified module aliases.

        This is equivalent to using the ``reset alias`` command.

        :param tuple[str] aliases: Module aliases to reset.

        See :py:meth:`State.without_module_aliases` for details.

    .. py:method:: with_config(config_dict=None, /, **config)

        Returns a shallow copy of the client with adjusted session config.

        This is equivalent to using the ``configure session set`` command.

        :type config_dict: dict[str, object] or None
        :param config_dict: This is an optional positional-only argument.

        :param dict[str, object] config:
            Adjust the config settings after applying ``config_dict`` if set.

        See :py:meth:`State.with_config` for details.

    .. py:method:: without_config(*config_names)

        Returns a shallow copy of the client without specified session config.

        This is equivalent to using the ``configure session reset`` command.

        :param tuple[str] config_names: Config to reset.

        See :py:meth:`State.without_config` for details.

    .. py:method:: with_globals(globals_dict=None, /, **globals_)

        Returns a shallow copy of the client with adjusted global values.

        This is equivalent to using the ``set global`` command.

        :type globals_dict: dict[str, object] or None
        :param globals_dict: This is an optional positional-only argument.

        :param dict[str, object] globals_:
            Adjust the global values after applying ``globals_dict`` if set.

        See :py:meth:`State.with_globals` for details.

    .. py:method:: without_globals(*global_names)

        Returns a shallow copy of the client without specified globals.

        This is equivalent to using the ``reset global`` command.

        :param tuple[str] global_names: Globals to reset.

        See :py:meth:`State.without_globals` for details.


.. _gel-python-blocking-api-transaction:

Transactions
------------

.. py:class:: Transaction()

    Represents a transaction.

    Instances of this type are yielded by a :py:class:`Retry` iterator.

    .. describe:: with c:

        start and commit/rollback the transaction
        automatically when entering and exiting the code inside the
        context manager block.

    .. py:method:: query(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run a query and return the results as an :py:class:`gel.Set` instance. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`Client.query()
        <gel.Client.query>` for details.

    .. py:method:: query_single(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run an optional singleton-returning query and return its element. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`Client.query_single()
        <gel.Client.query_single>` for details.

    .. py:method:: query_required_single(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run a singleton-returning query and return its element. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`Client.query_required_single()
        <gel.Client.query_required_single>` for details.

    .. py:method:: query_json(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run a query and return the results as JSON. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`Client.query_json()
        <gel.Client.query_json>` for details.

    .. py:method:: query_single_json(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run an optional singleton-returning query and return its element in JSON. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`Client.query_single_json()
        <gel.Client.query_single_json>` for details.

    .. py:method:: query_required_single_json(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run a singleton-returning query and return its element in JSON. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`Client.query_requried_single_json()
        <gel.Client.query_required_single_json>` for details.

    .. py:method:: execute(query)

        Acquire a connection if the current transaction doesn't have one yet, and use it to execute an EdgeQL command (or commands).  The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`Client.execute()
        <gel.Client.execute>` for details.

.. py:class:: Retry

    Represents a wrapper that yields :py:class:`Transaction`
    object when iterating.

    See :py:meth:`Client.transaction()` method for
    an example.

    .. py:method:: __next__()

        Yields :py:class:`Transaction` object every time transaction has to
        be repeated.


.. _gel-python-asyncio-api-reference:

AsyncIO client reference
========================

.. _gel-python-async-api-client:

Client
------

.. py:function:: create_async_client(dsn=None, *, \
            host=None, port=None, \
            user=None, password=None, \
            secret_key=None, \
            database=None, \
            timeout=60, \
            concurrency=None)

    Create an asynchronous client with a lazy connection pool.

    The connection parameters may be specified either as a connection URI in *dsn*, or as specific keyword arguments, or both.  If both *dsn* and keyword arguments are specified, the latter override the corresponding values parsed from the connection URI.

    If no connection parameter is specified, the client will try to search in environment variables and then the current project, see :ref:`Client Library Connection <gel_client_connection>` docs for more information.

    Returns a new :py:class:`AsyncIOClient` object.

    :param str dsn:
        If this parameter does not start with |geluri| then this is interpreted as the :ref:`name of a local instance <ref_reference_connection_instance_name>`.

        Otherwise it specifies a single string in the following format: :geluri:`user:password@host:port/database?option=value`.  The following options are recognized: host, port, user, database, password. For a complete reference on DSN, see the :ref:`DSN Specification <ref_dsn>`.

    :param host:
        Database host address as an IP address or a domain name;

        If not specified, the following will be tried, in order:

        - host address(es) parsed from the *dsn* argument,
        - the value of the :gelenv:`HOST` environment variable,
        - ``"localhost"``.

    :param port:
        Port number to connect to at the server host. If multiple host addresses were specified, this parameter may specify a sequence of port numbers of the same length as the host sequence, or it may specify a single port number to be used for all host addresses.

        If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`PORT` environment variable, or ``5656`` if neither is specified.

    :param user:
        The name of the database role used for authentication.

        If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`USER` environment variable, or the operating system name of the user running the application.

    :param database:
        The name of the database to connect to.

        If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`DATABASE` environment variable, or the operating system name of the user running the application.

    :param password:
        Password to be used for authentication, if the server requires one.  If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`PASSWORD` environment variable.  Note that the use of the environment variable is discouraged as other users and applications may be able to read it without needing specific privileges.

    :param secret_key:
        Secret key to be used for authentication, if the server requires one.  If not specified, the value parsed from the *dsn* argument is used, or the value of the :gelenv:`SECRET_KEY` environment variable.  Note that the use of the environment variable is discouraged as other users and applications may be able to read it without needing specific privileges.

    :param float timeout:
        Connection timeout in seconds.

    :param int concurrency:
        Max number of connections in the pool. If not set, the suggested concurrency value provided by the server is used.

    :return: An instance of :py:class:`AsyncIOClient`.

    The APIs on the returned client instance can be safely used by different :py:class:`asyncio.Task`/coroutines, because under the hood they are checking out different connections from the pool to run the queries:

    * :py:meth:`AsyncIOClient.query()`
    * :py:meth:`AsyncIOClient.query_single()`
    * :py:meth:`AsyncIOClient.query_required_single()`
    * :py:meth:`AsyncIOClient.query_json()`
    * :py:meth:`AsyncIOClient.query_single_json()`
    * :py:meth:`AsyncIOClient.query_required_single_json()`
    * :py:meth:`AsyncIOClient.execute()`
    * :py:meth:`AsyncIOClient.transaction()`

    .. code-block:: python

        client = gel.create_async_client()
        await client.query('SELECT {1, 2, 3}')

    The same for transactions:

    .. code-block:: python

        client = gel.create_async_client()
        async for tx in client.transaction():
            async with tx:
                await tx.query('SELECT {1, 2, 3}')



.. py:class:: AsyncIOClient()

    An asynchronous client with a connection pool, safe for concurrent use.

    Async clients are created by calling :py:func:`~gel.create_async_client`.

    .. py:coroutinemethod:: query(query, *args, **kwargs)

        Acquire a connection and use it to run a query and return the results as an :py:class:`gel.Set` instance. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            An instance of :py:class:`gel.Set` containing the query result.

        Note that positional and named query arguments cannot be mixed.


    .. py:coroutinemethod:: query_single(query, *args, **kwargs)

        Acquire a connection and use it to run an optional singleton-returning query and return its element. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            Query result.

        The *query* must return no more than one element.  If the query returns more than one element, an ``gel.ResultCardinalityMismatchError`` is raised, if it returns an empty set, ``None`` is returned.

        Note, that positional and named query arguments cannot be mixed.


    .. py:coroutinemethod:: query_required_single(query, *args, **kwargs)

        Acquire a connection and use it to run a singleton-returning query and return its element. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            Query result.

        The *query* must return exactly one element.  If the query returns more than one element, an ``gel.ResultCardinalityMismatchError`` is raised, if it returns an empty set, an ``gel.NoDataError`` is raised.

        Note, that positional and named query arguments cannot be mixed.


    .. py:coroutinemethod:: query_json(query, *args, **kwargs)

        Acquire a connection and use it to run a query and return the results as JSON. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            A JSON string containing an array of query results.

        Note, that positional and named query arguments cannot be mixed.

        .. note::

            Caution is advised when reading ``decimal`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` number can be losslessly represented in JSON. However, the default JSON decoder in Python will read all such numbers as ``float`` values, which may result in errors or precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as ``Decimal``.


    .. py:coroutinemethod:: query_single_json(query, *args, **kwargs)

        Acquire a connection and use it to run an optional singleton-returning query and return its element in JSON. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            Query result encoded in JSON.

        The *query* must return no more than one element.  If the query returns more than one element, an ``gel.ResultCardinalityMismatchError`` is raised, if it returns an empty set, ``"null"`` is returned.

        Note, that positional and named query arguments cannot be mixed.

        .. note::

            Caution is advised when reading ``decimal`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` number can be losslessly represented in JSON. However, the default JSON decoder in Python will read all such numbers as ``float`` values, which may result in errors or precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as ``Decimal``.


    .. py:coroutinemethod:: query_required_single_json(query, *args, **kwargs)

        Acquire a connection and use it to run a singleton-returning query and return its element in JSON. The temporary connection is automatically returned back to the pool.

        :param str query: Query text.
        :param args: Positional query arguments.
        :param kwargs: Named query arguments.

        :return:
            Query result encoded in JSON.

        The *query* must return exactly one element.  If the query returns more than one element, an ``gel.ResultCardinalityMismatchError`` is raised, if it returns an empty set, an ``gel.NoDataError`` is raised.

        Note, that positional and named query arguments cannot be mixed.

        .. note::

            Caution is advised when reading ``decimal`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` number can be losslessly represented in JSON. However, the default JSON decoder in Python will read all such numbers as ``float`` values, which may result in errors or precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as ``Decimal``.


    .. py:coroutinemethod:: execute(query)

        Acquire a connection and use it to execute an EdgeQL command (or commands).  The temporary connection is automatically returned back to the pool.

        :param str query: Query text.

        The commands must take no arguments.

        Example:

        .. code-block:: pycon

            >>> await con.execute('''
            ...     CREATE TYPE MyType {
            ...         CREATE PROPERTY a -> int64
            ...     };
            ...     FOR x IN {100, 200, 300}
            ...     UNION INSERT MyType { a := x };
            ... ''')

        .. note::
            If the results of *query* are desired, :py:meth:`query`, :py:meth:`query_single` or :py:meth:`query_required_single` should be used instead.

    .. py:method:: transaction()

        Open a retryable transaction loop.

        This is the preferred method of initiating and running a database transaction in a robust fashion.  The ``transaction()`` transaction loop will attempt to re-execute the transaction loop body if a transient error occurs, such as a network error or a transaction serialization error.

        Returns an instance of :py:class:`AsyncIORetry`.

        See :ref:`gel-python-asyncio-api-transaction` for more details.

        Example:

        .. code-block:: python

            async for tx in con.transaction():
                async with tx:
                    value = await tx.query_single("SELECT Counter.value")
                    await tx.execute(
                        "UPDATE Counter SET { value := <int64>$value }",
                        value=value + 1,
                    )

        Note that we are executing queries on the ``tx`` object rather than on the original connection.

        .. note::
            The transaction starts lazily. A connection is only acquired from the pool when the first query is issued on the transaction instance.


    .. py:coroutinemethod:: aclose()

        Attempt to gracefully close all connections in the pool.

        Wait until all pool connections are released, close them and shut down the pool.  If any error (including cancellation) occurs in ``aclose()`` the pool will terminate by calling :py:meth:`~gel.AsyncIOClient.terminate`.

        It is advisable to use :py:func:`python:asyncio.wait_for` to set a timeout.

    .. py:method:: terminate()

        Terminate all connections in the pool.


    .. py:coroutinemethod:: ensure_connected()

        If the client does not yet have any open connections in its pool, attempts to open a connection, else returns immediately.

        Since the client lazily creates new connections as needed (up to the configured ``concurrency`` limit), the first connection attempt will only occur when the first query is run on a client. ``ensureConnected`` can be useful to catch any errors resulting from connection mis-configuration by triggering the first connection attempt explicitly.

    .. py:method:: with_transaction_options(options=None)

        Returns a shallow copy of the client with adjusted transaction options.

        :param TransactionOptions options:
            Object that encapsulates transaction options.

        See :ref:`gel-python-transaction-options` for details.

    .. py:method:: with_retry_options(options=None)

        Returns a shallow copy of the client with adjusted retry options.

        :param RetryOptions options: Object that encapsulates retry options.

        See :ref:`gel-python-retry-options` for details.

    .. py:method:: with_state(state)

        Returns a shallow copy of the client with adjusted state.

        :param State state: Object that encapsulates state.

        See :ref:`gel-python-state` for details.

    .. py:method:: with_default_module(module=None)

        Returns a shallow copy of the client with adjusted default module.

        This is equivalent to using the ``set module`` command, or using the ``reset module`` command when giving ``None``.

        :type module: str or None
        :param module: Adjust the *default module*.

        See :py:meth:`State.with_default_module` for details.

    .. py:method:: with_module_aliases(aliases_dict=None, /, **aliases)

        Returns a shallow copy of the client with adjusted module aliases.

        This is equivalent to using the ``set alias`` command.

        :type aliases_dict: dict[str, str] or None
        :param aliases_dict: This is an optional positional-only argument.

        :param dict[str, str] aliases:
            Adjust the module aliases after applying ``aliases_dict`` if set.

        See :py:meth:`State.with_module_aliases` for details.

    .. py:method:: without_module_aliases(*aliases)

        Returns a shallow copy of the client without specified module aliases.

        This is equivalent to using the ``reset alias`` command.

        :param tuple[str] aliases: Module aliases to reset.

        See :py:meth:`State.without_module_aliases` for details.

    .. py:method:: with_config(config_dict=None, /, **config)

        Returns a shallow copy of the client with adjusted session config.

        This is equivalent to using the ``configure session set`` command.

        :type config_dict: dict[str, object] or None
        :param config_dict: This is an optional positional-only argument.

        :param dict[str, object] config:
            Adjust the config settings after applying ``config_dict`` if set.

        See :py:meth:`State.with_config` for details.

    .. py:method:: without_config(*config_names)

        Returns a shallow copy of the client without specified session config.

        This is equivalent to using the ``configure session reset`` command.

        :param tuple[str] config_names: Config to reset.

        See :py:meth:`State.without_config` for details.

    .. py:method:: with_globals(globals_dict=None, /, **globals_)

        Returns a shallow copy of the client with adjusted global values.

        This is equivalent to using the ``set global`` command.

        :type globals_dict: dict[str, object] or None
        :param globals_dict: This is an optional positional-only argument.

        :param dict[str, object] globals_:
            Adjust the global values after applying ``globals_dict`` if set.

        See :py:meth:`State.with_globals` for details.

    .. py:method:: without_globals(*global_names)

        Returns a shallow copy of the client without specified globals.

        This is equivalent to using the ``reset global`` command.

        :param tuple[str] global_names: Globals to reset.

        See :py:meth:`State.without_globals` for details.


.. _gel-python-asyncio-api-transaction:

Transactions
------------

.. py:class:: AsyncIORetry

    Represents a wrapper that yields :py:class:`AsyncIOTransaction` object when iterating.

    See :py:meth:`AsyncIOClient.transaction()` method for an example.

    .. py:coroutinemethod:: __anext__()

        Yields :py:class:`AsyncIOTransaction` object every time transaction has to be repeated.

.. py:class:: AsyncIOTransaction

    Represents a transaction.

    Instances of this type are yielded by a :py:class:`AsyncIORetry` iterator.

    .. describe:: async with c:

        Start and commit/rollback the transaction automatically when entering and exiting the code inside the context manager block.

    .. py:coroutinemethod:: query(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run a query and return the results as an :py:class:`gel.Set` instance. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`AsyncIOClient.query() <gel.AsyncIOClient.query>` for details.

    .. py:coroutinemethod:: query_single(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run an optional singleton-returning query and return its element. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`AsyncIOClient.query_single() <gel.AsyncIOClient.query_single>` for details.

    .. py:coroutinemethod:: query_required_single(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run a singleton-returning query and return its element. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`AsyncIOClient.query_required_single() <gel.AsyncIOClient.query_required_single>` for details.

    .. py:coroutinemethod:: query_json(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run a query and return the results as JSON. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`AsyncIOClient.query_json() <gel.AsyncIOClient.query_json>` for details.

    .. py:coroutinemethod:: query_single_json(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run an optional singleton-returning query and return its element in JSON. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`AsyncIOClient.query_single_json() <gel.AsyncIOClient.query_single_json>` for details.

    .. py:coroutinemethod:: query_required_single_json(query, *args, **kwargs)

        Acquire a connection if the current transaction doesn't have one yet, and use it to run a singleton-returning query and return its element in JSON. The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`AsyncIOClient.query_requried_single_json() <gel.AsyncIOClient.query_required_single_json>` for details.

    .. py:coroutinemethod:: execute(query)

        Acquire a connection if the current transaction doesn't have one yet, and use it to execute an EdgeQL command (or commands).  The temporary connection is automatically returned back to the pool when exiting the transaction block.

        See :py:meth:`AsyncIOClient.execute() <gel.AsyncIOClient.execute>` for details.

.. _RFC1004: https://github.com/gel/rfcs/blob/master/text/1004-transactions-api.rst
