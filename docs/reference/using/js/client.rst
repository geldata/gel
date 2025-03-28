.. _gel-js-driver:
.. _gel-js-client:

======
Client
======

The ``Client`` class implements the basic functionality required to establish a pool of connections to your database, execute queries with some context and parameters, manage transactions, and decode results into JavaScript types.

Creating a client
=================

The ``gel`` package exposes a :ref:`createClient <gel-js-create-client>` function that can be used to create a new :ref:`Client <gel-js-api-client>` instance. This client instance manages a pool of connections to the database which it discovers automatically from either being in a :gelcmd:`project init` directory or being provided connection details via Environment Variables. See :ref:`the environment section of the connection reference <ref_reference_connection_environments>` for more details and options.

.. note::

  If you're using |Gel| Cloud to host your development instance, you can use the :gelcmd:`cloud login` command to authenticate with |Gel| Cloud and then use the :gelcmd:`project init --server-instance <instance-name>` command to create a local project-linked instance that is linked to an Gel Cloud instance. For more details, see :ref:`the Gel Cloud guide <ref_guide_cloud>`.

.. code-block:: typescript

  import { createClient } from "gel";

  const client = createClient();

  const answer = await client.queryRequiredSingle<number>("select 2 + 2;");
  console.log(answer); // number: 4

Checking connection status
--------------------------

The client maintains a dynamically sized *pool* of connections under the hood.  These connections are initialized *lazily*, so no connection will be established until the first time you execute a query.

If you want to explicitly ensure that the client is connected without running a query, use the ``.ensureConnected()`` method. This can be useful to catch any errors resulting from connection mis-configuration by triggering the first connection attempt explicitly.

.. code-block:: typescript

  import { createClient } from "gel";

  const client = createClient();

  async function main() {
    await client.ensureConnected();
    const answer = await client.queryRequiredSingle<number>("select 2 + 2;");
    console.log(answer); // number: 4
  }

  main();

.. _gel-js-running-queries:

Running queries
===============

The ``Client`` class provides a number of methods for running queries. The simplest is ``query``, which runs a query and returns the result as an array of results. The function signature is generic over the type of the result element, so you can provide a type to receive a strongly typed result.

.. code-block:: typescript

  import { createClient } from "gel";

  const client = createClient();

  const result = await client.query<number>("select 2 + 2;");
  console.log(result); // number[]: [4]

Parameters
----------

If your query contains parameters (e.g. ``$foo``), you can pass in values as the second argument.

.. code-block:: typescript

  const result = await client.querySingle<{ id: string }>(
    `insert Movie { title := <str>$title }`,
    { title: "Iron Man" }
  );
  console.log(result);
  // {id: "047c5893..."}

.. note::

  Parameters can only be scalars or arrays of scalars. See :ref:`parameters <ref_eql_params>` for more details.

Cardinality
-----------

The ``.query`` method always returns an array of results. It places no constraints on cardinality.

.. code-block:: typescript

  await client.query<number>("select 2 + 2;"); // number[]: [4]
  await client.query<number>("select <int64>{};"); // number[]: []
  await client.query<number>("select {1, 2, 3};"); // number[]: [1, 2, 3]

If you know your query will only return a single element, you can tell |Gel| to expect a *singleton result* by using the ``.querySingle`` method. This is intended for queries that return *zero or one* elements. If the query returns a set with more than one elements, the ``Client`` will throw a runtime error.

.. note::

  Remember that arrays and tuples are considered an element of the result set, so if you're returning exactly one array or tuple, the result will be an array.

.. code-block:: typescript

  await client.querySingle<number>("select 2 + 2;"); // number | null: 4
  await client.querySingle<number[]>("select [1, 2, 3];"); // number[] | null: [1, 2, 3]
  await client.querySingle<number>("select <int64>{};"); // number | null: null
  await client.querySingle<number>("select {1, 2, 3};"); // Throws a ResultCardinalityMismatchError

Use ``queryRequiredSingle`` for queries that return *exactly one* element. If the query returns an empty set or a set with multiple elements, the ``Client`` will throw a runtime error.

.. code-block:: typescript

  await client.queryRequiredSingle<number>("select 2 + 2;"); // number: 4
  await client.queryRequiredSingle<number>("select <int64>{};"); // Throws a NoDataError
  await client.queryRequiredSingle<number>("select {1, 2, 3};"); // Throws a ResultCardinalityMismatchError

Use ``queryRequired`` for queries that return *one or more* elements. If the query returns an empty set, the ``Client`` will throw a runtime error.

.. code-block:: typescript

  await client.queryRequired<number>("select 2 + 2;"); // [number, ...number[]]: 4
  await client.queryRequired<number>("select {1, 2, 3};"); // [number, ...number[]]: [1, 2, 3]
  await client.queryRequired<number>("select <int64>{};"); // Throws a ResultCardinalityMismatchError

If you do not need or expect a result, you can use ``execute`` which will return ``void``. This is often useful for mutations where you do not need to retrieve a result.

.. code-block:: typescript

  await client.execute(`insert Movie { title := "Iron Man" }`); // void

JSON results
------------

Client provide additional methods for running queries and retrieving results as a *serialized JSON string*. This serialization happens inside the database and is typically more performant than running ``JSON.stringify`` yourself.

.. code-block:: javascript

  await client.queryJSON(`select {1, 2, 3};`);
  // "[1, 2, 3]"

  await client.querySingleJSON(`select <int64>{};`);
  // "null"

  await client.queryRequiredSingleJSON(`select 3.14;`);
  // "3.14"

  await client.queryRequiredJSON(`select 3.14;`);
  // "3.14"

.. warning::

  Caution is advised when reading ``decimal`` or ``bigint`` values using these methods. The JSON specification does not have a limit on significant digits, so a ``decimal`` or a ``bigint`` number can be losslessly represented in JSON.  However, JSON decoders in JavaScript will often read all such numbers as ``number`` values, which may result in precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as BigInt_.

SQL queries
-----------

.. versionadded:: 6.0

The ``querySQL`` method allows you to run a SQL query and return the result as an array of objects. This method is also generic over the type of the result element, so you can provide a type to receive a strongly typed result.

.. code-block:: typescript

  const result = await client.querySQL<{ result: number }>(`select 2 + 2 as result;`);
  console.log(result); // [{result: 4}]

If you don't need the result, you can use ``executeSQL`` which will return ``void``.

.. code-block:: typescript

  await client.executeSQL(`insert into "Movie" (name) values ("Iron Man")`); // void

Scripts
-------

Both ``execute`` and the ``query*`` methods support scripts (queries containing multiple statements). The statements, like all queries, are run in an implicit transaction (unless already in an explicit transaction), so the whole script remains atomic. For the ``query*`` methods only the result of the final statement in the script will be returned.

.. code-block:: typescript

  const result = await client.query<{ id: string }>(`
    insert Movie {
      title := <str>$title
    };
    insert Person {
      name := <str>$name
    };
  `, {
    title: "Thor: Ragnarok",
    name: "Anson Mount"
  });
  result; // { id: string }[]: the result of the `insert Person` statement

For more fine grained control of atomic exectution of multiple statements, use the ``transaction()`` API.

.. _gel-js-api-transaction:

Transactions
------------

For more fine grained control of atomic exectution of multiple statements, use the ``transaction()`` API.

.. code-block:: typescript

    await client.transaction(async (tx) => {
      await tx.execute("insert Movie { title := <str>$title }", { title: "Iron Man" });
      await tx.execute("insert Person { name := <str>$name }", { name: "Anson Mount" });
    });

Note that we execute queries on the ``tx`` object in the above example, rather than on the original ``client`` object.

The ``transaction()`` API guarantees that:

1. Transactions are executed atomically;
2. If a transaction fails due to retryable error (like a network failure or a concurrent update error), the transaction would be retried;
3. If any other, non-retryable error occurs, the transaction is rolled back and the ``transaction()`` block throws.

The *transaction* object exposes ``query()``, ``execute()``, ``querySQL()``, ``executeSQL()``, and other ``query*()`` methods that *clients* expose, with the only difference that queries will run within the current transaction and can be retried automatically.

.. warning::

  In transactions, the entire nested code block can be re-run, including any non-querying JavaScript code. In general, the code inside the transaction block **should not have side effects or run for a significant amount of time**. Consider the following example:

  .. code-block:: typescript

      const email = "timmy@example.com";

      await client.transaction(async (tx) => {
        await tx.execute(
          `insert User { email := <str>$email }`,
          { email },
        );

        await sendWelcomeEmail(email);

        await tx.execute(
          `insert LoginHistory {
            user := (select User filter .email = <str>$email),
            timestamp := datetime_current()
          }`,
          { email },
        );
      });

  In the above example, the welcome email may be sent multiple times if the transaction block is retried. Additionally, transactions allocate expensive server resources. Having too many concurrently running long-running transactions will negatively impact the performance of the DB server.


Configuring clients
===================

Clients can be configured using a set of methods that start with ``with``. One you'll likely use often in application code is the ``withGlobals`` which sets the global variables in the query.

.. code-block:: typescript

  const client = createClient();
  await client
    .withGlobals({
      current_user_id: "00000000-0000-0000-0000-000000000000",
    })
    .querySingle(
      "select User { * } filter .id ?= global current_user_id;"
    );

.. note::

  These methods return a *new Client instance* that *shares a connection pool* with the original client. This is important. Each call to ``createClient`` instantiates a new connection pool, so in typical usage you should create a single shared client instance and configure it at runtime as needed.


.. _gel-js-api-client:

Client Reference
================

.. _gel-js-create-client:

``createClient`` function
-------------------------

.. js:function:: createClient( \
      options?: string | ConnectOptions | null | undefined \
    ): Client

    Creates a new :js:class:`Client` instance.

    :param options:
        This is an optional parameter. We recommend omitting it in all but the most unusual circumstances. When it is not specified the client will connect to the current |Gel| Project instance or discover connection parameters from the environment.

        If this parameter is a string it can represent either a DSN or an instance name. When the string does not start with |geluri| it is parsed as the :ref:`name of an instance <ref_reference_connection_instance_name>`; otherwise it specifies a single string in the DSN format: :geluri:`user:password@host:port/database?option=value`.

        Alternatively the parameter can be a ``ConnectOptions`` config; see the documentation of valid options below, and the full :ref:`connection parameter reference <ref_reference_connection_parameters>` for details.

    :param string options.dsn:
        Specifies the DSN of the instance.

    :param string options.credentialsFile:
        Path to a file containing credentials.

    :param string options.host:
        Instance host address as either an IP address or a domain name.

    :param number options.port:
        Port number to connect to at the server host.

    :param string options.branch:
        The name of the branch to connect to.

    :param string options.user:
        The name of the database role used for authentication.

    :param string options.password:
        Password to be used for authentication, if the server requires one.

    :param string options.tlsCAFile:
        Path to a file containing the root certificate of the server.

    :param string options.tlsSecurity:
        Determines whether certificate and hostname verification is enabled.  Valid values are ``'strict'`` (certificate will be fully validated), ``'no_host_verification'`` (certificate will be validated, but hostname may not match), ``'insecure'`` (certificate not validated, self-signed certificates will be trusted), or ``'default'`` (acts as ``strict`` by default, or ``no_host_verification`` if ``tlsCAFile`` is set).

    The above connection options can also be specified by their corresponding environment variable. If none of ``dsn``, ``credentialsFile``, ``host`` or ``port`` are explicitly specified, the client will connect to your linked project instance, if it exists. For full details, see the :ref:`Connection Parameters <ref_reference_connection>` docs.

    :param number options.timeout:
        Connection timeout in milliseconds.

    :param number options.waitUntilAvailable:
        If first connection fails, the number of milliseconds to keep retrying to connect. Useful if your development instance and app are started together, to allow the server time to be ready.

    :param number options.concurrency:
        The maximum number of connections the ``Client`` will create in it's connection pool. If not specified the concurrency will be controlled by the server. This is recommended as it allows the server to better manage the number of client connections based on it's own available resources.

    :returns:
        Returns an instance of :js:class:`Client`.

    Example:

    .. code-block:: typescript

      import { createClient } from "gel";
      import assert from "node:assert";

      async function main() {
        const client = createClient();

        const data: number = await client.queryRequiredSingle<number>(
          "select 1 + 1"
        );

        assert(data === 2, "Result is exactly the number 2");
      }

      main();

``Client`` class
----------------

.. js:class:: Client

    A ``Client`` allows you to run queries on a |Gel| instance.

    Since opening connections is an expensive operation, ``Client`` also maintains a internal pool of connections to the instance, allowing connections to be automatically reused, and you to run multiple queries on the client simultaneously, enhancing the performance of database interactions.

    :js:class:`Client` is not meant to be instantiated directly; :js:func:`createClient` should be used instead.


    .. _gel-js-api-async-optargs:

    .. note::

        Some methods take query arguments as an *args* parameter. The type of the *args* parameter depends on the query:

        * If the query uses positional query arguments, the *args* parameter must be an ``array`` of values of the types specified by each query argument's type cast.
        * If the query uses named query arguments, the *args* parameter must be an ``object`` with property names and values corresponding to the query argument names and type casts.

        If a query argument is defined as ``optional``, the key/value can be either omitted from the *args* object or be a ``null`` value.

    .. js:method:: execute(query: string, args?: QueryArgs): Promise<void>

        Execute an EdgeQL command or script of commands. Does not return any results.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<void>``

        Example:

        .. code-block:: typescript

          await client.execute(`
            for x in {100, 200, 300}
            insert MyType { a := x };
          `)

    .. js:method:: query<T>(query: string, args?: QueryArgs): Promise<T[]>

        Run an EdgeQL query and return the results as an array.
        This method **always** returns an array.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<T[]>``

        Example:

        .. code-block:: typescript

          const result = await client.query<number>("select 2 + 2;"); // number[]: [4]
          const result = await client.query<number>("select {1, 2, 3};"); // number[]: [1, 2, 3]
          const result = await client.query<number>("select <int64>{};"); // number[]: []

    .. js:method:: queryRequired<T>( \
            query: string, \
            args?: QueryArgs \
        ): Promise<[T, ...T[]]>

        Run a query that returns at least one element and return the result as an
        array. The *query* must return at least one element. If the query less than one
        element, a ``ResultCardinalityMismatchError`` error is thrown.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<[T, ...T[]]>``
        :throws: ``ResultCardinalityMismatchError`` if the query returns less than one element.

        Example:

        .. code-block:: typescript

          await client.queryRequired<number>("select 2 + 2;"); // [number, ...number[]]: [4]
          await client.queryRequired<number>("select {1, 2, 3};"); // [number, ...number[]]: [1, 2, 3]
          await client.queryRequired<number>("select <int64>{};"); // Throws a ResultCardinalityMismatchError

    .. js:method:: querySingle<T>( \
            query: string, \
            args?: QueryArgs \
        ): Promise<T | null>

        Run an optional singleton-returning query and return the result. The *query* must return no more than one element. If the query returns more than one element, a ``ResultCardinalityMismatchError`` error is thrown.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<T | null>``
        :throws: ``ResultCardinalityMismatchError`` if the query returns more than one element.

        Example:

        .. code-block:: typescript

          const result = await client.querySingle<number>("select 2 + 2;"); // number | null: 4
          await client.querySingle<number>("select <int64>{};"); // number | null: null
          await client.querySingle<number>("select {1, 2, 3};"); // Throws a ResultCardinalityMismatchError

    .. js:method:: queryRequiredSingle<T>( \
            query: string, \
            args?: QueryArgs \
        ): Promise<T>

        Run a singleton-returning query and return the result. The *query* must return exactly one element. If the query returns more than one element, a ``ResultCardinalityMismatchError`` error is thrown. If the query returns an empty set, a ``NoDataError`` error is thrown.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<T>``
        :throws: ``ResultCardinalityMismatchError`` if the query returns more than one element.
        :throws: ``NoDataError`` if the query returns an empty set.

        Example:

        .. code-block:: typescript

          await client.queryRequiredSingle<number>("select 2 + 2;"); // number: 4
          await client.queryRequiredSingle<number>("select <int64>{};"); // Throws a NoDataError
          await client.queryRequiredSingle<number>("select {1, 2, 3};"); // Throws a ResultCardinalityMismatchError


    .. js:method:: queryJSON(query: string, args?: QueryArgs): Promise<string>

        Run a query and return the results as a JSON-encoded string.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<string>``

        .. note::

          Caution is advised when reading ``decimal`` or ``bigint`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` or a ``bigint`` number can be losslessly represented in JSON.  However, JSON decoders in JavaScript will often read all such numbers as ``number`` values, which may result in precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as BigInt_.

    .. js:method:: queryRequiredJSON( \
            query: string, \
            args?: QueryArgs \
        ): Promise<string>

        Run a query that returns at least one element and return the result as a JSON-encoded string. The *query* must return at least one element. If the query less than one element, a ``ResultCardinalityMismatchError`` error is thrown.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<string>``
        :throws: ``ResultCardinalityMismatchError`` if the query returns less than one element.

        Example:

        .. code-block:: typescript

          const result = await client.queryRequiredJSON("select 2 + 2;"); // string: "4"
          const result = await client.queryRequiredJSON("select <int64>{};"); // Throws a ResultCardinalityMismatchError
          const result = await client.queryRequiredJSON("select {1, 2, 3};"); // Throws a ResultCardinalityMismatchError


        .. warning::

          Caution is advised when reading ``decimal`` or ``bigint`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` or a ``bigint`` number can be losslessly represented in JSON.  However, JSON decoders in JavaScript will often read all such numbers as ``number`` values, which may result in precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as BigInt_.

    .. js:method:: querySingleJSON( \
            query: string, \
            args?: QueryArgs \
        ): Promise<string>

        Run an optional singleton-returning query and return its element as a JSON-encoded string.  The *query* must return at most one element.  If the query returns more than one element, an ``ResultCardinalityMismatchError`` error is thrown.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<string>``
        :throws: ``ResultCardinalityMismatchError`` if the query returns more than one element.

        Example:

        .. code-block:: typescript

          const result = await client.querySingleJSON("select 2 + 2;"); // string: "4"
          await client.querySingleJSON("select <int64>{};"); // Throws a ResultCardinalityMismatchError
          await client.querySingleJSON("select {1, 2, 3};"); // Throws a ResultCardinalityMismatchError

        .. warning::

          Caution is advised when reading ``decimal`` or ``bigint`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` or a ``bigint`` number can be losslessly represented in JSON.  However, JSON decoders in JavaScript will often read all such numbers as ``number`` values, which may result in precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as BigInt_.

    .. js:method:: queryRequiredSingleJSON( \
            query: string, \
            args?: QueryArgs \
        ): Promise<string>

        Run a singleton-returning query and return its element as a JSON-encoded string. The *query* must return exactly one element. If the query returns more than one element, a ``ResultCardinalityMismatchError`` error is thrown. If the query returns an empty set, a ``NoDataError`` error is thrown.

        :param query: Query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<string>``
        :throws: ``ResultCardinalityMismatchError`` if the query returns more than one element.
        :throws: ``NoDataError`` if the query returns an empty set.

        Example:

        .. code-block:: typescript

          const result = await client.queryRequiredSingleJSON("select 2 + 2;"); // string: "4"
          await client.queryRequiredSingleJSON("select <int64>{};"); // Throws a ResultCardinalityMismatchError
          await client.queryRequiredSingleJSON("select {1, 2, 3};"); // Throws a ResultCardinalityMismatchError


        .. warning::

            Caution is advised when reading ``decimal`` or ``bigint`` values using this method. The JSON specification does not have a limit on significant digits, so a ``decimal`` or a ``bigint`` number can be losslessly represented in JSON.  However, JSON decoders in JavaScript will often read all such numbers as ``number`` values, which may result in precision loss. If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type, such as BigInt_.

    .. js:method:: executeSQL(query: string, args?: unknown[]): Promise<void>

        Execute a SQL command.

        :param query: SQL query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<void>``

        Example:

        .. code-block:: typescript

          await client.executeSQL(`
            INSERT INTO "MyType" (prop) VALUES ("value");
          `)

    .. js:method:: querySQL<T>(query: string, args?: unknown[]): Promise<T[]>

        Run a SQL query and return the results as an array. This method **always** returns an array.

        The array will contain the returned rows. By default, rows are ``Objects`` with columns addressable by name, and the type of the object as the generic type parameter ``T``. You can also opt into ``array`` mode, where the array contains arrays of values by calling ``client.withSQLRowMode('array')``.

        :param query: SQL query text.
        :param args: (optional) :ref:`query arguments <gel-js-api-async-optargs>`.

        :returns: ``Promise<T[]>``

        Example:

        .. code-block:: typescript

            const sqlQuery = `SELECT 1 as foo, "hello" as bar`;
            await client.querySQL<{foo: number; bar: string }>(sqlQuery);
            // { foo: number; bar: string }[]: [{'foo': 1, 'bar': 'hello'}]

            const arrayModeClient = client.withSQLRowMode('array');
            await arrayModeClient.querySQL<[number, string]>(sqlQuery);
            // [number, string][]: [[1, 'hello']]

    .. js:method:: transaction<T>( \
            action: (tx: Transaction) => Promise<T> \
        ): Promise<T>

        Execute a retryable transaction. The ``Transaction`` object passed to the ``action`` callback function has the same ``execute`` and ``query*`` methods as ``Client``.

        The ``transaction()`` method will attempt to re-execute the transaction body if a transient error occurs, such as a network error or a transaction serialization error.  The number of times ``transaction()`` will attempt to execute the transaction, and the backoff timeout between retries can be configured with :js:meth:`Client.withRetryOptions`.

        See :ref:`gel-js-api-transaction` for more details.

        :arg action: A callback function that takes a ``Transaction`` object as an argument and returns a ``Promise`` that resolves to the result of the transaction.

        :returns: ``Promise<T>``

        Example:

        .. code-block:: javascript

            await client.transaction(async (tx) => {
              const value = await tx.queryRequiredSingle<number>("select Counter.value");
              await tx.execute(
                `update Counter set { value := <int64>$value }`,
                {value: value + 1},
              );
            });

    .. js:method:: ensureConnected(): Promise<Client>

        If the client does not yet have any open connections in its pool, attempts to open a connection, else returns immediately.

        Since the client lazily creates new connections as needed (up to the configured ``concurrency`` limit), the first connection attempt will only occur when the first query is run a client. ``ensureConnected`` can be useful to catch any errors resulting from connection mis-configuration by triggering the first connection attempt explicitly.

        :returns: ``Promise<Client>``

        Example:

        .. code-block:: javascript

            import { createClient } from "gel";

            async function getClient() {
              try {
                return await createClient().ensureConnected();
              } catch (err) {
                // handle connection error
              }
            }

            async function main() {
              const client = await getClient();

              await client.query("select 2 + 2;");
            }

    .. js:method:: withGlobals(globals: {[name: string]: any}): Client

        Returns a clone of the ``Client`` instance with the specified global values. The ``globals`` argument object is merged with any existing globals defined on the current client instance. The new client instance will share the same connection pool as the client it's created from.

        Equivalent to using the ``set global`` command.

        :arg globals: An object mapping global names to values.

        :returns: ``Client``

        Example:

        .. code-block:: typescript

            const user = await client.withGlobals({
              userId: "00000000-0000-0000-0000-000000000000"
            }).querySingle<{ name: string }>(`
              select User { name } filter .id = global userId;
            `);

    .. js:method:: withModuleAliases(aliases: {[name: string]: string}): Client

        Returns a clone of the ``Client`` instance with the specified module aliases. The ``aliases`` argument object is merged with any existing module aliases defined on the current client instance. The new client instance will share the same connection pool as the client it's created from.

        If the alias ``name`` is ``module`` this is equivalent to using the ``set module`` command, otherwise it is equivalent to the ``set alias`` command.

        :arg aliases: An object mapping alias names to values.

        :returns: ``Client``

        Example:

        .. code-block:: javascript

            const user = await client.withModuleAliases({
              module: "sys"
            }).queryRequiredSingle<string>(`
              select get_version_as_str();
            `);
            // "6.4"

    .. js:method:: withConfig(config: {[name: string]: any}): Client

        Returns a clone of the ``Client`` instance with the specified client session configuration. The ``config`` argument object is merged with any existing session config defined on the current client instance. The new client instance will share the same connection pool as the client it's created from.

        Equivalent to using the ``configure session`` command. For available configuration parameters refer to the :ref:`Config documentation <ref_std_cfg>`.

        :arg config: An object mapping configuration parameter names to values.

        :returns: ``Client``

        Example:

        .. code-block:: typescript

            const user = await client
              .withConfig({ "query_timeout": 10000 })
              .query<{ name: string }>(`
                select User { name };
              `);

    .. js:method:: withRetryOptions(opts: { \
            attempts?: number, \
            backoff?: (attempt: number) => number \
        }): Client

        Returns a clone of the ``Client`` instance with the specified retry attempts number and backoff time function (the time that retrying methods will wait between retry attempts, in milliseconds), where options not given are inherited from the current client instance.

        The default number of attempts is ``3``. The default backoff function returns a random time between 100 and 200ms multiplied by ``2 ^ attempt number``.

        :arg opts: An object mapping retry options to values.

        :returns: ``Client``

        Example:

        .. code-block:: javascript

            const nonRetryingClient = client.withRetryOptions({
              attempts: 1
            });

            // This transaction will not retry
            await nonRetryingClient.transaction(async (tx) => {
              // ...
            });

    .. js:method:: close(): Promise<void>

        Close the client's open connections gracefully. When a client is closed, all its underlying connections are awaited to complete their pending operations, then closed. A warning is produced if the pool takes more than 60 seconds to close.

        .. note::

            Clients will not prevent Node.js from exiting once all of it's open connections are idle and Node.js has no further tasks it is awaiting on, so it is not necessary to explicitly call ``close()`` if it is more convenient for your application.

    .. js:method:: isClosed(): boolean

        Returns true if ``close()`` has been called on the client.

    .. js:method:: terminate(): void

        Terminate all connections in the client, closing all connections non gracefully. If the client is already closed, return without doing anything.

.. _BigInt:
    https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/BigInt
