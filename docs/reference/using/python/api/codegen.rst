.. _gel-python-codegen:

===============
Code Generation
===============

.. py:currentmodule:: gel

The ``gel-python`` package exposes a command-line tool to generate various kinds of type-safe code from EdgeQL queries and your schema:

- ``queries``: typesafe functions from ``*.edgeql`` files, using :py:mod:`dataclasses` for objects primarily.
- ``models``: a programmatic query-builder and Pydantic-based models generator.

.. code-block:: bash

  $ uvx gel generate py/queries
  $ uvx gel generate py/models

The :gelcmd:`generate` commands supports the same set of :ref:`connection options <ref_cli_gel_connopts>` as the ``gel`` CLI.

.. code-block::

    -I, --instance <instance>
    --dsn <dsn>
    --credentials-file <path/to/credentials.json>
    -H, --host <host>
    -P, --port <port>
    -b, --branch <branch>
    -u, --user <user>
    --password
    --password-from-stdin
    --tls-ca-file <path/to/certificate>
    --tls-security <insecure | no_host_verification | strict | default>

Queries
=======

Consider a simple query that lives in a file called ``get_number.edgeql``:

.. code-block:: edgeql

  select <int64>$arg;

Running the code generator will generate a new file called ``get_number_async_edgeql.py`` containing the following code (roughly):

.. code-block:: python

  from __future__ import annotations
  import gel


  async def get_number(
      client: gel.AsyncIOClient,
      *,
      arg: int,
  ) -> int:
      return await client.query_single(
          """\
          select <int64>$arg\
          """,
          arg=arg,
      )

Target
~~~~~~

By default, the generated code uses an ``async`` API. The generator supports additional targets via the ``--target`` flag.

.. code-block:: bash

  $ gel generate py/queries --target async        # generate async function (default)
  $ gel generate py/queries --target blocking     # generate blocking code

The names of the generated files will differ accordingly: ``{query_filename}_{target}_edgeql.py``.

Single-file mode
~~~~~~~~~~~~~~~~

It may be preferable to generate a single file containing all the generated functions. This can be done by passing the ``--file`` flag.

.. code-block:: bash

  $ gel generate py/queries --file

This generates a single file called ``generated_{target}_edgeql.py`` in the root of your project.

Models
======

The ``models`` generator will generate Pydantic classes and a programmatic query builder. It reflects your full schema, as well as our standard library into functions and Pydantic classes which we've enhanced to make a truly powerful type-safe programmatic data layer.

.. code-block:: python

    import datetime
    from models import User, std
    from gel import create_client

    def main():
        client = create_client()

        # Create a new User instance and save it to the database
        bob = User(name='Bob', dob=datetime.date(1984, 3, 1))
        client.save(bob)

        # Select all Users
        users = client.query(User)

        # Select all users with names like "Bob"
        bob_like = client.query(User.filter(lambda u: std.ilike(u.name, '%bob%')))

        # Update an object
        bob.name = 'Robert'
        client.save(bob)

        # Delete an object
        client.execute(User.filter(id=bob.id).delete())

        client.close()

    if __name__ == '__main__':
        main()
