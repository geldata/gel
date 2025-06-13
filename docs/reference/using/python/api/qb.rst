.. _gel-python-qb:

=============
Query Builder
=============

.. py:currentmodule:: gel

The ``gel-python`` package exposes a command-line tool to generate typesafe Python query builder functions for an existing project instance. The schema is reflected as Pydantic models that can be used to instantiate Gel objects and also to construct queries.

.. code-block:: bash

  $ gel-generate-py models

Consider a simple schema for an app where users can post things, comment, and follow friends:

.. code-block:: sdl
  :caption: dbschema/default.gel

  module default {
    type User {
      required name: str {
        constraint exclusive;
      }
      multi link friends: User;
      multi link posts := .<author[is Post];
      multi link comments := .<author[is Comment];
    }

    abstract type Text {
      required body: str;
      author: User;
      created_at: datetime {
        default := datetime_current()
      }
    }

    type Post extending Text {
      required title: str;
      multi link comments := .<reply_to[is Comment];
    }

    type Comment extending Text {
      reply_to: Post;
    }
  }

Running the ``gel-generate-py models`` command will create a ``models`` Python package that can now be used to interact with Gel.

Let's start by creating a few users:

.. code-block:: python

  import gel
  from models import default, std

  db = gel.create_client()

  alice = default.User(name='Alice')
  billie = default.User(name='Billie')
  cameron = default.User(name='Cameron')

  db.save(alice, billie, cameron)

The ``models`` package will have a ``default`` module corresponding to the schema module of the same name. It will contain Pydantic models that can be used to simply instantiate Gel objects and ``save`` them to the database. The ``std`` module has built-in functions, types, and operators.

We can also build up nested objects and ``save`` them as a whole structure:

.. code-block:: python

  db.save(
    default.Post(
      title='New here',
      body='Hello',
      author=alice,
    ),
    default.Post(
      title='First time',
      body='Hello',
      author=billie,
    ),
  )

The Pydantic models can also be used to build up queries for fetching objects from the database.

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.User
    everyone = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select User {*}

Passing the base model to the ``db.query()`` simply results in fetching all objects of the corresponding type from the database.

We can fetch just one object using ``db.get()`` and adding a ``.filter()`` to the query:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.User.filter(name='Alice')
    alice = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select User {*}
    filter .name = 'Alice'

We can also fetch several objects by using ``db.query()`` and providing a ``.filter``:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.Post.filter(body='Hello')
    posts = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select Post {*}
    filter .body = 'Hello'

We can have more elaborate filters by using ``lambda`` functions where the first argument represents the base of the query:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.User.filter(
      lambda u: std.len(u.name) > 5
    )
    users = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select User {*}
    filter len(.name) > 5

The expressions used in filters can be built up to follow links:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.Post.filter(
      lambda u: u.author.name == 'Alice'
    )
    posts = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select Post {*}
    filter .author.name = 'Alice'

So far fetching data resulted in flat objects, but we can also include links when fetching data by using the ``select()`` method:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.Post.select(
      '*',
      author=True,
    ).filter(
      lambda u: u.author.name == 'Alice'
    )
    posts = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select Post {
      *,
      author: {*},
    }
    filter .author.name = 'Alice'

The ``select()`` method can be used to cherry-pick the specific fields that will be fetched and populated or the ``'*'`` can be used to indicate that all properties should be fetched:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.Post.select(
      title=True,
      body=True,
      author=True,
    ).filter(
      lambda u: u.author.name == 'Alice'
    )
    posts = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select Post {
      title,
      body,
      author: {*},
    }
    filter .author.name = 'Alice'

The fetched objects can be used to update the data or as references to existing objects when creating new data. So the above query fetching ``posts`` can be user to edit the existing post and create a new one by the same user:

.. code-block:: python

  # so far we're expecting one post, so let's edit it
  posts[0].body = 'Hello world!'
  # make another post by Alice
  new_post = default.Post(
    title='Question',
    body='How do I insert data?',
    author=posts[0].author,
  )
  db.save(
    posts[0],
    new_post,
  )

We can sort the posts in Python (as long as we made sure to either fetch all the properties or explicitly included ``created_at``). However, we can also sort things in Gel and fetch posts in the right order:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.Post.select(
      '*',
      author=True,
    ).filter(
      lambda u: u.author.name == 'Alice'
    ).order_by(
      created_at=True
    )
    posts = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select Post {
      *,
      author: {*},
    }
    filter .author.name = 'Alice'
    order by .created_at

We can also add more nuance to the ordering by controlling the ordering direction as well as having multiple ordering criteria:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.Post.select(
      '*',
      author=True,
    ).filter(
      lambda u: u.author.name == 'Alice'
    ).order_by(
      created_at='desc',
      title='asc',
    )
    posts = db.query(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select Post {
      *,
      author: {*},
    }
    filter .author.name = 'Alice'
    order by .created_at desc then .title asc

The query builder lets us compose nested queries with nested sub-queries benefiting from all the same fine-tuning mechanisms for filtering and ordering:

.. tabs::

  .. code-block:: python
    :caption: Python

    q = default.User.select(
      '*',
      posts=lambda u: u.posts.order_by(
        created_at='desc',
        title='asc',
      ),
    ).filter(
      name='Alice'
    )
    user = db.get(q)

  .. code-block:: edgeql
    :caption: equivalent EdgeQL

    select User {
      *,
      posts: {
        *,
      }
      order by .created_at desc then .title asc,
    }
    filter .name = 'Alice'
