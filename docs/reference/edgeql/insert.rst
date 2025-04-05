.. _ref_eql_insert:

Insert
======

:eql-statement:
:eql-haswith:

.. api-index:: insert, :=

``insert`` -- create a new object in a database

The code samples on this page assume the following schema:

.. code-block:: sdl

    module default {
      abstract type Person {
        required name: str { constraint exclusive };
      }

      type Hero extending Person {
        secret_identity: str;
        multi villains := .<nemesis[is Villain];
      }

      type Villain extending Person {
        nemesis: Hero;
      }

      type Movie {
        required title: str { constraint exclusive };
        required release_year: int64;
        multi characters: Person;
      }
    }


.. _ref_eql_insert_basic:

Basic usage
-----------

You can ``insert`` instances of any *non-abstract* object type.

.. code-block:: edgeql-repl

  db> insert Hero {
  ...   name := "Spider-Man",
  ...   secret_identity := "Peter Parker"
  ... };
  {default::Hero {id: b0fbe9de-3e90-11ec-8c12-ffa2d5f0176a}}

Similar to :ref:`selecting fields <ref_eql_shapes>` in ``select``, ``insert``
statements include a *shape* specified with ``curly braces``; the values of
properties/links are assigned with the ``:=`` operator.

Optional links or properties can be omitted entirely, as well as those with a
``default`` value (like ``id``).

.. code-block:: edgeql-repl

  db> insert Hero {
  ...   name := "Spider-Man"
  ...   # secret_identity is omitted
  ... };
  {default::Hero {id: b0fbe9de-3e90-11ec-8c12-ffa2d5f0176a}}

You can only ``insert`` instances of concrete (non-abstract) object types.

.. code-block:: edgeql-repl

  db> insert Person {
  ...   name := "The Man With No Name"
  ... };
  error: QueryError: cannot insert into abstract object type 'default::Person'

By default, ``insert`` returns only the inserted object's ``id`` as seen in the
examples above. If you want to get additional data back, you may wrap your
``insert`` with a ``select`` and apply a shape specifying any properties and
links you want returned:

.. code-block:: edgeql-repl

  db> select (insert Hero {
  ...   name := "Spider-Man"
  ...   # secret_identity is omitted
  ... }) {id, name};
  {
    default::Hero {
      id: b0fbe9de-3e90-11ec-8c12-ffa2d5f0176a,
      name: "Spider-Man"
    }
  }

You can use :ref:`ref_eql_with` to tidy this up if you prefer:

.. code-block:: edgeql-repl

  db> with NewHero := (insert Hero {
  ...   name := "Spider-Man"
  ...   # secret_identity is omitted
  ... })
  ... select NewHero {
  ...   id,
  ...   name,
  ... }
  {
    default::Hero {
      id: b0fbe9de-3e90-11ec-8c12-ffa2d5f0176a,
      name: "Spider-Man"
    }
  }


.. _ref_eql_insert_links:

Inserting links
---------------

EdgeQL's composable syntax makes link insertion painless. Below, we insert
"Spider-Man: No Way Home" and include all known heroes and villains as
``characters`` (which is basically true).

.. code-block:: edgeql-repl

  db> insert Movie {
  ...   title := "Spider-Man: No Way Home",
  ...   release_year := 2021,
  ...   characters := (
  ...     select Person
  ...     filter .name in {
  ...       'Spider-Man',
  ...       'Doctor Strange',
  ...       'Doc Ock',
  ...       'Green Goblin'
  ...     }
  ...   )
  ... };
  {default::Movie {id: 9b1cf9e6-3e95-11ec-95a2-138eeb32759c}}

To assign to the ``Movie.characters`` link, we're using a *subquery*. This
subquery is executed and resolves to a set of type ``Person``, which is
assignable to ``characters``.  Note that the inner ``select Person`` statement
is wrapped in parentheses; this is required for all subqueries in EdgeQL.

Now let's assign to a *single link*.

.. code-block:: edgeql-repl

  db> insert Villain {
  ...   name := "Doc Ock",
  ...   nemesis := (select Hero filter .name = "Spider-Man")
  ... };


This query is valid because the inner subquery is guaranteed to return at most
one ``Hero`` object, due to the uniqueness constraint on ``Hero.name``. If you
are filtering on a non-exclusive property, use ``assert_single`` to guarantee
that the subquery will return zero or one results. If more than one result is
returned, this query will fail at runtime.

.. code-block:: edgeql-repl

  db> insert Villain {
  ...   name := "Doc Ock",
  ...   nemesis := assert_single((
  ...     select Hero
  ...     filter .secret_identity = "Peter B. Parker"
  ...   ))
  ... };


.. _ref_eql_insert_nested:

Nested inserts
--------------

Just as we used subqueries to populate links with existing objects, we can also
execute *nested inserts*.

.. code-block:: edgeql-repl

  db> insert Villain {
  ...   name := "The Mandarin",
  ...   nemesis := (insert Hero {
  ...     name := "Shang-Chi",
  ...     secret_identity := "Shaun"
  ...   })
  ... };
  {default::Villain {id: d47888a0-3e7b-11ec-af13-fb68c8777851}}


Now let's write a nested insert for a ``multi`` link.

.. code-block:: edgeql-repl

  db> insert Movie {
  ...   title := "Black Widow",
  ...   release_year := 2021,
  ...   characters := {
  ...     (select Hero filter .name = "Black Widow"),
  ...     (insert Hero { name := "Yelena Belova"}),
  ...     (insert Villain {
  ...       name := "Dreykov",
  ...       nemesis := (select Hero filter .name = "Black Widow")
  ...     })
  ...   }
  ... };
  {default::Movie {id: af706c7c-3e98-11ec-abb3-4bbf3f18a61a}}

We are using :ref:`set literal syntax <ref_eql_set_constructor>` to construct a
set literal containing several ``select`` and ``insert`` subqueries. This set
contains a mix of ``Hero`` and ``Villain`` objects; since these are both
subtypes of ``Person`` (the expected type of ``Movie.characters``), this is
valid.

You also can't *assign* to a computed property or link; these fields don't
actually exist in the database.

.. code-block:: edgeql-repl

  db> insert Hero {
  ...   name := "Ant-Man",
  ...   villains := (select Villain)
  ... };
  error: QueryError: modification of computed link 'villains' of object type
  'default::Hero' is prohibited

.. _ref_eql_insert_with:

With block
----------

.. api-index:: with

In the previous query, we selected Black Widow twice: once in the
``characters`` set and again as the ``nemesis`` of Dreykov. In circumstances
like this, pulling a subquery into a ``with`` block lets you avoid
duplication.

.. code-block:: edgeql-repl

  db> with black_widow := (select Hero filter .name = "Black Widow")
  ... insert Movie {
  ...   title := "Black Widow",
  ...   release_year := 2021,
  ...   characters := {
  ...     black_widow,
  ...     (insert Hero { name := "Yelena Belova"}),
  ...     (insert Villain {
  ...       name := "Dreykov",
  ...       nemesis := black_widow
  ...     })
  ...   }
  ... };
  {default::Movie {id: af706c7c-3e98-11ec-abb3-4bbf3f18a61a}}


The ``with`` block can contain an arbitrary number of clauses; later clauses
can reference earlier ones.

.. code-block:: edgeql-repl

  db> with
  ...  black_widow := (select Hero filter .name = "Black Widow"),
  ...  yelena := (insert Hero { name := "Yelena Belova"}),
  ...  dreykov := (insert Villain {name := "Dreykov", nemesis := black_widow})
  ... insert Movie {
  ...   title := "Black Widow",
  ...   release_year := 2021,
  ...   characters := { black_widow, yelena, dreykov }
  ... };
  {default::Movie {id: af706c7c-3e98-11ec-abb3-4bbf3f18a61a}}


.. _ref_eql_insert_conflicts:
.. _ref_eql_statements_insert_unless:

Conflicts
---------

.. api-index:: unless conflict on, else

|Gel| provides a general-purpose mechanism for gracefully handling possible
exclusivity constraint violations. Consider a scenario where we are trying to
``insert`` Eternals (the ``Movie``), but we can't remember if it already exists
in the database.

.. code-block:: edgeql-repl

  db> insert Movie {
  ...   title := "Eternals",
  ...   release_year := 2021
  ... }
  ... unless conflict on .title
  ... else (select Movie);
  {default::Movie {id: af706c7c-3e98-11ec-abb3-4bbf3f18a61a}}

This query attempts to ``insert`` Eternals. If it already exists in the
database, it will violate the uniqueness constraint on ``Movie.title``, causing
a *conflict* on the ``title`` field. The ``else`` clause is then executed and
returned instead. In essence, ``unless conflict`` lets us "catch" exclusivity
conflicts and provide a fallback expression.

.. note::

  Note that the ``else`` clause is simply ``select Movie``. There's no need to
  apply additional filters on ``Movie``; in the context of the ``else`` clause,
  ``Movie`` is bound to the conflicting object.

.. note::

    Using ``unless conflict`` on :ref:`multi properties
    <ref_datamodel_props_cardinality>` is only supported in 2.10 and later.

.. _ref_eql_upsert:

Upserts
^^^^^^^

There are no limitations on what the ``else`` clause can contain; it can be any
EdgeQL expression, including an :ref:`update <ref_eql_update>` statement. This
lets you express *upsert* logic in a single EdgeQL query.

.. code-block:: edgeql-repl

  db> with
  ...   title := "Eternals",
  ...   release_year := 2021
  ... insert Movie {
  ...   title := title,
  ...   release_year := release_year
  ... }
  ... unless conflict on .title
  ... else (
  ...   update Movie set { release_year := release_year }
  ... );
  {default::Movie {id: f1bf5ac0-3e9d-11ec-b78d-c7dfb363362c}}

When a conflict occurs during the initial ``insert``, the statement falls back
to the ``update`` statement in the ``else`` clause. This updates the
``release_year`` of the conflicting object.

.. note::

    It can be useful to know the outcome of an upsert. Here's an example
    showing how you can return that:

    .. code-block:: edgeql-repl

      db> with
      ...   title := "Eternals",
      ...   release_year := 2021,
      ...   movie := (
      ...     insert Movie {
      ...       title := title,
      ...       release_year := release_year
      ...     }
      ...     unless conflict on .title
      ...     else (
      ...       update Movie set { release_year := release_year }
      ...     )
      ...   )
      ... select movie {
      ...   is_new := (movie not in Movie)
      ... };
      {default::Movie {is_new: true}}

    This technique exploits the fact that a ``select`` will not return an
    object inserted in the same query. We know that, if the record exists, we
    updated it. If it does not, we inserted it.

    By wrapping your upsert in a ``select`` and putting a shape on it that
    queries for the object and returns whether or not it exists (as ``is_new``,
    in this example), you can easily see whether the object was inserted or
    updated.

    If you want to also return some of the ``Movie`` object's data, drop
    additional property names into the shape alongside ``is_new``. If you're on
    3.0+, you can add ``Movie.*`` to the shape alongside ``is_new`` to get back
    all of the ``Movie`` object's properties. You could even silo the data off,
    keeping it separate from the ``is_new`` computed value like this:

    .. code-block:: edgeql-repl

      db> with
      ...   title := "Eternals",
      ...   release_year := 2021,
      ...   movie := (
      ...     insert Movie {
      ...       title := title,
      ...       release_year := release_year
      ...     }
      ...     unless conflict on .title
      ...     else (
      ...       update Movie set { release_year := release_year }
      ...     )
      ...   )
      ... select {
      ...   data := (select movie {*}),
      ...   is_new := (movie not in Movie)
      ... };
      {
        {
          data: {
            default::Movie {
              id: 6880d0ba-62ca-11ee-9608-635818746433,
              release_year: 2021,
              title: 'Eternals'
            }
          },
          is_new: false
        }
      }


Suppressing failures
^^^^^^^^^^^^^^^^^^^^

.. api-index:: unless conflict

The ``else`` clause is optional; when omitted, the ``insert`` statement will
return an *empty set* if a conflict occurs. This is a common way to prevent
``insert`` queries from failing on constraint violations.

.. code-block:: edgeql-repl

  db> insert Hero { name := "The Wasp" } # initial insert
  ... unless conflict;
  {default::Hero {id: 35b97a92-3e9b-11ec-8e39-6b9695d671ba}}
  db> insert Hero { name := "The Wasp" } # The Wasp now exists
  ... unless conflict;
  {}

.. _ref_eql_insert_bulk:

Bulk inserts
------------

Bulk inserts are performed by passing in a JSON array as a :ref:`query
parameter <ref_eql_params>`, :eql:func:`unpacking <json_array_unpack>` it, and
using a :ref:`for loop <ref_eql_for>` to insert the objects.

.. code-block:: edgeql-repl

  db> with
  ...   raw_data := <json>$data,
  ... for item in json_array_unpack(raw_data) union (
  ...   insert Hero { name := <str>item['name'] }
  ... );
  Parameter <json>$data: [{"name":"Sersi"},{"name":"Ikaris"},{"name":"Thena"}]
  {
    default::Hero {id: 35b97a92-3e9b-11ec-8e39-6b9695d671ba},
    default::Hero {id: 35b97a92-3e9b-11ec-8e39-6b9695d671ba},
    default::Hero {id: 35b97a92-3e9b-11ec-8e39-6b9695d671ba},
    ...
  }


.. _ref_eql_statements_insert:

EdgeQL Syntax
-------------

.. eql:synopsis::

    [ with <with-spec> [ ,  ... ] ]
    insert <expression> [ <insert-shape> ]
    [ unless conflict
        [ on <property-expr> [ else <alternative> ] ]
    ] ;


Overview
^^^^^^^^

When evaluating an ``insert`` statement, *expression* is used solely to
determine the *type* of the inserted object and is not evaluated in any
other way.

If a value for a *required* link is evaluated to an empty set, an error is
raised.

It is possible to insert multiple objects by putting the ``insert``
into a :eql:stmt:`for` statement.

See :ref:`ref_eql_forstatement` for more details.

:eql:synopsis:`with`
    Alias declarations.

    The ``with`` clause allows specifying module aliases as well
    as expression aliases that can be referenced by the :eql:stmt:`update`
    statement.  See :ref:`ref_eql_statements_with` for more information.

:eql:synopsis:`<expression>`
    An arbitrary expression returning a set of objects to be updated.

    .. eql:synopsis::

        insert <expression>
        [ "{" <link> := <insert-value-expr> [, ...]  "}" ]

.. _ref_eql_statements_conflict:

:eql:synopsis:`unless conflict [ on <property-expr> ]`
    :index: unless conflict

    Handler of conflicts.

    This clause allows to handle specific conflicts arising during
    execution of ``insert`` without producing an error.  If the
    conflict arises due to exclusive constraints on the properties
    specified by *property-expr*, then instead of failing with an
    error the ``insert`` statement produces an empty set (or an
    alternative result).

    The exclusive constraint on ``<property-expr>`` cannot be defined on a
    parent type.

    The specified *property-expr* may be either a reference to a property (or
    link) or a tuple of references to properties (or links).

    A caveat, however, is that ``unless conflict`` will not prevent
    conflicts caused between multiple DML operations in the same
    query; inserting two conflicting objects (through use of ``for``
    or simply with two ``insert`` statements) will cause a constraint
    error.

    Example:

    .. code-block:: edgeql

        insert User { email := 'user@example.org' }
        unless conflict on .email

    .. code-block:: edgeql

        insert User { first := 'Jason', last := 'Momoa' }
        unless conflict on (.first, .last)

:eql:synopsis:`else <alternative>`
    Alternative result in case of conflict.

    This clause can only appear after ``unless conflict`` clause. Any
    valid expression can be specified as the *alternative*. When a
    conflict arises, the result of the ``insert`` becomes the
    *alternative* expression (instead of the default ``{}``).

    In order to refer to the conflicting object in the *alternative*
    expression, the name used in the ``insert`` must be used (see
    the :ref:`example <ref_eql_statements_insert_unless>`.)

Output
^^^^^^

The result of an ``insert`` statement used as an *expression* is a
singleton set containing the inserted object.


.. note::

    Statements in EdgeQL represent an atomic interaction with the
    database. From the point of view of a statement all side-effects
    (such as database updates) happen after the statement is executed.
    So as far as each statement is concerned, it is some purely
    functional expression evaluated on some specific input (database
    state).



.. list-table::
  :class: seealso

  * - **See also**
  * - :ref:`Cheatsheets > Inserting data <ref_cheatsheet_insert>`
