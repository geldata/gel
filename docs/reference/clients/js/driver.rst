.. _gel-js-driver:


Client
======

The ``Client`` class implements the basic functionality required to establish a pool of connections to your database, execute queries with some context and parameters, manage transactions, and decode results into JavaScript types.

In typical usage, you will call :js:func:`createClient` with no arguments and rely on the :ref:`default behavior <gel_client_js_connection>` to connect to the instance specified either as a local project, or via environment variables. Directly specifying connection parameters should be considered for debugging or unusual scenarios.

.. _gel-js-api-client:
.. _gel-js-create-client:

.. js:function:: createClient( \
        options?: string | ConnectOptions | null | undefined \
    ): Client

    Creates a new :js:class:`Client` instance.

    :param options:
        This is an optional parameter. We recommend omitting it in all but the most unusual circumstances. When it is not specified the client will connect to the current |Gel| Project instance or discover connection parameters from the environment.

        If this parameter is a string it can represent either a DSN or an instance name:

        * when the string does not start with |geluri| it is parsed as the :ref:`name of an instance <ref_reference_connection_instance_name>`;

        * otherwise it specifies a single string in the DSN format: :geluri:`user:password@host:port/database?option=value`.

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


Connections
^^^^^^^^^^^

Notice we didn't pass any arguments into ``createClient``. That's intentional.

**In development**, we recommend using :gelcmd:`project init` to create an
instance and link it to your project directory. As long as you're inside this
directory, ``createClient()`` with auto-detect the project and connect to the
associated instance automatically.

**In production** you should use environment variables to provide connection
information to ``createClient``. See the :ref:`Connection parameters
<ref_reference_connection>` docs for details.

Configuring clients
^^^^^^^^^^^^^^^^^^^

Clients can be configured using a set of *immutable* methods that start with
``with``.

.. note::

  These methods return a *new Client instance* that *shares a connection pool*
  with the original client! This is important. Each call to ``createClient``
  instantiates a new connection pool.

The code example below demonstrates all available configuration settings. The
value specified below is the *default value* for that setting.

.. code-block:: typescript

  import {createClient, Duration, IsolationLevel} from "gel";

  const baseClient = createClient();
  const client = baseClient
    .withConfig({
      // 10 seconds
      session_idle_transaction_timeout: Duration.from({seconds: 10}),
      // 0 seconds === no timeout
      query_execution_timeout: Duration.from({seconds: 0}),
      allow_bare_ddl: "NeverAllow",
      allow_user_specified_id: false,
      apply_access_policies: true,
    })
    .withRetryOptions({
      attempts: 3,
      backoff: (attemptNo: number) => {
        // exponential backoff
        return 2 ** attemptNo * 100 + Math.random() * 100;
      },
    })
    .withTransactionOptions({
      isolation: IsolationLevel.Serializable, // only supported value
      deferrable: false,
      readonly: false,
    });

Running queries
---------------

To execute a basic query:

.. code-block:: javascript

  const gel = require("gel");

  const client = gel.createClient();

  async function main() {
    const result = await client.query(`select 2 + 2;`);
    console.log(result); // [4]
  }


.. _gel-js-typescript:

In TypeScript, you can supply a type hint to receive a strongly typed result.

.. code-block:: javascript

  const result = await client.query<number>(`select 2 + 2;`);
  // number[]

``.query`` method
^^^^^^^^^^^^^^^^^

The ``.query`` method always returns an array of results. It places no
constraints on cardinality.

.. code-block:: javascript

  await client.query(`select 2 + 2;`); // [4]
  await client.query(`select [1, 2, 3];`); // [[1, 2, 3]]
  await client.query(`select <int64>{};`); // []
  await client.query(`select {1, 2, 3};`); // [1, 2, 3]

``.querySingle`` method
^^^^^^^^^^^^^^^^^^^^^^^

If you know your query will only return a single element, you can tell |Gel|
to expect a *singleton result* by using the ``.querySingle`` method. This is
intended for queries that return *zero or one* elements. If the query returns
a set with more than one elements, the ``Client`` will throw a runtime error.

.. note::

  Note that if you're selecting an array or tuple, the returned value may
  still be an array.

.. code-block:: javascript

  await client.querySingle(`select 2 + 2;`); // 4
  await client.querySingle(`select [1, 2, 3];`); // [1, 2, 3]
  await client.querySingle(`select <int64>{};`); // null
  await client.querySingle(`select {1, 2, 3};`); // Error

``.queryRequiredSingle`` method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``queryRequiredSingle`` for queries that return *exactly one* element. If
the query returns an empty set or a set with multiple elements, the ``Client``
will throw a runtime error.

.. code-block:: javascript

  await client.queryRequiredSingle(`select 2 + 2;`); // 4
  await client.queryRequiredSingle(`select [1, 2, 3];`); // [1, 2, 3]
  await client.queryRequiredSingle(`select <int64>{};`); // Error
  await client.queryRequiredSingle(`select {1, 2, 3};`); // Error

TypeScript
^^^^^^^^^^

The TypeScript signatures of these methods reflects their behavior.

.. code-block:: typescript

  await client.query<number>(`select 2 + 2;`);
  // number[]

  await client.querySingle<number>(`select 2 + 2;`);
  // number | null

  await client.queryRequiredSingle<number>(`select 2 + 2;`);
  // number


Type conversion
---------------

The client converts |Gel| types into a corresponding JavaScript data
structure. Some Gel types like ``duration`` don't have a corresponding type
in the JavaScript type system, so we've implemented classes like
:js:class:`Duration` to represent them.

.. list-table::

  * - **Gel type**
    - **JavaScript type**
  * - Sets
    - ``Array``
  * - Arrays
    - ``Array``
  * - Tuples ``tuple<x, y, ...>``
    - ``Array``
  * - Named tuples ``tuple<foo: x, bar: y, ...>``
    - ``object``
  * - Enums
    - ``string``
  * - ``Object``
    - ``object``
  * - ``str``
    - ``string``
  * - ``bool``
    - ``boolean``
  * - ``float32`` ``float64`` ``int16`` ``int32`` ``int64``
    - ``number``
  * - ``json``
    - ``string``
  * - ``uuid``
    - ``string``
  * - ``bigint``
    - ``BigInt``
  * - ``decimal``
    - ``string``
  * - ``bytes``
    - ``Uint8Array``
  * - ``datetime``
    - ``Date``
  * - ``duration``
    - :js:class:`Duration`
  * - ``e.cal.relative_duration``
    - :js:class:`RelativeDuration`
  * - ``e.cal.date_duration``
    - :js:class:`DateDuration`
  * - ``cal::local_date``
    - :js:class:`LocalDate`
  * - ``cal::local_time``
    - :js:class:`LocalTime`
  * - ``cal::local_datetime``
    - :js:class:`LocalDateTime`
  * - ``cfg::memory``
    - :js:class:`ConfigMemory`
  * - Ranges ``range<x>``
    - :js:class:`Range`


To learn more about the client's built-in type classes, refer to the reference
documentation.

- :js:class:`Duration`
- :js:class:`RelativeDuration`
- :js:class:`DateDuration`
- :js:class:`LocalDate`
- :js:class:`LocalTime`
- :js:class:`LocalDateTime`
- :js:class:`ConfigMemory`
- :js:class:`Range`


JSON results
------------

Client provide additional methods for running queries and retrieving results
as a *serialized JSON string*. This serialization happens inside the database
and is typically more performant than running ``JSON.stringify`` yourself.

.. code-block:: javascript

  await client.queryJSON(`select {1, 2, 3};`);
  // "[1, 2, 3]"

  await client.querySingleJSON(`select <int64>{};`);
  // "null"

  await client.queryRequiredSingleJSON(`select 3.14;`);
  // "3.14"

Non-returning queries
---------------------

To execute a query without retrieving a result, use the ``.execute`` method.
This is especially useful for mutations, where there's often no need for the
query to return a value.

.. code-block:: javascript

  await client.execute(`insert Movie {
    title := "Avengers: Endgame"
  };`);

You can also execute a "script" consisting of multiple
semicolon-separated statements in a single ``.execute`` call.

.. code-block:: javascript

  await client.execute(`
    insert Person { name := "Robert Downey Jr." };
    insert Person { name := "Scarlett Johansson" };
    insert Movie {
      title := <str>$title,
      actors := (
        select Person filter .name in {
          "Robert Downey Jr.",
          "Scarlett Johansson"
        }
      )
    }
  `, { title: "Iron Man 2" });

Parameters
----------

If your query contains parameters (e.g. ``$foo``), you can pass in values as
the second argument. This is true for all ``query*`` methods and ``execute``.

.. code-block:: javascript

  const INSERT_MOVIE = `insert Movie {
    title := <str>$title
  }`
  const result = await client.querySingle(INSERT_MOVIE, {
    title: "Iron Man"
  });
  console.log(result);
  // {id: "047c5893..."}

Remember that :ref:`parameters <ref_eql_params>` can only be *scalars* or
*arrays of scalars*.

Scripts
-------

Both ``execute`` and the ``query*`` methods support scripts (queries
containing multiple statements). The statements are run in an implicit
transaction (unless already in an explicit transaction), so the whole script
remains atomic. For the ``query*`` methods only the result of the final
statement in the script will be returned.

.. code-block:: javascript

  const result = await client.query(`
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
  // [{id: "5dd2557b..."}]

For more fine grained control of atomic exectution of multiple statements, use
the ``transaction()`` API.

Checking connection status
--------------------------

The client maintains a dynamically sized *pool* of connections under the hood.
These connections are initialized *lazily*, so no connection will be
established until the first time you execute a query.

If you want to explicitly ensure that the client is connected without running
a query, use the ``.ensureConnected()`` method.

.. code-block:: javascript

  import { createClient } from "gel";

  const client = createClient();

  async function main() {
    await client.ensureConnected();
    // client is now connected
  }

.. _gel-js-api-transaction:

Transactions
------------

The most robust way to execute transactional code is to use
the ``transaction()`` API:

.. code-block:: javascript

    await client.transaction(tx => {
      await tx.execute("insert User {name := 'Don'}");
    });

Note that we execute queries on the ``tx`` object in the above
example, rather than on the original ``client`` object.

The ``transaction()`` API guarantees that:

1. Transactions are executed atomically;
2. If a transaction fails due to retryable error (like
   a network failure or a concurrent update error), the transaction
   would be retried;
3. If any other, non-retryable error occurs, the transaction is rolled
   back and the ``transaction()`` block throws.

The *transaction* object exposes ``query()``, ``execute()``, ``querySQL()``,
``executeSQL()``, and other ``query*()`` methods that *clients* expose, with
the only difference that queries will run within the current transaction
and can be retried automatically.

The key implication of retrying transactions is that the entire
nested code block can be re-run, including any non-querying
JavaScript code. Here is an example:

.. code-block:: javascript

    const email = "timmy@example.com"

    await client.transaction(async tx => {
      await tx.execute(
        `insert User { email := <str>$email }`,
        { email },
      )

      await sendWelcomeEmail(email);

      await tx.execute(
        `insert LoginHistory {
          user := (select User filter .email = <str>$email),
          timestamp := datetime_current()
        }`,
        { email },
      )
    })

In the above example, the welcome email may be sent multiple times if the
transaction block is retried. Generally, the code inside the transaction block
shouldn't have side effects or run for a significant amount of time.

.. note::

  Transactions allocate expensive server resources and having
  too many concurrently running long-running transactions will
  negatively impact the performance of the DB server.

.. note::

  * RFC1004_
  * :js:meth:`Client.transaction\<T\>`

  .. _RFC1004: https://github.com/geldata/rfcs/blob/master/text/1004-transactions-api.rst


Next up
-------

If you're a TypeScript user and want autocompletion and type inference, head
over to the :ref:`Query Builder docs <gel-js-qb>`. If you're using plain
JavaScript that likes writing queries with composable code-first syntax, you
should check out the query builder too! If you're content writing queries as
strings, the vanilla Client API will meet your needs.
