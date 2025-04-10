.. _gel-js-intro:

==========
TypeScript
==========

.. toctree::
   :maxdepth: 3
   :hidden:

   client
   datatypes
   generation
   queries
   interfaces
   querybuilder

.. _gel-js-installation:

Installation
============

Install the `client <https://www.npmjs.com/package/gel>`_ and optional (but recommended!) `generator <https://www.npmjs.com/package/@gel/generate>`_ packages from npm using your package manager of choice.

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

.. _gel-js-examples:

Basic Usage
===========

The ``gel`` package exposes a :ref:`createClient <gel-js-create-client>` function that can be used to create a new :ref:`Client <gel-js-api-client>` instance. This client instance manages a pool of connections to the database which it discovers automatically from either being in a :gelcmd:`project init` directory or being provided connection details via Environment Variables. See :ref:`the environment section of the connection reference <ref_reference_connection_environments>` for more details and options.

.. note::

  If you're using |Gel| Cloud to host your development instance, you can use the :gelcmd:`cloud login` command to authenticate with |Gel| Cloud and then use the :gelcmd:`project init --server-instance <instance-name>` command to create a local project-linked instance that is linked to an Gel Cloud instance. For more details, see :ref:`the Gel Cloud guide <ref_guide_cloud>`.

Once you have a client instance, you can use the various :ref:`query methods <gel-js-running-queries>` to execute queries. Each of these methods has an implied cardinality of the result, and if you're using TypeScript, you can provide a type parameter to receive a strongly typed result.

.. code-block:: bash

  $ mkdir gel-js-example
  $ cd gel-js-example
  $ npm init -y
  $ npm install gel
  $ npm install --save-dev @gel/generate
  $ npx gel project init --non-interactive
  $ touch index.mjs

.. code-block:: javascript
  :caption: index.mjs

  import { createClient } from "gel";
  import assert from "node:assert";

  const client = createClient(); // get connection details automatically

  // Query always returns an array of result, even for single object queries
  const queryResult = await client.query("select 1");
  assert.equal(queryResult, [1]);

  // querySingle will throw an error if the query returns more than one row
  const singleQueryResult = await client.querySingle("select 1");
  assert.equal(singleQueryResult, 1);

  // queryRequired will throw an error if the query returns no rows
  const requiredQueryResult = await client.queryRequired("select 1");
  assert.equal(requiredQueryResult, 1);

  // queryRequiredSingle will throw an error if
  // - the query returns more than one row
  // - the query returns no rows
  const requiredSingleQueryResult = await client.queryRequiredSingle("select 1");
  assert.equal(requiredSingleQueryResult, 1);

Code generation
===============

The ``@gel/generate`` npm package provides a set of generators that can make querying the database a bit more pleasant than manually constructing strings and passing explicit query element types to the query methods.

``interfaces`` generator
------------------------

The :ref:`interfaces <gel-js-interfaces>` generator will create TypeScript interfaces for the object types in your database.

.. code-block:: bash

  $ npx @gel/generate interfaces

.. code-block:: typescript
  :caption: main.mts

  import { createClient } from "gel";
  import { Movie } from "./dbschema/interfaces";

  const client = createClient();

  const result = await client.query<Movie[]>(`
    select Movie {
      **,
      actors: { ** },
    };
  `);

  console.log(result);

``queries`` generator
----------------------

The :ref:`queries <gel-js-queries>` generator will create TypeScript functions for any EdgeQL queries defined in your project in separate ``.edgeql`` files.

.. code-block:: edgeql
  :caption: get-movies.edgeql

  select Movie {
    **,
    actors: { ** },
  };

.. code-block:: bash

  $ npx @gel/generate queries

.. code-block:: typescript
  :caption: main.mts

  import { createClient } from "gel";
  import { getMovies } from "./get-movies.query";

  const client = createClient();

  const result = await getMovies(client);

  console.log(result);

``edgeql-js`` generator
-----------------------

The :ref:`edgeql-js <gel-js-qb>` generator will create a fully type-safe query builder that you can use to write code-first queries in TypeScript. This is the recommended way to write dynamic queries and many people prefer it even for static queries.

.. code-block:: bash

  $ npx @gel/generate edgeql-js

.. code-block:: typescript
  :caption: main.mts

  import { createClient } from "gel";
  import e from "./dbschema/edgeql-js";

  const client = createClient();

  const result = await e
    .params({ title: e.str }, (params) =>
      e.select(e.Movie, (m) => ({
        filter_single: e.op(m.title, "=", params.title),
        id: true,
        title: true,
        actors: { name: true },
      })),
    )
    .run(client, {
      title: "The Matrix",
    });

  console.log(result);


Next steps
==========

If you haven't already done so, you can go through our :ref:`quickstart tutorial <ref_quickstart>` to have a guided tour of using Gel as the data layer for a complex web application.

You will also find full reference information in this section of the documentation for the various generators and public APIs that the :ref:`gel <gel-js-client>` and :ref:`@gel/generate <gel-js-generators>` packages provide.
