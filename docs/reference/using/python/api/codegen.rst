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

Here's an example of a schema and a simple Python program using the generated models:

.. tabs::

  .. code-tab:: sdl
    :caption: :dotgel:`dbschema/default`

    module default {
      type Person {
        required name: str {
          constraint exclusive;
        }
        email: str;

        multi friends: Person;
      }
    }

  .. code-block:: python
    :caption: main.py

    import datetime
    from models import Person, std
    from gel import create_client

    def main():
        client = create_client()

        # Create a new Person instance and save it to the database
        bob = Person(name='Bob', email='robert@gel.com')
        client.save(bob)

        # Select all Person records
        people = client.query(Person)

        # Select all people with names like "Bob"
        bob_like = client.query(Person.filter(lambda p: std.ilike(p.name, '%bob%')))

        # Update an object
        bob.name = 'Robert'
        client.save(bob)

        # Delete an object
        client.execute(Person.filter(id=bob.id).delete())

        client.close()

    if __name__ == '__main__':
        main()

You can use the standard |Gel| client created by either :py:func:`~gel.create_client` or :py:func:`~gel.create_async_client` to work with the generated models or the query builder.

.. py:class:: GelModel

    A reflected Gel model.

    This is a base class for all reflected Pydantic Gel models. The specific reflected models will also feature fields based on the schema.

    There are also some common methods and fields available to all reflected models.

    .. py:attribute:: __defs__

        Field definitions for a given model.

        Every field present in the current model has a corresponding field *definition* in ``__defs__``. These definitions can be used when declaring custom models that may be cherry-picking the specific fields they need to reflect.

        .. code-block:: python

            class NewPerson(default.Person.__shapes__.NoId):
                # define a single field
                name: default.Person.__defs__.name


            client = create_client()

            def make_person(name):
                person = NewPerson(name=name)
                client.save(person)
                # id is always populated after saving a new object
                return person.id

    .. py:attribute:: __shapes__

        Various ``GelModel`` mixin types based on the current model.

        There are several template types available via ``__shapes__``, each of which can be used to construct a custom model type. These custom types are useful for validating data (prior to :py:meth:`Client.sync`), working with partial data (so that ``sync()`` does not attempt to re-fetch unnecessary fields), or working with ad-hoc computed fields that aren't represented in the schema and thus aren't part of regular reflected types.

        Here's a list of available ``__shapes__``:

        * ``Base`` - marks this as the specific type, no field definitions.
        * ``NoId`` - an alias to ``Base``.
        * ``RequiredId`` - this model must have an ``id``.
        * ``OptionalId`` - this model may have an ``id``.
        * ``PropsAsDeclared`` - this model includes all properties (except ``id``) as declared in the schema.
        * ``PropsAsOptional`` - this model includes all properties (except ``id``) as optional fields.
        * ``LinksAsDeclared`` - this model includes all links as declared in the schema.
        * ``LinksAsOptional`` - this model includes all links as optional fields.
        * ``Create`` - a combination of ``NoId``, ``PropsAsDeclared`` and ``LinksAsDeclared``; useful for validating new objects.
        * ``Read`` - a combination of ``RequiredId`` and ``PropsAsDeclared``; useful for reading shallow objects (such as given by ``.select("*")``).
        * ``Update`` - a combination of ``RequiredId``, ``PropsAsOptional``, and ``LinksAsOptional``; useful for validating objects that need to be updated, but only some fields are expected to be provided.

        The following is an example of using a custom model to validate a new ``Person`` that's only given the required ``name``:

        .. code-block:: python

            class NewPerson(default.Person.__shapes__.NoId):
                # define a single field
                name: default.Person.__defs__.name


            client = create_client()

            def make_person(name):
                person = NewPerson(name=name)
                client.save(person)
                # id is always populated after saving a new object
                return person.id

        A different example of using a custom computed field:

        .. code-block:: python

            class CustomPerson(default.Person.__shapes__.Read):
                # custom field
                name_length: std.int64


            client = create_client()
            res = client.query(
                CustomPerson.select(
                    "*",
                    name_length=lambda p: std.len(p.name)
                ).order_by(name=True)
            )

    .. py:method:: __init__(self, /, id, **kwargs):

        Constructs a new or per-existing Gel object.

        :param uuid.UUID id: The ``id`` of the pre-existing object in Gel.
        :param kwargs: Fields and their values.

        The most basic API of the generated models is the object constructor. There's a Pydantic class corresponding to each reflected concrete Gel type. The reflected type will have fields corresponding to Gel properties and links. Properties will be reflected as their corresponding Python built-in types where possible. If there is no corresponding built-in type, a custom Gel type will be used. Link fields use the reflected object types.

        For new objects, *id* is always omitted as it is generated on the server-side. Values for required fields must be provided when instantiating a model. Values of optional fields or fields with default values may be omitted, though.

        For existing objects the *id* value must be specified. All other fields are optional in this case. The passed fields will be used to update the server-side field values.

        Once the models are instantiated, they can be synced to the Gel database via a standard gel client. The :py:meth:`Client.sync` method will write all the passed objects to the database. This includes any objects connected via links. This means that an entire object tree structure can be written to the database by passing the root object to :py:meth:`Client.sync`. Once the objects are successfully written, the :py:meth:`Client.sync` method will also re-fetch their properties and update the Python objects. This means that after :py:meth:`Client.sync` the ``id`` as well as properties that have default values will now be populated.

        .. code-block:: python

            alice = Person(name='Alice')
            billie = Person(
                name='Billie',
                email='billie@gel.com',
            )
            cameron = Person(
                name='Cameron',
                email='cameron@gel.com',
                friends=[alice, billie],
            )

            # Even though we only sync(cameron), the alice and billie
            # objects will also be synced, since they are linked to
            # cameron.
            client.sync(cameron)

            # We can expect ids to be populated by sync()
            print(alice.id, billie.id, cameron.id)

        Here's an example of updating an existing object by using the ``id``:

        .. code-block:: python

            def update_email(id: uuid.UUID, email: str):
                # Pass id to refer to a specific object, then pass the email
                # since that's the field that needs to be updated.
                p = Person(id=id, email=email)
                client.sync(p)

    .. py:method:: select(*elements, **kwargs):

        Creates a ``select`` query for this object type.

        :param elements: The strings ``"*"`` and ``"**"`` can be used as ``select`` splats.
        :param kwargs: Fields and that need to be included in the fetched shape.

        This method specifies the shape that should be fetched. You can use the splats (``"*"`` or ``"**"``) or specify fields individually.

        The most basic way to include a field is to pass ``field_name=True`` (``False`` would indicate that the field should not be included).

        .. code-block:: python

            res = client.query(
                default.Person.select(
                    name=True,
                    email=True,
                )
            )

        It is also possible to pass some other expression, which will be treated as an ad-hoc computed field.

        .. code-block:: python

            # Replace the name with upper-case name
            res = client.query(
                default.Person.select(
                    name=std.str_upper(default.Person.name),
                )
            )

        For a sub-query the expression for the field should be a function with one parameter. The parameter must be the same type as the type on which ``.select()`` is invoked. The function should return a query-builder expression which will be used as the sub-query. This is commonly done to select nested shapes.

        .. code-block:: python

            # Provide a nested sub-query for fetching friends
            res = client.query(
                default.Person.select(
                    name=True,
                    friends=lambda p: p.friends.select(
                        name=True,
                    ),
                )
            )

        Replacing an existing field with a computed can also be done with a lambda:

        .. code-block:: python

            # Replace the name with upper-case name (using lambda)
            res = client.query(
                default.Person.select(
                    name=lambda p: std.str_upper(p.name),
                )
            )

        Arbitrary sub-queries are also possible, although they need to be used in conjunction with a model that has the corresponding ad-hoc field declared.

        .. code-block:: python

            class MyPerson(default.Person):
                name_upper: std.str


            # Fetch both name and upper-case name
            res = client.query(
                MyPerson.select(
                    name=True,
                    name_upper=lambda p: std.str_upper(p.name),
                )
            )

    .. py:method:: filter(*exprs, **kwargs):

        Creates a ``filter`` clause.

        :param exprs: Filtering expressions.
        :param kwargs: Fields and values to be used for filtering.

        The simplest way to use ``.filter()`` is to provide the fields and values that need to be filtered as *kwargs*.

        .. code-block:: python

            alice = client.get(
                default.Person.filter(name="Alice")
            )
            billie = client.get(
                default.Person.filter(
                    name="Billie",
                    email="billie@gel.com",
                )
            )

        It's also possible to use arbitrary expressions for filtering. One or more valid query builder expressions can be passed to the filter method. Since filtering is usually performed based on some of the object fields, *exprs* should be one or more functions with one parameter. The parameter must be the same type as the type on which ``.filter()`` is invoked. The function should return a query-builder expression which will be used as the filtering sub-query.

        .. code-block:: python

            # Get people with short names
            res = client.query(
                default.Person.filter(
                    lambda p: std.len(p.name) <= 4
                )
            )

        Multiple expressions will be combined with an ``and`` in EdgeQL.

        .. code-block:: python

            # Get people with short names starting with 'A'
            res = client.query(
                default.Person.filter(
                    lambda p: std.ilike(p.name, "a%"),
                    lambda p: std.len(p.name) <= 4,
                )
            )

        If you need to use an ``or`` in your filter, the reflected ``std`` module has one for you:

        .. code-block:: python

            # Get people with short names OR names starting with 'A'
            res = client.query(
                default.Person.filter(
                    lambda p: std.or_(
                      std.ilike(p.name, "a%"),
                      std.len(p.name) <= 4,
                    )
                )
            )

    .. py:method:: order_by(*exprs, **kwargs):

        Creates an :ref:`order by <ref_eql_select_order>` clause.

        :param exprs: An ``order by`` query builder expression.
        :param kwargs: Fields to be used for ordering and order direction.

        The most basic use of this method involves using *kwagrs* where the key is the field name and the value is simply ``True`` (indicating that it must be used in ordering).

        .. code-block:: python

            # Query people ordered by name
            res = client.query(
                default.Person.order_by(name=True)
            )

        The order in which the *kwargs* are specified determines which fields take priority when ordering.

        .. code-block:: python

            # Query items ordered by price, then by name
            res = client.query(
                default.Item.order_by(price=True, name=True)
            )

        It is also possible to specify the direction of ordering and the handling of empty sets by passing either a string or a tuple with two strings as the kwarg value:

        .. code-block:: python

            # Query people by name in ascending order
            ppl = client.query(
                default.Person.order_by(name="asc")
            )

            # Query people by name in descending order
            ppl_desc = client.query(
                default.Person.order_by(name="desc")
            )

            # Query people by email in ascending order, empty first
            ppl_efirst = client.query(
                default.Person.order_by(email=("asc", "empty first"))
            )

            # Query people by email in ascending order, empty last
            ppl_elast = client.query(
                default.Person.order_by(email=("asc", "empty last"))
            )

        It is also possible to pass valid query builder expressions as *exprs* to specify the order, if some non-trivial sub-query is required:

        .. code-block:: python

            # Order people by name length, then by name
            res = client.query(
                default.Person.order_by(
                    lambda p: std.len(p.name),
                    name=True,
                )
            )

    .. py:method:: offset(expr):

        Creates an :ref:`offset <ref_eql_select_pagination>` clause.

        :param expr: The expression ofr ``offset`` value.

        This is the kind of clause that makes sense in combination with ``.order_by()`` since an offset without ordering is unpredictable.

        Typically, the offset value is provided by a Python integer (literal or variable):

        .. code-block:: python

            # skip the first 5 records
            res = client.query(
                default.Person.order_by(name=True).offset(5)
            )

        However, it is also valid to supply any query-builder expression that represents an integer in EdgeQL:

        .. code-block:: python

            # An expression for fetching offset setting
            expr = std.assert_single(default.AdminSettings).offset_value
            # Use it in the query
            res = client.query(
                default.Person.order_by(name=True).offset(expr)
            )

    .. py:method:: limit(expr):

        Creates an :ref:`limit <ref_eql_select_pagination>` clause.

        :param expr: The expression ofr ``limit`` value.

        This is the kind of clause that makes sense in combination with ``.order_by()`` since a limit without ordering is unpredictable.

        Typically, the limit value is provided by a Python integer (literal or variable):

        .. code-block:: python

            # get the first 5 records
            res = client.query(
                default.Person.order_by(name=True).limit(5)
            )

        However, it is also valid to supply any query-builder expression that represents an integer in EdgeQL:

        .. code-block:: python

            # An expression for fetching limit setting
            expr = std.assert_single(default.AdminSettings).limit_value
            # Use it in the query
            res = client.query(
                default.Person.order_by(name=True).limit(expr)
            )

    .. py:method:: update(*elements, **kwargs):

        Creates an ``update`` query for this object type.

        :param kwargs: Fields and that need to be updated.

        This method will turn the query builder expression it's invoked on into an ``update`` query. So it should be used **after** setting up ``.filter()``, ``.order_by()``, ``.offset()``, or ``.limit()``.

        In the simple case the *kwargs* consist of a field name and the value that field should be updated to:

        .. code-block:: python

            # Update the name of a specific Person
            client.query(
                default.Person.filter(
                    name="Alice"
                ).update(
                    name="ALICE",
                    email="alice@geldata.com",
                )
            )

        It's also possible to use arbitrary expressions for updates. A valid query builder expression can be passed as one of the *kwargs* values. It must be a function with one parameter. The parameter must be the same type as the type on which ``.update()`` is invoked. The function should return a query-builder expression which will be used as the new value.

        .. code-block:: python

            # Update all Person records to make names upper case
            # and emails lower case.
            client.query(
                default.Person.update(
                    name=lambda p: std.str_upper(p.name),
                    email=lambda p: std.str_lower(p.email),
                )
            )

    .. py:method:: delete():

        Creates a ``delete`` query for this object type.

        This method will wrap the query builder expression it's invoked on into a ``delete`` query. So it should be used **after** setting up ``.filter()``, ``.order_by()``, ``.offset()``, or ``.limit()``.

        .. code-block:: python

            # delete a specific Person using the name filter
            client.query(
                default.Person.filter(name="Alice").delete()
            )
            # delete several objects based on offset and limit
            client.query(
                default.Person.order_by(
                  name=True
                ).offset(5).limit(2).delete()
            )
