.. _gel-python-intro:

======
Python
======

.. toctree::
   :maxdepth: 3
   :hidden:

   client
   api/types
   api/codegen
   api/advanced

**gel-python** is the official |Gel| driver for Python.  It provides both :ref:`blocking IO <gel-python-blocking-api-reference>` and :ref:`asyncio <gel-python-asyncio-api-reference>` implementations.

Installation
============

Install the `client package from PyPI <https://pypi.org/project/gel/>`_ using your package manager of choice.

.. tabs::

  .. code-tab:: bash
    :caption: pip

    $ pip install gel

  .. code-tab:: bash
    :caption: uv

    $ uv add gel

Basic Usage
===========

To start using Gel in Python, create an :py:class:`gel.Client` instance using :py:func:`gel.create_client` or :py:func:`gel.create_async_client` for AsyncIO. This client instance manages a pool of connections to the database which it discovers automatically from either being in a :gelcmd:`project init` directory or being provided connection details via Environment Variables. See :ref:`the environment section of the connection reference <ref_reference_connection_environments>` for more details and options.

.. note::

  If you're using |Gel| Cloud to host your development instance, you can use the :gelcmd:`cloud login` command to authenticate with |Gel| Cloud and then use the :gelcmd:`project init --server-instance <instance-name>` command to create a local project-linked instance that is linked to an Gel Cloud instance. For more details, see :ref:`the Gel Cloud guide <ref_guide_cloud>`.

.. tabs::

  .. code-tab:: python
    :caption: Blocking

    import datetime
    import gel

    client = gel.create_client()

    client.query("""
        INSERT User {
            name := <str>$name,
            dob := <cal::local_date>$dob
        }
    """, name="Bob", dob=datetime.date(1984, 3, 1))

    user_set = client.query(
        "SELECT User {name, dob} FILTER .name = <str>$name", name="Bob")
    # *user_set* now contains
    # Set{Object{name := 'Bob', dob := datetime.date(1984, 3, 1)}}

    client.close()

  .. code-tab:: python
    :caption: AsyncIO

    import asyncio
    import datetime
    import gel

    client = gel.create_async_client()

    async def main():
        await client.query("""
            INSERT User {
                name := <str>$name,
                dob := <cal::local_date>$dob
            }
        """, name="Bob", dob=datetime.date(1984, 3, 1))

        user_set = await client.query(
            "SELECT User {name, dob} FILTER .name = <str>$name", name="Bob")
        # *user_set* now contains
        # Set{Object{name := 'Bob', dob := datetime.date(1984, 3, 1)}}

        await client.aclose()

    asyncio.run(main())

.. _gel-python-connection-pool:

Client connection pools
-----------------------

For server-type applications that handle frequent requests and need the database connection for a short period of time while handling a request, you will want to use a connection pool. Both :py:class:`gel.Client` and :py:class:`gel.AsyncIOClient` come with such a pool.

For :py:class:`gel.Client`, all methods are thread-safe. You can share the same client instance safely across multiple threads, and run queries concurrently. Likewise, :py:class:`~gel.AsyncIOClient` is designed to be shared among different :py:class:`asyncio.Task`/coroutines for concurrency.

Below is an example of a web API server running `fastapi <https://fastapi.tiangolo.com/>`_:

.. code-block:: python

    import asyncio
    import gel
    from fastapi import FastAPI, Query

    app = FastAPI()

    @app.on_event("startup")
    async def startup_event():
        """Initialize the database client on startup."""
        app.state.client = gel.create_async_client()
        # Optional: explicitly start up the connection pool
        await app.state.client.ensure_connected()

    @app.get("/users")
    async def handle(
      name: str = Query(None)
    ):
        """Handle incoming requests."""
        client = app.state.client

        # Execute the query on any pool connection
        if name:
          result = await client.query_single(
              '''
                  SELECT User {first_name, email, bio}
                  FILTER .name = <str>$username
              ''', username=name)
        else:
          result = await client.query(
              '''
                  SELECT User {first_name, email, bio}
              ''')
        return result

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)

Note that the client instance itself is created synchronously. Pool connections are created lazily as they are needed. If you want to explicitly connect to the database in ``startup_event()``, use the ``ensure_connected()`` method on the client.

For more information, see API documentation of :ref:`the blocking client <gel-python-blocking-api-client>` and :ref:`the asynchronous client <gel-python-async-api-client>`.


Transactions
------------

To create a :ref:`transaction <ref_eql_transactions>` use the ``transaction()`` method on the client instance:

* :py:meth:`AsyncIOClient.transaction() <gel.AsyncIOClient.transaction>`
* :py:meth:`Client.transaction() <gel.Client.transaction>`


Example:

.. tabs::

  .. code-tab:: python
    :caption: Blocking

    for tx in client.transaction():
        with tx:
            tx.execute("INSERT User {name := 'Don'}")

  .. code-tab:: python
    :caption: AsyncIO

    async for tx in client.transaction():
        async with tx:
            await tx.execute("INSERT User {name := 'Don'}")

.. note::

  When not in an explicit transaction block, any changes to the database will be applied immediately.

For more information, see API documentation of transactions for :ref:`the blocking client <gel-python-blocking-api-transaction>` and :ref:`the AsyncIO client <gel-python-asyncio-api-transaction>`.


Code generation
===============

.. py:currentmodule:: gel

The ``gel-python`` package exposes a command-line tool to generate typesafe functions from ``*.edgeql`` files, using :py:mod:`dataclasses` for objects primarily.

.. code-block:: edgeql
  :caption: queries/get_user_by_name.edgeql

  with
      name := <str>$name,
  select User { first_name, email, bio }
  filter .name = name;

.. code-block:: bash

  $ gel-py
  # or
  $ python -m gel.codegen

.. code-block:: python

  import gel
  from .queries import get_user_by_name_sync_edgeql as get_user_by_name_qry

  client = gel.create_async_client()

  async def main():
    result = await get_user_by_name_qry.get_user_by_name(client, name="John")
    print(result)

  asyncio.run(main())

