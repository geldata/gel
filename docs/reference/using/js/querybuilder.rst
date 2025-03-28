.. _gel-js-qb:

=======================
Query Builder Generator
=======================

.. index:: querybuilder, generator, typescript

Overview
========

The |Gel| query builder provides a **code-first** way to write **fully-typed** EdgeQL queries with TypeScript. Unlike traditional ORMs that offer a limited set of operations, the query builder leverages EdgeQL's composable nature, allowing developers to dynamically construct complex queries by combining expressions. This approach is particularly useful in scenarios where queries need to change dynamically at runtime. Even for static queries, the query builder offers the benefits of type safety and autocompletion, helping you write correct queries with confidence while maintaining the full expressiveness of EdgeQL.

Usage Example
-------------

All queries on this page assume the following schema.

.. code-block:: sdl
  :class: collapsible

  module default {
    type Person {
      required name: str;
    }

    abstract type Content {
      required title: str {
        constraint exclusive;
      };
      multi actors: Person {
        character_name: str;
      };
    }

    type Movie extending Content {
      release_year: int64;
    }

    type TVShow extending Content {
      num_seasons: int64;
    }
  }


.. code-block:: typescript

  import { createClient } from "gel";
  import e from "./dbschema/edgeql-js";

  const client = createClient();

  const query = e.select(e.Movie, () => ({
    id: true,
    title: true,
    actors: {
      name: true,
    },
  }));

  const result = await query.run(client)
  /*
    {
      id: string;
      title: string;
      actors: { name: string; }[];
    }[]
  */

Is it an ORM?
-------------

No—it's better! Like any modern TypeScript ORM, the query builder gives you full typesafety and autocompletion, but without the power and `performance <https://github.com/geldata/imdbench>`_ tradeoffs. You have access to the **full power** of EdgeQL and can write EdgeQL queries of arbitrary complexity. And since |Gel| compiles each EdgeQL query into a single, highly-optimized SQL query, your queries stay fast, even when they're complex.

Why use the query builder?
--------------------------

* **Type inference!**
    If you're using TypeScript, the result type of *all queries* is automatically inferred for you. For the first time, you don't need an ORM to write strongly typed queries.

* **Auto-completion!**
    You can write queries full autocompletion on EdgeQL keywords, standard library functions, and link/property names.

* **Type checking!**
    In the vast majority of cases, the query builder won't let you construct invalid queries. This eliminates an entire class of bugs and helps you write valid queries the first time.

* **Close to EdgeQL!**
    The goal of the query builder is to provide an API that is as close as possible to EdgeQL itself while feeling like idiomatic TypeScript.

Installation
------------

Install the ``gel`` package as a production dependency and the ``@gel/generate`` package as a development dependency.

.. tabs::

    .. code-tab:: bash
      :caption: npm

      $ npm install --save-prod gel          # database client
      $ npm install --save-dev @gel/generate # generators

    .. code-tab:: bash
      :caption: yarn

      $ yarn add gel                 # database client
      $ yarn add --dev @gel/generate # generators

    .. code-tab:: bash
      :caption: pnpm

      $ pnpm add --save-prod gel          # database client
      $ pnpm add --save-dev @gel/generate # generators

    .. code-tab:: bash
      :caption: bun

      $ bun add gel                 # database client
      $ bun add --dev @gel/generate # generators

    .. code-tab:: bash
      :caption: deno

      $ deno add npm:gel                 # database client
      $ deno add --dev npm:@gel/generate # generators


Generation
----------

The following command will run the ``edgeql-js`` query builder generator.

.. tabs::

  .. code-tab:: bash
    :caption: npm

    $ npx @gel/generate edgeql-js

  .. code-tab:: bash
    :caption: yarn

    $ yarn run -B generate edgeql-js

  .. code-tab:: bash
    :caption: pnpm

    $ pnpm exec generate edgeql-js

  .. code-tab:: bash
    :caption: Deno

    $ deno run --allow-all npm:@gel/generate edgeql-js

  .. code-tab:: bash
    :caption: Bun

    $ bunx @gel/generate edgeql-js

The generation command is configurable in a number of ways.

``--output-dir <path>``
  Sets the output directory for the generated files.

``--target <ts|cjs|esm|mts>``
  What type of files to generate.

``--force-overwrite``
  To avoid accidental changes, you'll be prompted to confirm whenever the
  ``--target`` has changed from the previous run. To avoid this prompt, pass
  ``--force-overwrite``.

The generator also supports all the :ref:`connection flags
<ref_cli_gel_connopts>` supported by the |Gel| CLI. These aren't
necessary when using a project or environment variables to configure a
connection.

.. note::

  Generators work by connecting to the database to get information about the current state of the schema. Make sure you run the generators again any time the schema changes so that the generated code is in-sync with the current state of the schema. The easiest way to do this is to add the generator command to the :ref:`schema.update.after hook <ref_reference_gel_toml_hooks>` in your :ref:`gel.toml <ref_reference_gel_toml>`.

.. _gel-js-execution:

Expressions
-----------

Throughout the documentation, we use the term "expression" a lot. This is a catch-all term that refers to *any query or query fragment* you define with the query builder. They all conform to an interface called ``Expression`` with some common functionality.

Most importantly, any expression can be executed with the ``.run()`` method, which accepts a ``Client`` or ``Transaction`` instance as the first argument. The result is ``Promise<T>``, where ``T`` is the inferred type of the query.

.. code-block:: typescript

  await e.str("hello world").run(client);
  // => "hello world"

  await e.set(e.int64(1), e.int64(2), e.int64(3)).run(client);
  // => [1, 2, 3]

  await e
    .select(e.Movie, () => ({
      title: true,
      actors: { name: true },
    }))
    .run(client);
  // => [{ title: "The Avengers", actors: [...]}]

.. _gel-js-objects:

Objects and Paths
-----------------

All object types in your schema are reflected into the query builder, properly namespaced by module.

.. code-block:: typescript

  e.default.Person;
  e.default.Movie;
  e.default.TVShow;
  e.my_module.SomeType;

For convenience, the contents of the ``default`` module are also available at the top-level of ``e``.

.. code-block:: typescript

  e.Person;
  e.Movie;
  e.TVShow;

Paths
^^^^^

EdgeQL-style *paths* are supported on object type references.

.. code-block:: typescript

  e.Person.name;              // Person.name
  e.Movie.title;              // Movie.title
  e.TVShow.actors.name;          // Movie.actors.name

Paths can be constructed from any object expression, not just the root types.

.. code-block:: typescript

  e.select(e.Person).name;
  // EdgeQL: (select Person).name

  e.op(e.Movie, "union", e.TVShow).actors;
  // EdgeQL: (Movie union TVShow).actors

  const ironMan = e.insert(e.Movie, {
    title: "Iron Man"
  });
  ironMan.title;
  // EdgeQL: (insert Movie { title := "Iron Man" }).title


.. _gel-js-objects-type-intersections:

Type intersections
^^^^^^^^^^^^^^^^^^

Use the type intersection operator to narrow the type of a set of objects. For instance, to represent the elements of an Account's watchlist that are of type ``TVShow``:

.. code-block:: typescript

  e.Person.acted_in.is(e.TVShow);
  // Person.acted_in[is TVShow]


Backlinks
^^^^^^^^^

All possible backlinks are auto-generated and can be auto-completed by TypeScript. They behave just like forward links. However, because they contain a special character (``<``), you must use bracket syntax instead of simple dot notation.

.. code-block:: typescript

  e.Person["<director[is Movie]"]
  // Person.<director[is Movie]

For convenience, these backlinks automatically combine the backlink operator and type intersection into a single key. However, the query builder also provides "plain" backlinks; these can be refined with the ``.is`` type intersection method.

.. code-block:: typescript

  e.Person['<director'].is(e.Movie);
  // Person.<director[is Movie]

Converting to EdgeQL
--------------------

.. index:: querybuilder, toedgeql

You can extract an EdgeQL representation of any expression calling the ``.toEdgeQL()`` method. Below is a number of expressions and the logical EdgeQL they produce. The query builder does some optimizing and scoping of the query, so the actual EdgeQL will look slightly different, but it's equivalent.

.. code-block:: typescript

  e.str("hello world").toEdgeQL();
  // => select "hello world"

  e.set(e.int64(1), e.int64(2), e.int64(3)).toEdgeQL();
  // => select {1, 2, 3}

  e.select(e.Movie, () => ({
    title: true,
    actors: { name: true }
  })).toEdgeQL();
  // => select Movie { title, actors: { name }}

Extracting the inferred type
----------------------------

The query builder *automatically infers* the TypeScript type that best represents the result of a given expression. This inferred type can be extracted with the ``$infer`` type helper.

.. code-block:: typescript

  import e, { type $infer } from "./dbschema/edgeql-js";

  const query = e.select(e.Movie, () => ({ id: true, title: true }));
  type result = $infer<typeof query>;
  // { id: string; title: string }[]

It even infers the cardinality of the query based on things like filtering on exclusive properties and usage of our cardinality assertion functions.

.. code-block:: typescript

  import e, { type $infer } from "./dbschema/edgeql-js";

  const query = e.select(e.Movie, () => ({
    filter_single: { id: "00000000-0000-0000-0000-000000000000" },
    id: true,
    title: true,
  }));
  type result = $infer<typeof query>;
  // { id: string; title: string } | null

Basic usage
===========

Below is a set of examples to get you started with the query builder. It is not intended to be comprehensive, but it should provide a good starting point.

Insert an object
----------------

.. code-block:: typescript

  const query = e.insert(e.Movie, {
    title: 'Doctor Strange 2',
    release_year: 2022
  });

  const result = await query.run(client);
  // { id: string }
  // by default INSERT only returns the id of the new object

See also:
* :ref:`EdgeQL <ref_eql_insert>`

.. _gel-js-qb-transaction:

Transaction
-----------

We can also run the same query as above, build with the query builder, in a transaction.

.. code-block:: typescript

  const query = e.insert(e.Movie, {
    title: 'Doctor Strange 2',
    release_year: 2022
  });

  await client.transaction(async (tx) => {
    const result = await query.run(tx);
    // { id: string }
  });

See also:

* :ref:`EdgeQL <ref_eql_transactions>`

.. _gel-js-parameters:

Parameters
----------

You can pass strongly-typed parameters into your query with ``e.params``.

.. code-block:: typescript

  const helloQuery = e.params({name: e.str}, (params) =>
    e.op('Yer a wizard, ', '++', params.name)
  );
  /*  with name := <str>$name
      select name;
  */


The first argument is an object defining the parameter names and their corresponding types. The second argument is a closure that returns an expression; use the ``params`` argument to construct the rest of your query.

See also:

* :ref:`EdgeQL <ref_eql_params>`

Passing parameter data
^^^^^^^^^^^^^^^^^^^^^^

To execute a query with parameters, pass the data as the second argument to ``.run()``; this argument is *fully typed*!

.. code-block:: typescript

  await helloQuery.run(client, { name: "Harry Styles" })
  // => "Yer a wizard, Harry Styles"

  await helloQuery.run(client, { name: 16 })
  // => TypeError: number is not assignable to string

Top-level usage
^^^^^^^^^^^^^^^

Note that you must call ``.run`` on the result of ``e.params``; in other words, you can only use ``e.params`` at the *top level* of your query, not as an expression inside a larger query.

.. code-block:: typescript

  // ❌ TypeError
  const wrappedQuery = e.select(helloQuery);
  wrappedQuery.run(client, {name: "Harry Styles"});


.. _gel-js-optional-parameters:

Optional parameters
^^^^^^^^^^^^^^^^^^^

A type can be made optional with the ``e.optional`` function.

.. code-block:: typescript

  const query = e.params(
    {
      title: e.str,
      duration: e.optional(e.duration),
    },
    (params) => {
      return e.insert(e.Movie, {
        title: params.title,
        duration: params.duration,
      });
    }
  );

  // works with duration
  const result = await query.run(client, {
    title: "The Eternals",
    duration: Duration.from({hours: 2, minutes: 3})
  });

  // or without duration
  const result = await query.run(client, { title: "The Eternals" });

Complex types
^^^^^^^^^^^^^

In EdgeQL, parameters can only be primitives or arrays of primitives. That's not true with the query builder! Parameter types can be arbitrarily complex. If you need to pass optional data in a nested parameter, you can use ``e.json`` and cast the data to the correct type in the query.

.. code-block:: typescript

  const insertMovie = e.params(
    {
      title: e.str,
      release_year: e.int64,
      actors: e.json,
    },
    (params) =>
      e.insert(e.Movie, {
        title: params.title,
        release_year: params.release_year,
        actors: e.for(e.json_array_unpack(params.actors), (actor) =>
          e.insert(e.Person, {
            name: e.cast(e.str, actor.name),
          })
        ),
      })
  );

  await insertMovie.run(client, {
    title: "Dune",
    release_year: 2021,
    actors: [{ name: "Timmy" }, { name: "JMo" }],
  });

Insert multiple objects
-----------------------

You can iterate over an array of input values to insert multiple objects at once by unpacking an array of named tuples into a set and passing that set to the ``e.for`` function.

.. code-block:: typescript

  const movies = [
    {
      title: "Doctor Strange 2",
      release_year: 2022,
    },
    {
      title: "The Avengers",
      release_year: 2012,
    },
  ];
  const query = e.params(
    {
      movies: e.array(e.tuple({
        title: e.str,
        release_year: e.int64,
      }))
    },
    (params) => e.for(
      e.array_unpack(params.movies),
      (movie) => e.insert(e.Movie, {
        title: movie.title,
        release_year: movie.release_year,
      })
    )
  );

  const result = await query.run(client, { movies });
  // { id: string }[]

Select objects
--------------

.. code-block:: typescript

  const query = e.select(e.Movie, () => ({
    id: true,
    title: true,
  }));

  const result = await query.run(client);
  // { id: string; title: string; }[]

To select all properties of an object, use the spread operator with the special ``*`` property:

.. code-block:: typescript

  const query = e.select(e.Movie, () => ({
    ...e.Movie['*']
  }));

  const result = await query.run(client);
  /*
    {
      id: string;
      title: string;
      release_year: number | null;  # optional property
    }[]
  */

Nested shapes
-------------

.. code-block:: typescript

  const query = e.select(e.Movie, () => ({
    id: true,
    title: true,
    actors: {
      name: true,
    }
  }));

  const result = await query.run(client);
  /*
    {
      id: string;
      title: string;
      actors: { name: string; }[];
    }[]
  */

If you need to create computed properties on the nested object, you can pass a closure to the nested object.

.. code-block:: typescript

  const query = e.select(e.Movie, () => ({
    id: true,
    title: true,
    actors: (a) => ({
      id: true,
      name: true,
      lower_name: e.str_lower(a.name),
      upper_name: e.str_upper(a.name),
    }),
  }));

  const result = await query.run(client);
  /*
    {
      id: string;
      title: string;
      actors: {
        id: string;
        name: string;
        lower_name: string;
        upper_name: string;
      }[];
    }[]
  */

Filtering
---------

Pass a boolean expression as the special key ``filter`` to filter the results. You can even filter nested objects.

.. code-block:: typescript

  const query = e.select(e.Movie, (movie) => ({
    // special "filter" key
    filter: e.op(movie.release_year, ">", 1999),

    id: true,
    title: true,
    actors: (a) => ({
      // nested filter
      filter: e.op(a.name, "ilike", "a%"),
      name: true,
      id: true,
    }),
  }));

  const result = await query.run(client);
  // { id: string; title: number }[]

Since ``filter`` is a reserved keyword in EdgeQL, the special ``filter`` key can live alongside your property keys without a risk of collision.

.. note::

  The ``e.op`` function is used to express EdgeQL operators. It is documented in more detail below and on the :ref:`Functions and operators <gel-js-funcops>` page.

Select a single object
----------------------

To select a particular object, use the ``filter_single`` key and filter on an exclusive property. This tells the query builder to expect a singleton result.

.. code-block:: typescript

  const query = e.select(e.Movie, (movie) => ({
    id: true,
    title: true,
    release_year: true,

    filter_single: e.op(
      movie.id,
      "=",
      e.uuid("2053a8b4-49b1-437a-84c8-e1b0291ccd9f")
    ),
  }));

  const result = await query.run(client);
  // { id: string; title: string; release_year: number | null }

For convenience ``filter_single`` also supports a simplified syntax that eliminates the need for ``e.op`` when used on exclusive properties:

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    id: true,
    title: true,
    release_year: true,

    filter_single: { id: "2053a8b4-49b1-437a-84c8-e1b0291ccd9f" },
  }));

This also works if an object type has a composite exclusive constraint. Each property in the object will be combined with an ``and`` to form the final filter expression that matches the composite exclusive constraint.

.. code-block:: typescript

  /*
    type Movie {
      ...
      constraint exclusive on (.title, .release_year);
    }
  */

  e.select(e.Movie, (movie) => ({
    title: true,
    filter_single: {
      title: "The Avengers",
      release_year: 2012
    },
  }));


Ordering and pagination
-----------------------

The special keys ``order_by``, ``limit``, and ``offset`` correspond to equivalent EdgeQL clauses.

.. code-block:: typescript

  const query = e.select(e.Movie, (movie) => ({
    id: true,
    title: true,

    order_by: movie.title,
    limit: 10,
    offset: 10
  }));

  const result = await query.run(client);
  // { id: true; title: true }[]

Operators and functions
-----------------------

Note that the filter expression above uses ``e.op`` function, which is how to
use *operators* like ``=``, ``>=``, ``++``, and ``and``.

.. code-block:: typescript

  // prefix (unary) operators
  e.op("not", e.bool(true));      // not true
  e.op("exists", e.set("hi"));    // exists {"hi"}

  // infix (binary) operators
  e.op(e.int64(2), "+", e.int64(2)); // 2 + 2
  e.op(e.str("Hello "), "++", e.str("World!")); // "Hello " ++ "World!"

  // ternary operator (if/else)
  e.op(e.str("😄"), "if", e.bool(true), "else", e.str("😢"));
  // "😄" if true else "😢"

Functions are also available as functions on the ``e`` object.

.. code-block:: typescript

  e.datetime_of_statement();
  e.sum(e.set(e.int64(1), e.int64(2), e.int64(3)));
  e.assert_single(e.select(/* some query */));


Update objects
--------------

.. code-block:: typescript

  const query = e.update(e.Movie, (movie) => ({
    filter_single: { title: "Doctor Strange 2" },
    set: {
      title: "Doctor Strange in the Multiverse of Madness",
    },
  }));

  const result = await query.run(client);

Delete objects
--------------

.. code-block:: typescript

  const query = e.delete(e.Movie, (movie) => ({
    filter: e.op(movie.title, 'ilike', "the avengers%"),
  }));

  const result = await query.run(client);
  // { id: string }[]

Delete multiple objects using an array of properties:

.. code-block:: typescript

  const titles = ["The Avengers", "Doctor Strange 2"];
  const query = e.delete(e.Movie, (movie) => ({
    filter: e.op(
      movie.title,
      "in",
      e.array_unpack(e.literal(e.array(e.str), titles))
    )
  }));
  const result = await query.run(client);
  // { id: string }[]

Note that we have to use ``array_unpack`` to cast our ``array<str>`` into a ``set<str>`` since the ``in`` operator works on sets. And we use ``literal`` to create a custom literal since we're inlining the titles array into our query.

Typically you'll want to pass data into a query using params. Here's an example of how to do this with params:

.. code-block:: typescript

  const titles = ["The Avengers", "Doctor Strange 2"];
  const query = e.params(
    { titles: e.array(e.str) },
    (params) => e.delete(e.Movie, (movie) => ({
      filter: e.op(movie.title, "in", e.array_unpack(params.titles)),
    }))
  );

  const result = await query.run(client, { titles });
  // { id: string }[]

Compose queries
---------------

All query expressions are fully composable; this is one of the major differentiators between this query builder and a typical ORM. For instance, we can ``select`` an ``insert`` query in order to fetch properties of the object we just inserted.


.. code-block:: typescript

  const newMovie = e.insert(e.Movie, {
    title: "Iron Man",
    release_year: 2008
  });

  const query = e.select(newMovie, () => ({
    title: true,
    release_year: true,
    num_actors: e.count(newMovie.actors)
  }));

  const result = await query.run(client);
  // { title: string; release_year: number; num_actors: number }

Or we can use subqueries inside mutations.

.. code-block:: typescript

  // select Doctor Strange
  const drStrange = e.select(e.Movie, (movie) => ({
    filter_single: { title: "Doctor Strange" }
  }));

  // select actors
  const actors = e.select(e.Person, (person) => ({
    filter: e.op(
      person.name,
      "in",
      e.set("Benedict Cumberbatch", "Rachel McAdams")
    )
  }));

  // add actors to cast of drStrange
  const query = e.update(drStrange, () => ({
    actors: { "+=": actors }
  }));

  const result = await query.run(client);


.. _ref_geljs_globals:

Globals
-------

Reference global variables.

.. code-block:: typescript

  e.global.user_id;
  e.default.global.user_id;  // same as above
  e.my_module.global.some_value;

Other modules
-------------

Reference entities in modules other than ``default``.

The ``Vampire`` type in a module named ``characters``:

.. code-block:: typescript

  e.characters.Vampire;

As shown in "Globals," a global ``some_value`` in a module ``my_module``:

.. code-block:: typescript

  e.my_module.global.some_value;

Advanced usage
==============

e.for vs JS for or .forEach
---------------------------

You may be tempted to use JavaScript's ``for`` or the JavaScript array's ``.forEach`` method to avoid having to massage your data into a set for consumption by ``e.for``. This approach comes at a cost of performance.

If you use ``for`` or ``.forEach`` to iterate over a standard JavaScript data structure and run separate queries for each item in your iterable, you're doing just that: running separate queries for each item in your iterable. By iterating inside your query using ``e.for``, you're guaranteed everything will happen in a single query.

In addition to the performance implications, a single query means that either everything succeeds or everything fails. You will never end up with only some of your data inserted. This ensures your data integrity is maintained. You could achieve this yourself by wrapping your batch queries with :ref:`a transaction <gel-js-qb-transaction>`, but a single query is already atomic without any additional work on your part.

Using ``e.for`` to run a single query is generally the best approach. When dealing with extremely large datasets, you can define the query once, chunk the data, and run the query in batches.

.. _gel-js-for-bulk-inserts:

Bulk inserts
------------

It's common to use ``for`` expressions to perform bulk inserts. In this example, the raw data is passed in as a ``json`` parameter, converted to a set of ``json`` objects with ``json_array_unpack``, then passed into a ``for`` expression for insertion.

.. code-block:: typescript

  const query = e.params(
    { items: e.json },
    (params) => e.for(
      e.json_array_unpack(params.items),
      (item) => e.insert(e.Movie, {
        title: e.cast(e.str, item.title),
        release_year: e.cast(e.int64, item.release_year),
      })
    )
  );

  const result = await query.run(client, {
    items: [
      { title: "Deadpool", release_year: 2016 },
      { title: "Deadpool 2", release_year: 2018 },
      { title: "Deadpool 3", release_year: 2024 },
      { title: "Deadpool 4", release_year: null },
    ],
  });

Note that any optional properties values must be explicitly set to ``null``.  They cannot be set to ``undefined`` or omitted; doing so will cause a runtime error.

.. _gel-js-for-bulk-inserts-conflicts:

Handling conflicts in bulk inserts
----------------------------------

Here's a more complex example, demonstrating how to complete a nested insert with conflicts on the inner items. First, let's recall that the ``Movie`` type's ``title`` property has an exclusive constraint.

Here's the data we want to bulk insert:

.. code-block:: javascript

    [
      {
        portrayed_by: "Robert Downey Jr.",
        name: "Iron Man",
        movies: ["Iron Man", "Iron Man 2", "Iron Man 3"]
      },
      {
        portrayed_by: "Chris Evans",
        name: "Captain America",
        movies: [
          "Captain America: The First Avenger",
          "The Avengers",
          "Captain America: The Winter Soldier",
        ]
      },
      {
        portrayed_by: "Mark Ruffalo",
        name: "The Hulk",
        movies: ["The Avengers", "Iron Man 3", "Avengers: Age of Ultron"]
      }
    ]

This is potentially a problem because some of the characters appear in the same movies. We can't just naively insert all the movies because we'll eventually hit a conflict. Since we're going to write this as a single query, chaining ``.unlessConflict`` on our query won't help. It only handles conflicts with objects that existed *before* the current query.

Let's look at a query that can accomplish this insert, and then we'll break it down.

.. code-block:: typescript

  const query = e.params(
    {
      characters: e.array(
        e.tuple({
          portrayed_by: e.str,
          name: e.str,
          movies: e.array(e.str),
        }),
      ),
    },
    (params) => {
      const movies = e.for(
        e.op(
          "distinct",
          e.array_unpack(e.array_unpack(params.characters).movies),
        ),
        (movieTitle) =>
          e.insert(e.Movie, { title: movieTitle }).unlessConflict((movie) => ({
            on: movie.title,
            else: movie,
          })),
      );
      return e.with(
        [movies],
        e.for(e.array_unpack(params.characters), (character) =>
          e.insert(e.Character, {
            name: character.name,
            portrayed_by: character.portrayed_by,
            movies: e.assert_distinct(
              e.select(movies, (movie) => ({
                filter: e.op(movie.title, "in", e.array_unpack(character.movies)),
              })),
            ),
          }),
        ),
      );
    },
  );


.. _gel-js-for-bulk-inserts-conflicts-params:

Structured params
^^^^^^^^^^^^^^^^^

.. code-block:: typescript

  const query = e.params(
    {
      characters: e.array(
        e.tuple({
          portrayed_by: e.str,
          name: e.str,
          movies: e.array(e.str),
        }),
      ),
    },
    (params) => { ...

In raw EdgeQL, you can only have scalar types as parameters. We could mirror that here with something like this: ``e.params({characters: e.json})``, but this would then require us to cast all the values inside the JSON like ``portrayed_by`` and ``name``.

By doing it this way — typing ``characters`` with ``e.array`` and the character objects as named tuples by passing an object to ``e.tuple`` — all the data in the array will be properly cast for us. It will also better type check the data you pass to the query's ``run`` method. The restriction here is that the data must be non-optional, since tuples cannot contain optional values.

.. _gel-js-for-bulk-inserts-conflicting-data:

Inserting the inner conflicting data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: typescript

  ...
    (params) => {
      const movies = e.for(
        e.op(
          "distinct",
          e.array_unpack(e.array_unpack(params.characters).movies),
        ),
        (movieTitle) =>
          e.insert(e.Movie, { title: movieTitle }).unlessConflict((movie) => ({
            on: movie.title,
            else: movie,
          })),
      );
  ...

We need to separate this movie insert query so that we can use ``distinct`` on it. We could just nest an insert inside our character insert if movies weren't duplicated across characters (e.g., two characters have "The Avengers" in ``movies``). Even though the query is separated from the character inserts here, it will still be built as part of a single EdgeQL query using ``with`` which we'll get to a bit later.

The ``distinct`` operator can only operate on sets. We use ``array_unpack`` to make these arrays into sets. We need to call it twice because ``params.characters`` is an array and ``.movies`` is an array nested inside each character.

Chaining ``unlessConflict`` takes care of any movies that already exist in the database *before* we run this query, but it won't handle conflicts that come about over the course of this query. The ``distinct`` operator we used earlier pro-actively eliminates any conflicts we might have had among this data.

.. _gel-js-for-bulk-inserts-outer-data:

Inserting the outer data
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: typescript

  ...
      return e.with(
        [movies],
        e.for(e.array_unpack(params.characters), (character) =>
          e.insert(e.Character, {
            name: character.name,
            portrayed_by: character.portrayed_by,
            movies: e.assert_distinct(
              e.select(movies, (movie) => ({
                filter: e.op(movie.title, "in", e.array_unpack(character.movies)),
              })),
            ),
          }),
        ),
      );
    },
  );
  ...

The query builder will try to automatically use EdgeQL's ``with``, but in this instance, it doesn't know where to place the ``with``. By using ``e.with`` explicitly, we break our movie insert out to the top-level of the query. By default, it would be scoped *inside* the query, so our ``distinct`` operator would be applied only to each character's movies instead of to all of the movies. This would have caused the query to fail.

The rest of the query is relatively straightforward. We unpack ``params.characters`` to a set so that we can pass it to ``e.for`` to iterate over the characters. For each character, we build an ``insert`` query with their ``name`` and ``portrayed_by`` values.

For the character's ``movies``, we ``select`` everything in the ``movies`` insert query we wrote previously, filtering for those with titles that match values in the ``character.movies`` array.

All that's left is to run the query, passing the data to the query's ``run`` method!

.. _gel-js-for-bulk-updates:

Bulk updates
------------

Just like with inserts, you can run bulk updates using a ``for`` loop. Pass in your data, iterate over it, and build an ``update`` query for each item.

In this example, we use ``name`` to filter for the character to be updated since ``name`` has an exclusive constraint in the schema (meaning a given name will correspond to, at most, a single object). That filtering is done using the ``filter_single`` property of the object returned from your ``update`` callback. Then the ``last_appeared`` value is updated by including it in the nested ``set`` object.

.. code-block:: typescript

  const query = e.params(
    {
      characters: e.array(
        e.tuple({
          name: e.str,
          last_appeared: e.int64,
        }),
      ),
    },
    (params) =>
      e.for(e.array_unpack(params.characters), (character) =>
        e.update(e.Character, () => ({
          filter_single: { name: character.name },
          set: {
            last_appeared: character.last_appeared,
          },
        })),
      ),
  );

  await query.run(client, {
    characters: [
      { name: "Iron Man", last_appeared: 2019 },
      { name: "Captain America", last_appeared: 2019 },
      { name: "The Hulk", last_appeared: 2021 },
    ],
  });

API Reference
=============

.. _gel-js-types-and-casting:
.. _gel-js-literals:

Types and Literals
------------------

The query builder provides a set of "helper functions" that convert JavaScript literals into *expressions* that can be used in queries. For the most part, these helper functions correspond to the *name* of the type.

Primitives
^^^^^^^^^^

Primitive literal expressions are created using constructor functions that correspond to Gel datatypes. Each expression below is accompanied by the EdgeQL it produces.

.. code-block:: typescript

  e.str("asdf")            // "asdf"
  e.int64(123)             // 123
  e.float64(123.456)       // 123.456
  e.bool(true)             // true
  e.bigint(12345n)         // 12345n
  e.decimal("1234.1234n")  // 1234.1234n
  e.uuid("599236a4...")    // <uuid>"599236a4..."

  e.bytes(Uint8Array.from('binary data'));
  // b'binary data'

.. _ref_qb_casting:

Casting
^^^^^^^

These types can be used to *cast* one expression to another type.

.. code-block:: typescript

  e.cast(e.json, e.int64('123'));
  // <json>'123'

  e.cast(e.duration, e.str('127 hours'));
  // <duration>'127 hours'

.. note::

  Scalar types like ``e.str`` serve a dual purpose. They can be used as functions to instantiate literals (``e.str("hi")``) or used as variables (``e.cast(e.str, e.int64(123))``).

Strings
^^^^^^^

String expressions have some special functionality: they support indexing and slicing, as in EdgeQL.

.. code-block:: typescript

  const myString = e.str("hello world");

  myString[5];         //  "hello world"[5]
  myString['2:5'];     //  "hello world"[2:5]
  myString[':5'];      //  "hello world"[:5]
  myString['2:'];      //  "hello world"[2:]

There are also equivalent ``.index`` and ``.slice`` methods that can accept integer expressions as arguments.

.. code-block:: typescript

  const myString = e.str("hello world");
  const start = e.int64(2);
  const end = e.int64(5);

  myString.index(start);          //  "hello world"[2]
  myString.slice(start, end);     //  "hello world"[2:5]
  myString.slice(null, end);      //  "hello world"[:5]
  myString.slice(start, null);    //  "hello world"[2:]

Enums
^^^^^

Enum literals are available as properties defined on the enum type.

.. code-block:: typescript

  e.Colors.green;
  // Colors.green;

  e.sys.VersionStage.beta;
  // sys::VersionStage.beta

Dates and times
^^^^^^^^^^^^^^^

To create an instance of ``datetime``, pass a JavaScript ``Date`` object into ``e.datetime``:

.. code-block:: typescript

  e.datetime(new Date('1999-01-01'));
  // <datetime>'1999-01-01T00:00:00.000Z'

Gel's other temporal datatypes don't have equivalents in the JavaScript type system: ``duration``, ``cal::relative_duration``, ``cal::date_duration``, ``cal::local_date``, ``cal::local_time``, and ``cal::local_datetime``.

To resolve this, each of these datatypes can be represented with an instance of a corresponding class, as defined in ``gel`` module. Clients use these classes to represent these values in query results; they are documented on the :ref:`Client API <gel-js-datatypes>` docs.

.. list-table::

  * - ``e.duration``
    - :js:class:`Duration`
  * - ``e.cal.relative_duration``
    - :js:class:`RelativeDuration`
  * - ``e.cal.date_duration``
    - :js:class:`DateDuration`
  * - ``e.cal.local_date``
    - :js:class:`LocalDate`
  * - ``e.cal.local_time``
    - :js:class:`LocalTime`
  * - ``e.cal.local_datetime``
    - :js:class:`LocalDateTime`
  * - ``e.cal.local_datetime``
    - :js:class:`LocalDateTime`
  * - ``e.cal.local_datetime``
    - :js:class:`LocalDateTime`

The code below demonstrates how to declare each kind of temporal literal, along with the equivalent EdgeQL.

.. code-block:: typescript

  import * as gel from "gel";

  const myDuration = new gel.Duration(0, 0, 0, 0, 1, 2, 3);
  e.duration(myDuration);

  const myLocalDate = new gel.LocalDate(1776, 7, 4);
  e.cal.local_date(myLocalDate);

  const myLocalTime = new gel.LocalTime(13, 15, 0);
  e.cal.local_time(myLocalTime);

  const myLocalDateTime = new gel.LocalDateTime(1776, 7, 4, 13, 15, 0);
  e.cal.local_datetime(myLocalDateTime);


You can also declare these literals by casting an appropriately formatted ``str`` expression, as in EdgeQL. Casting :ref:`is documented <ref_qb_casting>` in more detail later in the docs.

.. code-block:: typescript

  e.cast(e.duration, e.str('5 minutes'));
  // <std::duration>'5 minutes'

  e.cast(e.cal.local_datetime, e.str('1999-03-31T15:17:00'));
  // <cal::local_datetime>'1999-03-31T15:17:00'

  e.cast(e.cal.local_date, e.str('1999-03-31'));
  // <cal::local_date>'1999-03-31'

  e.cast(e.cal.local_time, e.str('15:17:00'));
  // <cal::local_time>'15:17:00'


JSON
^^^^

JSON literals are created with the ``e.json`` function. You can pass in any Gel-compatible data structure.

.. note::

  What does "Gel-compatible" mean? It means any JavaScript data structure with an equivalent in Gel: strings, number, booleans, ``bigint``\ s, ``Uint8Array``\ s, ``Date``\ s, and instances of Gel's built-in classes: (``LocalDate`` ``LocalTime``, ``LocalDateTime``, ``DateDuration``, ``Duration``, and ``RelativeDuration``), and any array or object of these types. Other JavaScript data structures like symbols, instances of custom classes, sets, maps, and `typed arrays <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Typed_arrays>`_ are not supported.

.. code-block:: typescript

  const query = e.json({ name: "Billie" })
  // to_json('{"name": "Billie"}')

  const data = e.json({
    name: "Billie",
    numbers: [1,2,3],
    nested: { foo: "bar"},
    duration: new gel.Duration(1, 3, 3)
  })

JSON expressions support indexing, as in EdgeQL. The returned expression also has a ``json`` type.

.. code-block:: typescript

  const query = e.json({ numbers: [0,1,2] });

  query.toEdgeQL(); // to_json((numbers := [0,1,2]))

  query.numbers[0].toEdgeQL();
  // to_json('{"numbers":[0,1,2]}')['numbers'][0]

The inferred type associated with a ``json`` expression is ``unknown``.

.. code-block:: typescript

  const result = await query.run(client)
  // unknown

Arrays
^^^^^^

Declare array expressions by passing an array of expressions into ``e.array``.

.. code-block:: typescript

  e.array([e.str("a"), e.str("b"), e.str("b")]);
  // ["a", "b", "c"]

EdgeQL semantics are enforced by TypeScript, so arrays can't contain elements with incompatible types.

.. code-block:: typescript

  e.array([e.int64(5), e.str("foo")]);
  // TypeError!

For convenience, the ``e.array`` can also accept arrays of plain JavaScript data as well.

.. code-block:: typescript

  e.array(['a', 'b', 'c']);
  // ['a', 'b', 'c']

  // you can intermixing expressions and plain data
  e.array([1, 2, e.int64(3)]);
  // [1, 2, 3]

Array expressions also support indexing and slicing operations.

.. code-block:: typescript

  const myArray = e.array(['a', 'b', 'c', 'd', 'e']);
  // ['a', 'b', 'c', 'd', 'e']

  myArray[1];
  // ['a', 'b', 'c', 'd', 'e'][1]

  myArray['1:3'];
  // ['a', 'b', 'c', 'd', 'e'][1:3]

There are also equivalent ``.index`` and ``.slice`` methods that can accept other expressions as arguments.

.. code-block:: typescript

  const start = e.int64(1);
  const end = e.int64(3);

  myArray.index(start);
  // ['a', 'b', 'c', 'd', 'e'][1]

  myArray.slice(start, end);
  // ['a', 'b', 'c', 'd', 'e'][1:3]

Tuples
^^^^^^

Declare tuples with ``e.tuple``. Pass in an array to declare a "regular" (unnamed) tuple; pass in an object to declare a named tuple.

.. code-block:: typescript

  e.tuple([e.str("Peter Parker"), e.int64(18)]);
  // ("Peter Parker", 18)

  e.tuple({
    name: e.str("Peter Parker"),
    age: e.int64(18)
  });
  // (name := "Peter Parker", age := 18)

Tuple expressions support indexing.

.. code-block:: typescript

  // Unnamed tuples
  const spidey = e.tuple([
    e.str("Peter Parker"),
    e.int64(18)
  ]);
  spidey[0];                 // => ("Peter Parker", 18)[0]

  // Named tuples
  const spidey = e.tuple({
    name: e.str("Peter Parker"),
    age: e.int64(18)
  });
  spidey.name;
  // (name := "Peter Parker", age := 18).name

Set literals
^^^^^^^^^^^^

Declare sets with ``e.set``.

.. code-block:: typescript

  e.set(e.str("asdf"), e.str("qwer"));
  // {'asdf', 'qwer'}

As in EdgeQL, sets can't contain elements with incompatible types. These
semantics are enforced by TypeScript.

.. code-block:: typescript

  e.set(e.int64(1234), e.str('sup'));
  // TypeError

Empty sets
^^^^^^^^^^

To declare an empty set, cast an empty set to the desired type. As in EdgeQL, empty sets are not allowed without a cast.

.. code-block:: typescript

  e.cast(e.int64, e.set());
  // <std::int64>{}


Range literals
^^^^^^^^^^^^^^

As in EdgeQL, declare range literals with the built-in ``range`` function.

.. code-block:: typescript

  const myRange = e.range(0, 8);

  myRange.toEdgeQL();
  // => std::range(0, 8);

Ranges can be created for all numerical types, as well as ``datetime``, ``local_datetime``, and ``local_date``.

.. code-block:: typescript

  e.range(e.decimal('100'), e.decimal('200'));
  e.range(Date.parse("1970-01-01"), Date.parse("2022-01-01"));
  e.range(new LocalDate(1970, 1, 1), new LocalDate(2022, 1, 1));

Supply named parameters as the first argument.

.. code-block:: typescript

  e.range({inc_lower: true, inc_upper: true, empty: true}, 0, 8);
  // => std::range(0, 8, true, true);

JavaScript doesn't have a native way to represent range values. Any range value returned from a query will be encoded as an instance of the :js:class:`Range` class, which is exported from the ``gel`` package.

.. code-block:: typescript

  const query = e.range(0, 8);
  const result = await query.run(client);
  // => Range<number>;

  console.log(result.lower);       // 0
  console.log(result.upper);       // 8
  console.log(result.isEmpty);     // false
  console.log(result.incLower);    // true
  console.log(result.incUpper);    // false

Custom literals
^^^^^^^^^^^^^^^

You can use ``e.literal`` to create literals corresponding to collection types like tuples, arrays, and primitives. The first argument expects a type, the second expects a *value* of that type.

.. code-block:: typescript

  e.literal(e.str, "sup");
  // equivalent to: e.str("sup")

  e.literal(e.array(e.int16), [1, 2, 3]);
  // <array<int16>>[1, 2, 3]

  e.literal(e.tuple([e.str, e.int64]), ['baz', 9000]);
  // <tuple<str, int64>>("Goku", 9000)

  e.literal(
    e.tuple({name: e.str, power_level: e.int64}),
    {name: 'Goku', power_level: 9000}
  );
  // <tuple<name: str, power_level: bool>>("asdf", false)

.. _gel-js-funcops:

Functions and Operators
-----------------------

The Gel :ref:`standard library <ref_std>` contains many functions and operators that you will use in your queries.

Function syntax
^^^^^^^^^^^^^^^

All built-in standard library functions are reflected as functions in ``e``.

.. code-block:: typescript

  e.str_upper(e.str("hello"));
  // str_upper("hello")

  e.op(e.int64(2), '+', e.int64(2));
  // 2 + 2

  const nums = e.set(e.int64(3), e.int64(5), e.int64(7))
  e.op(e.int64(4), 'in', nums);
  // 4 in {3, 5, 7}

  e.math.mean(nums);
  // math::mean({3, 5, 7})


.. _gel-js-funcops-prefix:

Prefix operators
^^^^^^^^^^^^^^^^

Unlike functions, operators do *not* correspond to a top-level function on the ``e`` object. Instead, they are expressed with the ``e.op`` function.

Prefix operators operate on a single argument: ``OPERATOR <arg>``.

.. code-block:: typescript

  e.op('not', e.bool(true));      // not true
  e.op('exists', e.set('hi'));    // exists {'hi'}
  e.op('distinct', e.set('hi', 'hi'));    // distinct {'hi', 'hi'}

.. list-table::

  * - ``"exists"`` ``"distinct"`` ``"not"``


.. _gel-js-funcops-infix:

Infix operators
^^^^^^^^^^^^^^^

Infix operators operate on two arguments: ``<arg> OPERATOR <arg>``.

.. code-block:: typescript

  e.op(e.str('Hello '), '++', e.str('World!'));
  // 'Hello ' ++ 'World!'

.. list-table::

  * - ``"="`` ``"?="`` ``"!="`` ``"?!="`` ``">="`` ``">"`` ``"<="`` ``"<"``
      ``"or"`` ``"and"`` ``"+"`` ``"-"`` ``"*"`` ``"/"`` ``"//"`` ``"%"``
      ``"^"`` ``"in"`` ``"not in"`` ``"union"`` ``"??"`` ``"++"`` ``"like"``
      ``"ilike"`` ``"not like"`` ``"not ilike"``


.. _gel-js-funcops-ternary:

Ternary operators
^^^^^^^^^^^^^^^^^

Ternary operators operate on three arguments.

.. code-block:: typescript

  e.op(e.str('😄'), 'if', e.bool(true), 'else', e.str('😢'));
  // 😄 if true else 😢

  e.op("if", e.bool(true), "then", e.str('😄'), "else", e.str('😢'));
  // if true then 😄 else 😢

.. _gel-js-select:

Select
------

The full power of the EdgeQL ``select`` statement is available as a top-level ``e.select`` function.

Scalars
^^^^^^^

Any scalar expression be passed into ``e.select``, though it's often unnecessary, since expressions are ``run``\ able without being wrapped by ``e.select``.

.. code-block:: typescript

  e.select(e.str('Hello world'));
  // select 1234;

  e.select(e.op(e.int64(2), '+', e.int64(2)));
  // select 2 + 2;


Objects
^^^^^^^

As in EdgeQL, selecting an set of objects will return their ``id`` property only. This is reflected in the TypeScript type of the result.

.. code-block:: typescript

  const query = e.select(e.Movie);
  // select Movie;

  const result = await query.run(client);
  // {id:string}[]

Shapes
^^^^^^

To specify a shape, pass a function as the second argument. This function should return an object that specifies which properties to include in the result. This roughly corresponds to a *shape* in EdgeQL.

.. code-block:: typescript

  const query = e.select(e.Movie, () => ({
    id: true,
    title: true,
    release_year: true,
  }));
  /*
    EdgeQL:
    select Movie {
      id,
      title,
      release_year
    }
  */
  /*
    Inferred type:
    {
      id: string;
      title: string;
      release_year: number | null;
    }[]
  */

As you can see, the type of ``release_year`` is ``number | null`` since it's an optional property, whereas ``id`` and ``title`` are required.

Passing a ``boolean`` value (as opposed to a ``true`` literal), which will make the property optional. Passing ``false`` will exclude that property which is generally used to exclude properties when using the special ``*`` property.

.. code-block:: typescript

  e.select(e.Movie, () => ({
    id: true,
    title: Math.random() > 0.5,
    release_year: false,
  }));

  const result = await query.run(client);
  // { id: string; title: string | undefined; }[]

Selecting all properties
************************

For convenience, the query builder provides a shorthand for selecting all properties of a given object.

.. code-block:: typescript

  e.select(e.Movie, movie => ({
    ...e.Movie['*']
  }));

  const result = await query.run(client);
  // { id: string; title: string; release_year: number | null }[]

This ``*`` property is just a strongly-typed, plain object:

.. code-block:: typescript

  e.Movie['*'];
  // => { id: true, title: true, release_year: true }

Select a single object
^^^^^^^^^^^^^^^^^^^^^^

To select a particular object, use the ``filter_single`` key. This tells the query builder to expect a result with zero or one elements.

.. code-block:: typescript

  e.select(e.Movie, () => ({
    id: true,
    title: true,
    release_year: true,

    filter_single: { id: "00000000-0000-0000-0000-000000000000" },
  }));

This also works if an object type has a composite exclusive constraint:

.. code-block:: typescript

  /*
    type Movie {
      ...
      constraint exclusive on (.title, .release_year);
    }
  */

  e.select(e.Movie, () => ({
    title: true,
    filter_single: { title: "The Avengers", release_year: 2012 },
  }));

You can also pass a boolean expression like from ``e.op`` or a function in the standard library to ``filter_single`` if you prefer.

.. code-block:: typescript

  const query = e.select(e.Movie, (movie) => ({
    id: true,
    title: true,
    release_year: true,
    filter_single: e.op(
      movie.id,
      "=",
      e.uuid("00000000-0000-0000-0000-000000000000"),
    ),
  }));

  const result = await query.run(client);
  // { id: string; title: string; release_year: number | null } | null

Notice that we must explicitly cast the string literal to a ``uuid`` expression using the ``e.uuid`` function. We can also use ``e.params`` to explicitly pass in the ``id`` as a parameter, which will make the query more reusable and also not require the explicit cast.

.. code-block:: typescript

  const id = "00000000-0000-0000-0000-000000000000";
  const query = e.params(
    { id: e.uuid },
    (params) => e.select(e.Movie, (movie) => ({
      id: true,
      title: true,
      release_year: true,
      filter_single: e.op(movie.id, "=", params.id),
    }))
  );

  const result = await query.run(client, { id });
  // { id: string; title: string; release_year: number | null } | null

Select many objects by ID
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: typescript

  const query = e.params(
    { ids: e.array(e.uuid) },
    (params) =>
      e.select(e.Movie, (movie) => ({
        id: true,
        title: true,
        release_year: true,
        filter: e.op(movie.id, "in", e.array_unpack(params.ids)),
      }))
  );

  const result = await query.run(client, {
    ids: [
      "00000000-0000-0000-0000-000000000000",
      "00000000-0000-0000-0000-000000000000",
    ],
  })
  // {id: string; title: string; release_year: number | null}[]

Nesting shapes
^^^^^^^^^^^^^^

As in EdgeQL, shapes can be nested to fetch deeply related objects.

.. code-block:: typescript

  const query = e.select(e.Movie, () => ({
    id: true,
    title: true,
    actors: {
      name: true
    }
  }));

  const result = await query.run(client);
  /* {
    id: string;
    title: string;
    actors: { name: string }[]
  }[] */


Portable shapes
^^^^^^^^^^^^^^^

You can use ``e.shape`` to define a "portable shape" that can be defined independently and used in multiple queries. The result of ``e.shape`` is a *function*. When you use the shape in your final queries, be sure to pass in the *scope variable* (e.g. ``movie`` in the example below). This is required for the query builder to correctly resolve the query.

You can also use the ``$infer`` type helper to extract the inferred type of the portable shape. Note that the cardinality of the shape will affect the inferred type, just like an ``e.select`` expression, so if you are trying to get to the element type, you will need to use TypeScript to get the correct type based on the cardinality of the shape.

.. code-block:: typescript

  const baseShape = e.shape(e.Movie, (movie) => ({
    title: true,
    num_actors: e.count(movie.actors),
  }));

  type MovieShape = $infer<typeof baseShape>;
  // { title: true; num_actors: true }[]
  type MovieShapeSingle = MovieShape[number];
  // { title: true; num_actors: true }

  const query = e.select(e.Movie, (movie) => ({
    ...baseShape(movie),
    release_year: true,
    filter_single: {title: 'The Avengers'}
  }))

  type QueryResult = $infer<typeof query>;
  // { title: string; num_actors: number; release_year: number | null } | null

Why closures?
^^^^^^^^^^^^^

In EdgeQL, a ``select`` statement introduces a new *scope*; within the clauses of a select statement, you can refer to fields of the *elements being selected* using leading dot notation.

.. code-block:: edgeql

  select Movie { id, title }
  filter .title = "The Avengers";

Here, ``.title`` is shorthand for the ``title`` property of the selected ``Movie`` elements. All properties/links on the ``Movie`` type can be referenced using this shorthand anywhere in the ``select`` expression. In other words, the ``select`` expression is *scoped* to the ``Movie`` type.

To represent this scoping in the query builder, we use function scoping. This is a powerful pattern that makes it painless to represent filters, ordering, computed fields, and other expressions. Let's see it in action.


Filtering
^^^^^^^^^

To add a filtering clause, just include a ``filter`` key in the returned
params object. This should correspond to a boolean expression.

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    id: true,
    title: true,
    filter: e.op(movie.title, "ilike", "The Matrix%")
  }));
  /*
    select Movie {
      id,
      title
    } filter .title ilike "The Matrix%"
  */

.. note::

  Since ``filter`` is a :ref:`reserved keyword <ref_eql_lexical_names>` in |Gel|, there is minimal danger of conflicting with a property or link named ``filter``. All shapes can contain filter clauses, even nested ones.

If you have many conditions you want to test for, your filter can start to get difficult to read.

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    id: true,
    title: true,
    filter: e.op(
      e.op(
        e.op(movie.title, "ilike", "The Matrix%"),
        "and",
        e.op(movie.release_year, "=", 1999)
      ),
      "or",
      e.op(movie.title, "=", "Iron Man")
    )
  }));

To improve readability, we recommend breaking these operations out into named variables and composing them.

.. code-block:: typescript

  e.select(e.Movie, (movie) => {
    const isAMatrixMovie = e.op(movie.title, "ilike", "The Matrix%");
    const wasReleased1999 = e.op(movie.release_year, "=", 1999);
    const isIronMan = e.op(movie.title, "=", "Iron Man");
    return {
      id: true,
      title: true,
      filter: e.op(
        e.op(
          isAMatrixMovie,
          "and",
          wasReleased1999
        ),
        "or",
        isIronMan
      )
    }
  });

You can combine compound conditions as much or as little as makes sense for
your application.

.. code-block:: typescript

  e.select(e.Movie, (movie) => {
    const isAMatrixMovie = e.op(movie.title, "ilike", "The Matrix%");
    const wasReleased1999 = e.op(movie.release_year, "=", 1999);
    const isAMatrixMovieReleased1999 = e.op(
      isAMatrixMovie,
      "and",
      wasReleased1999
    );
    const isIronMan = e.op(movie.title, "=", "Iron Man");
    return {
      id: true,
      title: true,
      filter: e.op(
        isAMatrixMovieReleased1999,
        "or",
        isIronMan
      )
    }
  });

Filters on links
^^^^^^^^^^^^^^^^

Links can be filtered using traditional filters.

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    title: true,
    actors: (actor) => ({
      name: true,
      filter: e.op(actor.name.slice(0, 1), "=", "A"),
    }),
    filter_single: { title: "Iron Man" },
  }));


You can also use the :ref:`type intersection <gel-js-objects-type-intersections>` operator to filter a link based on its type. For example, since ``actor.roles`` might be of type ``Movie`` or ``TVShow``, to only return ``roles`` that are ``Movie`` types, you would use the ``.is`` type intersection operator:

.. code-block:: typescript

  e.select(e.Actor, (actor) => ({
    movies: actor.roles.is(e.Movie),
  }));

This is how you would use the EdgeQL :eql:op:`[is type] <isintersect>` type intersection operator via the TypeScript query builder.


Filters on link properties
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    title: true,
    actors: (actor) => ({
      name: true,
      filter: e.op(actor["@character_name"], "ilike", "Tony Stark"),
    }),
    filter_single: { title: "Iron Man" },
  }));


Ordering
^^^^^^^^

As with ``filter``, you can pass a value with the special ``order_by`` key. To simply order by a property:

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    order_by: movie.title,
  }));

.. note::

  Unlike ``filter``, ``order_by`` is *not* a reserved word in |Gel|. Using ``order_by`` as a link or property name will create a naming conflict and likely cause bugs.

The ``order_by`` key can correspond to an arbitrary expression.

.. code-block:: typescript

  // order by length of title
  e.select(e.Movie, (movie) => ({
    order_by: e.len(movie.title),
  }));
  /*
    select Movie
    order by len(.title)
  */

  // order by number of actors
  e.select(e.Movie, (movie) => ({
    order_by: e.count(movie.actors),
  }));
  /*
    select Movie
    order by count(.actors)
  */

You can customize the sort direction and empty-handling behavior by passing an object into ``order_by``.

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    order_by: {
      expression: movie.title,
      direction: e.DESC,
      empty: e.EMPTY_FIRST,
    },
  }));
  /*
    select Movie
    order by .title desc empty first
  */

.. list-table::

  * - Order direction
    - ``e.DESC`` ``e.ASC``
  * - Empty handling
    - ``e.EMPTY_FIRST`` ``e.EMPTY_LAST``

Pass an array of objects for compound ordering.

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    title: true,
    order_by: [
      {
        expression: movie.title,
        direction: e.DESC,
      },
      {
        expression: e.count(movie.actors),
        direction: e.ASC,
        empty: e.EMPTY_LAST,
      },
    ],
  }));


Offset and limit
^^^^^^^^^^^^^^^^

You can pass an expression with an integer type or a plain JS number.

.. code-block:: typescript

  e.select(e.Movie, (movie) => ({
    offset: 50,
    limit: e.int64(10),
  }));
  /*
    select Movie
    offset 50
    limit 10
  */

Computed properties
^^^^^^^^^^^^^^^^^^^

To select a computed property, just add it to the returned shape alongside the other elements. All reflected functions are typesafe, so the output type will be correctly inferred.

.. code-block:: typescript

  const query = e.select(e.Movie, movie => ({
    title: true,
    uppercase_title: e.str_upper(movie.title),
    title_length: e.len(movie.title),
  }));

  const result = await query.run(client);
  /* =>
    [
      {
        title:"Iron Man",
        uppercase_title: "IRON MAN",
        title_length: 8
      },
      ...
    ]
  */
  // {name: string; uppercase_title: string, title_length: number}[]


Computed fields can "override" an actual link/property as long as the type signatures agree.

.. code-block:: typescript

  e.select(e.Movie, movie => ({
    title: e.str_upper(movie.title), // this works
    release_year: e.str("2012"), // TypeError

    // you can override links too
    actors: e.Person,
  }));


.. _ref_qb_polymorphism:

Polymorphism
^^^^^^^^^^^^

EdgeQL supports polymorphic queries using the ``[is type]`` prefix.

.. code-block:: edgeql

  select Content {
    title,
    [is Movie].release_year,
    [is TVShow].num_seasons
  }

In the query builder, this is represented with the ``e.is`` function.

.. code-block:: typescript

  e.select(e.Content, content => ({
    title: true,
    ...e.is(e.Movie, { release_year: true }),
    ...e.is(e.TVShow, { num_seasons: true }),
  }));

  const result = await query.run(client);
  /* {
    title: string;
    release_year: number | null;
    num_seasons: number | null;
  }[] */

The ``release_year`` and ``num_seasons`` properties are nullable to reflect the fact that they will only occur in certain objects.

.. note::

  In EdgeQL it is not valid to select the ``id`` property in a polymorphic field. So for convenience when using the ``['*']`` all properties shorthand with ``e.is``, the ``id`` property will be filtered out of the polymorphic shape object.


Detached
^^^^^^^^

Sometimes you need to "detach" a set reference from the current scope. (Read the :ref:`reference docs <ref_edgeql_with_detached>` for details.) You can achieve this in the query builder with the top-level ``e.detached`` function.

.. code-block:: typescript

  const query = e.select(e.Person, (outer) => ({
    name: true,
    castmates: e.select(e.detached(e.Person), (inner) => ({
      name: true,
      filter: e.op(outer.acted_in, 'in', inner.acted_in)
    })),
  }));
  /*
    with outer := Person
    select Person {
      name,
      castmates := (
        select detached Person { name }
        filter .acted_in in Person.acted_in
      )
    }
  */

Selecting free objects
^^^^^^^^^^^^^^^^^^^^^^

Select a free object by passing an object into ``e.select``. Notice that this is an object literal rather than a function like in the previous examples.

.. code-block:: typescript

  const movies = e.select(e.Movie, (movie) => ({
    ...movie["*"],
  }));

  e.select({
    of: e.str("Movie"),
    count: e.count(movies),
    data: movies,
  });
  /*
  with movies := (select Movie { * })
  select {
    of := "Movie",
    count := count(movies),
    data := movies
  }
  */
  // { of: string; count: number; data: Movie[] }

.. _gel-js-insert:

Insert
------

Insert new data with ``e.insert``.

.. code-block:: typescript

  e.insert(e.Movie, {
    title: e.str("Spider-Man: No Way Home"),
    release_year: e.int64(2021),
  });

For convenience, the second argument of ``e.insert`` function can also accept plain JS data or a named tuple.

.. code-block:: typescript

  e.params(
    {
      movie: e.tuple({
        title: e.str,
        release_year: e.int64,
      })
    },
    (params) => e.insert(e.Movie, params.movie)
  );


Link properties
^^^^^^^^^^^^^^^

As in EdgeQL, link properties are inserted inside the shape of a subquery.

.. code-block:: typescript

  const query = e.insert(e.Movie, {
    title: "Iron Man",
    actors: e.select(e.Person, person => ({
      filter_single: { name: "Robert Downey Jr." },
      "@character_name": e.str("Tony Stark")

      // link props must correspond to expressions
      "@character_name": "Tony Stark"  // invalid
    }))
  });


.. note::

  For technical reasons, link properties must correspond to query builder expressions, not plain JS data.

Similarly you can directly include link properties inside nested ``e.insert`` queries:

.. code-block:: typescript

  const query = e.insert(e.Movie, {
    title: "Iron Man",
    release_year: 2008,
    actors: e.insert(e.Person, {
      name: "Robert Downey Jr.",
      "@character_name": e.str("Tony Stark")
    }),
  });

Handling conflicts
^^^^^^^^^^^^^^^^^^
.. index:: querybuilder, unlessconflict, unless conflict, constraint

In EdgeQL, "upsert" functionality is achieved by handling **conflicts** on ``insert`` statements with the ``unless conflict`` clause. In the query builder, this is possible with the ``.unlessConflict`` method (available only on ``insert`` expressions).

In the simplest case, adding ``.unlessConflict`` with no arguments will prevent Gel from throwing an error if the insertion would violate an exclusivity constraint. Instead, the query returns an empty set.

.. code-block:: typescript

  const query = e.insert(e.Movie, {
    title: "Spider-Man: No Way Home",
    release_year: 2021
  }).unlessConflict();
  // => { id: string } | null


Provide an ``on`` clause to "catch" conflicts only on a specific property/link.

.. code-block:: typescript

  const query = e
    .insert(e.Movie, {
      title: "Spider-Man: No Way Home",
      release_year: 2021
    })
    .unlessConflict((movie) => ({
      on: movie.title, // can be any expression
    }));


You can also provide an ``else`` expression which will be executed and returned in case of a conflict. You must specify an ``on`` clause in order to use ``else``.

The following query simply returns the conflicting object.

.. code-block:: typescript

  const query = e
    .insert(e.Movie, {
      title: "Spider-Man: Homecoming",
      release_year: 2021
    })
    .unlessConflict((movie) => ({
      on: movie.title,
      else: movie,
    }));

Or you can perform an upsert operation with an ``e.update`` in the ``else``.

.. code-block:: typescript

  const query = e
    .insert(e.Movie, {
      title: "Spider-Man: Homecoming",
      release_year: 2021
    })
    .unlessConflict((movie) => ({
      on: movie.title,
      else: e.update(movie, () => ({
        set: {
          release_year: 2021
        }
      })),
  });


If the constraint you're targeting is a composite constraint, wrap the properties in a tuple.

.. code-block:: typescript

  const query = e
    .insert(e.Movie, {
      title: "Spider-Man: No Way Home",
      release_year: 2021
    })
    .unlessConflict((movie) => ({
      on: e.tuple([movie.title, movie.release_year])
    }));

.. _gel-js-update:

Update
------

Update objects with the ``e.update`` function.

.. code-block:: typescript

  e.update(e.Movie, () => ({
    filter_single: { title: "Avengers 4" },
    set: {
      title: "Avengers: Endgame"
    }
  }))

You can reference the current value of the object's properties.

.. code-block:: typescript

  e.update(e.Movie, (movie) => ({
    filter: e.op(movie.title[0], '=', ' '),
    set: {
      title: e.str_trim(movie.title)
    }
  }))

You can conditionally update a property by using an :ref:`optional parameter <gel-js-optional-parameters>` and the :ref:`coalescing infix operator <gel-js-funcops-infix>`.

.. code-block:: typescript

  e.params({ id: e.uuid, title: e.optional(e.str) }, (params) =>
    e.update(e.Movie, (movie) => ({
      filter_single: { id: params.id },
      set: {
        title: e.op(params.title, "??", movie.title),
      }
    }))
  );

Note that ``e.update`` will return just the ``{ id: true }`` of the updated object. If you want to select further properties, you can wrap the update in a ``e.select`` call. This is still just a single query to the database.

.. code-block:: typescript

  e.params({ id: e.uuid, title: e.optional(e.str) }, (params) => {
    const updated = e.update(e.Movie, (movie) => ({
      filter_single: { id: params.id },
      set: {
        title: e.op(params.title, "??", movie.title),
      },
    }));
    return e.select(updated, (movie) => ({
      title: movie.title,
    }));
  });

Updating links
^^^^^^^^^^^^^^

EdgeQL supports some convenient syntax for appending to, subtracting from, and overwriting links.  In the query builder this is represented with the following syntax:

**Overwrite a link**

.. code-block:: typescript

  const actors = e.select(e.Person, ...);
  e.update(e.Movie, movie => ({
    filter_single: {title: 'The Eternals'},
    set: {
      actors: actors,
    }
  }))

**Add to a link**

.. code-block:: typescript

  const actors = e.select(e.Person, ...);
  e.update(e.Movie, movie => ({
    filter_single: {title: 'The Eternals'},
    set: {
      actors: { "+=": actors },
    }
  }))


**Subtract from a link**

.. code-block:: typescript

  const actors = e.select(e.Person, ...);
  e.update(e.Movie, movie => ({
    filter_single: {title: 'The Eternals'},
    set: {
      actors: { "-=": actors },
    }
  }))

**Updating a single link property**

.. code-block:: typescript

  e.update(e.Movie, (movie) => ({
    filter_single: { title: "The Eternals" },
    set: {
      actors: {
        "+=": e.select(movie.actors, (actor) => ({
          "@character_name": e.str("Sersi"),
          filter: e.op(actor.name, "=", "Gemma Chan")
        }))
      }
    }
  }));

**Updating many link properties**

.. code-block:: typescript

  const q = e.params(
    {
      cast: e.array(e.tuple({ name: e.str, character_name: e.str })),
    },
    (params) =>
      e.update(e.Movie, (movie) => ({
        filter_single: { title: "The Eternals" },
        set: {
          actors: {
            "+=": e.for(e.array_unpack(params.cast), (cast) =>
              e.select(movie.characters, (character) => ({
                "@character_name": cast.character_name,
                filter: e.op(cast.name, "=", character.name),
              })),
            ),
          },
        },
      })),
  ).run(client, {
    cast: [
      { name: "Gemma Chan", character_name: "Sersi" },
      { name: "Richard Madden", character_name: "Ikaris" },
      { name: "Angelina Jolie", character_name: "Thena" },
      { name: "Salma Hayek", character_name: "Ajak" },
    ],
  });

.. _gel-js-delete:

Delete
------

Delete objects with ``e.delete``.

.. code-block:: typescript

  e.delete(e.Movie, (movie) => ({
    filter_single: { id: "00000000-0000-0000-0000-000000000000" },
    order_by: movie.title,
    offset: 10,
    limit: 10
  }));

The only supported keys are ``filter``, ``filter_single``, ``order_by``, ``offset``, and ``limit``.

.. _gel-js-for:

For
---

``for`` expressions let you create an expression that represents iterating over any set of values.

.. code-block:: typescript

  const query = e.for(e.set(1, 2, 3, 4), (number) => {
    return e.op(2, '^', number);
  });
  /*
    for number in {1, 2, 3, 4}
    2 ^ number
  */
  const result = query.run(client);
  // [2, 4, 8, 16]

.. _gel-js-group:

Group
-----

The ``group`` statement provides a powerful mechanism for categorizing a set of objects (e.g., movies) into *groups*. You can group by properties, expressions, or combinatations thereof.

Simple grouping
^^^^^^^^^^^^^^^

Sort a set of objects by a simple property.

.. tabs::

  .. code-tab:: typescript

    e.group(e.Movie, movie => {
      return {
        by: {release_year: movie.release_year}
      }
    });
    /*
      [
        {
          key: {release_year: 2008},
          grouping: ["release_year"],
          elements: [{id: "..."}, {id: "..."}]
        },
        {
          key: { release_year: 2009 },
          grouping: ["release_year"],
          elements: [{id: "..."}, {id: "..."}]
        },
        // ...
      ]
    */

  .. code-tab:: edgeql

    group Movie
    by .release_year

Add a shape that will be applied to ``elements``. The ``by`` key is a special key, similar to ``filter``, etc. in ``e.select``. All other keys are interpreted as *shape elements* and support the same functionality as ``e.select`` (nested shapes, computeds, etc.).

.. tabs::

  .. code-tab:: typescript

    e.group(e.Movie, (movie) => ({
      title: true,
      actors: { name: true },
      num_actors: e.count(movie.characters),
      by: { release_year: movie.release_year },
    }));
    /* [
      {
        key: {release_year: 2008},
        grouping: ["release_year"],
        elements: [{
          title: "Iron Man",
          actors: [...],
          num_actors: 5
        }, {
          title: "The Incredible Hulk",
          actors: [...],
          num_actors: 3
        }]
      },
      // ...
    ] */

  .. code-tab:: edgeql

    group Movie {
      title,
      num_actors := count(.actors)
    }
    by .release_year

Group by a tuple of properties.

.. tabs::

  .. code-tab:: typescript

    e.group(e.Movie, (movie) => {
      const release_year = movie.release_year;
      const first_letter = movie.title[0];
      return {
        title: true,
        by: { release_year, first_letter }
      };
    });
    /*
      [
        {
          key: {release_year: 2008, first_letter: "I"},
          grouping: ["release_year", "first_letter"],
          elements: [{title: "Iron Man"}]
        },
        {
          key: {release_year: 2008, first_letter: "T"},
          grouping: ["release_year", "first_letter"],
          elements: [{title: "The Incredible Hulk"}]
        },
        // ...
      ]
    */

  .. code-tab:: edgeql

    group Movie { title }
    using first_letter := .title[0]
    by .release_year, first_letter

Using grouping sets to group by several expressions simultaneously.

.. tabs::

  .. code-tab:: typescript

    e.group(e.Movie, (movie) => {
      const release_year = movie.release_year;
      const first_letter = movie.title[0];
      return {
        title: true,
        by: e.group.set({release_year, first_letter})
      };
    });
    /* [
      {
        key: {release_year: 2008},
        grouping: ["release_year"],
        elements: [{title: "Iron Man"}, {title: "The Incredible Hulk"}]
      },
      {
        key: {first_letter: "I"},
        grouping: ["first_letter"],
        elements: [{title: "Iron Man"}, {title: "Iron Man 2"}, {title: "Iron Man 3"}],
      },
      // ...
    ] */

  .. code-tab:: edgeql

    group Movie { title }
    using first_letter := .title[0]
    by {.release_year, first_letter}


Using a combination of tuples and grouping sets.

.. tabs::

  .. code-tab:: typescript

    e.group(e.Movie, (movie) => {
      const release_year = movie.release_year;
      const first_letter = movie.title[0];
      const cast_size = e.count(movie.actors);
      return {
        title: true,
        by: e.group.tuple(release_year, e.group.set({ first_letter, cast_size }))
      };
    });
    /* [
      {
        key: {release_year: 2008, first_letter: "I"},
        grouping: ["release_year", "first_letter"],
        elements: [{title: "Iron Man"}]
      },
      {
        key: {release_year: 2008, cast_size: 3},
        grouping: ["release_year", "cast_size"],
        elements: [{title: "The Incredible Hulk"}]
      },
      // ...
    ] */

  .. code-tab:: edgeql

    group Movie { title }
    using
      first_letter := .title[0],
      cast_size := count(.actors)
    by .release_year, {first_letter, cast_size}



The ``group`` statement provides a syntactic sugar for defining certain common grouping sets: ``cube`` and ``rollup``. Here's a quick primer on how they work:

.. code-block::

  ROLLUP (a, b, c)
  is equivalent to
  {(), (a), (a, b), (a, b, c)}

  CUBE (a, b)
  is equivalent to
  {(), (a), (b), (a, b)}

To use these in the query builder use the ``e.group.cube`` and ``e.group.rollup`` functions.


.. tabs::

  .. code-tab:: typescript

    e.group(e.Movie, (movie) => {
      const release_year = movie.release_year;
      const first_letter = movie.title[0];
      const cast_size = e.count(movie.actors);
      return {
        title: true,
        by: e.group.rollup({release_year, first_letter, cast_size})
      };
    });

  .. code-tab:: edgeql

    group Movie { title }
    using
      first_letter := .title[0],
      cast_size := count(.actors)
    by rollup(.release_year, first_letter, cast_size)

.. tabs::

  .. code-tab:: typescript

    e.group(e.Movie, (movie) => {
      const release_year = movie.release_year;
      const first_letter = movie.title[0];
      const cast_size = e.count(movie.actors);
      return {
        title: true,
        by: e.group.cube({release_year, first_letter, cast_size})
      };
    });

  .. code-tab:: edgeql

    group Movie { title }
    using
      first_letter := .title[0],
      cast_size := count(.actors)
    by cube(.release_year, first_letter, cast_size)

.. _gel-js-with:

With Blocks
-----------

During the query rendering step, the number of occurrences of each expression are tracked. If an expression occurs more than once it is automatically extracted into a ``with`` block.

.. code-block:: typescript

  const x = e.int64(3);
  const y = e.select(e.op(x, '^', x));

  y.toEdgeQL();
  // with x := 3
  // select x ^ x

  const result = await y.run(client);
  // => 27

This hold for expressions of arbitrary complexity.

.. code-block:: typescript

  const robert = e.insert(e.Person, {
    name: "Robert Pattinson"
  });
  const colin = e.insert(e.Person, {
    name: "Colin Farrell"
  });
  const newMovie = e.insert(e.Movie, {
    title: "The Batman",
    actors: e.set(colin, robert)
  });

  /*
  with
    robert := (insert Person { name := "Robert Pattinson"}),
    colin := (insert Person { name := "Colin Farrell"}),
  insert Movie {
    title := "The Batman",
    actors := {robert, colin}
  }
  */

Note that ``robert`` and ``colin`` were pulled out into a top-level with block. To force these variables to occur in an internal ``with`` block, you can short-circuit this logic with ``e.with``.


.. code-block:: typescript

  const robert = e.insert(e.Person, {
    name: "Robert Pattinson"
  });
  const colin = e.insert(e.Person, {
    name: "Colin Farrell"
  });
  const newMovie = e.insert(e.Movie, {
    actors: e.with([robert, colin], // list "dependencies"
      e.select(e.set(robert, colin))
    )
  })

  /*
  insert Movie {
    title := "The Batman",
    actors := (
      with
        robert := (insert Person { name := "Robert Pattinson"}),
        colin := (insert Person { name := "Colin Farrell"})
      select {robert, colin}
    )
  }
  */


.. note::

  It's an error to pass an expression into multiple ``e.with``\ s, or use an expression passed to ``e.with`` outside of that block.

To explicitly create a detached "alias" of another expression, use ``e.alias``.

.. code-block:: typescript

  const a = e.set(1, 2, 3);
  const b = e.alias(a);

  const query = e.select(e.op(a, '*', b))
  // WITH
  //   a := {1, 2, 3},
  //   b := a
  // SELECT a + b

  const result = await query.run(client);
  // => [1, 2, 3, 2, 4, 6, 3, 6, 9]

