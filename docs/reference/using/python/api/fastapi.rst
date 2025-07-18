.. _gel-python-fastapi:

=============
FastAPI + Gel
=============

.. py:currentmodule:: gel

The ``gel`` Python package offers a sleek addition to FastAPI. With the built-in tools for schema migration management and automatic reflection into Pydantic models you can quickly integrate into the FastAPI development workflow. The ORM and query-building capability of Gel make building endpoints simple. So install ``gel`` and ``fastapi`` Python packages and run :gelcmd:`init` to setup the database and get started.

To initialize a Gel-aware FastAPI project, create the following file:

.. code-block:: python
  :caption: main.py

  import fastapi
  import gel.fastapi

  app = fastapi.FastAPI()
  db = gel.fastapi.gelify(app)

  @app.get("/")
  async def index():
      # get the Gel client associated with the app
      db = g.client
      # This is an actual (trivial) query sent to Gel
      return await db.query_single("select 'Hello world!'")

...and start the FastAPI development:

.. code-block:: bash

  $ fastapi dev main.py

Among the output you should see some messages from |gelcmd|:

.. code-block::

  gel   Hint: --migrate will apply any changes from your schema files to the
        database. When ready to commit your changes, use:
  gel   1) `gel migration create` to write those changes to a migration file,
  gel   2) `gel migrate --dev-mode` to replace all synced changes with the
        migration.
  gel
  gel   Monitoring /home/projects/myproject for changes in:
  gel
  gel   --migrate: gel migration apply --dev-mode
  gel
  gel   Automatic backup is enabled, see the full backup list with "gel
        instance list-backups -I myproject".
  gel   Read more at https://geldata.com/p/localdev


It's a bit of a mouthful, but basically it's informing you that the database that was set up by :gelcmd:`init` will now be monitored. More specifically, the schema files (typically found in :dotgel:`dbschema/default`) will be used to automatically apply migrations when the schema is edited. Every time a migration is about to be applied a backup will be made as well, to make sure that it's easy to revert to a previous state if anything goes wrong.

There will also be another message:

.. code-block::

  gel   hook schema.update.after: gel-generate-py models
       --output=/home/projects/myproject/models
  gel    Found Gel project: /home/projects/myproject/models

That's the automatic schema reflection in action. There's not much in the schema at this moment, except for all the standard built-in stuff. But all that still gets reflected into the ``models`` Python package and will be useful for building queries.

Let's start with a simple schema first - just a ``Person`` with a name and email:

.. code-block:: sdl
  :caption: :dotgel:`dbschema/default`

  module default {
    type Person {
      required name: str {
        constraint exclusive;
      }
      required email: str {
        constraint exclusive;
      }
    }
  }

After you save that schema, you can watch the ``fastapi dev`` process pick up that change and update the database as well as the ``models``. Now we'll be able to create some endpoints.

Let's start with endpoints for creating and listing people:

.. code-block:: python-diff
  :caption: main.py

    import fastapi
    import gel.fastapi

  + from pydantic import BaseModel
  + from models import default, std

    app = fastapi.FastAPI()
    g = gel.fastapi.gelify(app)


    @app.get("/")
    async def index():
        # get the Gel client associated with the app
        db = g.client
        return await db.query_single("select 'Hello world!'")
  +
  +
  + class CreatePerson(BaseModel):
  +     name: str
  +     email: str
  +
  +
  + @app.post("/person/")
  + async def create_person(data: CreatePerson):
  +     db = g.client
  +     person = default.Person(**data.model_dump())
  +     await db.save(person)
  +     return person.id
  +
  +
  + @app.get("/people/", response_model=list[default.Person])
  + async def get_people():
  +     db = g.client
  +     q = default.Person.order_by(name=True)
  +     return await db.query(q)

In order to create a new person we'll need a simple input model with the ``name`` and ``email`` fields. We can then use that input model to initialize the fields of ``default.Person`` reflected Gel model. After that all that's left is to call ``save()`` on our database client, passing the new person we want to save. Finally, we can just return the ``person.id`` since it will be initialized after the model is saved.

Listing all existing people is even simpler. We just use the query builder to create a query by starting with the base model we want to fetch: ``default.Person``. In this case we're fetching all the data, so we don't need any filters added, but we still probably want to sort the results, so we add an ``order_by(name=True)``. Then we use the database client to run the query, just like we would run a hand-written query. We'll get a bunch of ``default.Person`` objects as the response, so we can set ``response_model=list[default.Person]``.

We can use the built-in FastAPI docs to introspect the endpoints and even try them out.

Set up a few people with the following inputs:

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/person/

  {
    "name": "Alice",
    "email": "alice@gel.com"
  }

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/person/

  {
    "name": "Billie",
    "email": "billie@gel.com"
  }

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/person/

  {
    "name": "Cameron",
    "email": "cameron@gel.com"
  }

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/person/

  {
    "name": "Dana",
    "email": "dana@gel.com"
  }

And then we can try out the endpoint listing all people, getting:

.. code-block:: json
  :caption: GET http://127.0.0.1:8000/people/

  [
    {
      "id": "60a49492-4aa1-11f0-8507-4729d6e4bd07",
      "email": "alice@gel.com",
      "name": "Alice"
    },
    {
      "id": "8ae1bd40-4aa4-11f0-9256-33400a7cef0d",
      "email": "billie@gel.com",
      "name": "Billie"
    },
    {
      "id": "c2407822-4aa8-11f0-9854-73380baaaa0c",
      "email": "cameron@gel.com",
      "name": "Cameron"
    },
    {
      "id": "c9ee56ac-4aa8-11f0-9854-3f9a869324db",
      "email": "dana@gel.com",
      "name": "Dana"
    }
  ]

Now that we can add and view people let's expand the functionality to create a "friends list". First we're going to need to update our schema (and let the Gel hooks do their migration and reflection magic):

.. code-block:: sdl-diff
  :caption: :dotgel:`dbschema/default`

    module default {
      type Person {
        required name: str {
          constraint exclusive;
        }
        required email: str {
          constraint exclusive;
        }
  +     multi friends: Person;
      }
    }

We're going to keep the existing endpoints, but we'll need some more models to describe the input and output:

.. code-block:: python-diff
  :caption: main.py

    import fastapi
    import gel.fastapi

    from pydantic import BaseModel
    from models import default, std

    app = fastapi.FastAPI()
    g = gel.fastapi.gelify(app)


    @app.get("/")
    async def index():
        # get the Gel client associated with the app
        db = g.client
        # This is an actual (trivial) query sent to Gel
        return await db.query_single("select 'Hello world!'")


    class CreatePerson(BaseModel):
        name: str
        email: str


  + class BasePerson(default.Person.__variants__.Base):
  +     name: default.Person.__typeof__.name
  +     email: default.Person.__typeof__.email
  +
  +
    @app.post("/person/")
    async def create_person(data: CreatePerson):
        db = g.client
        person = default.Person(**data.model_dump())
        await db.save(person)
        return person.id


  - @app.get("/people/", response_model=list[default.Person])
  + @app.get("/people/", response_model=list[BasePerson])
    async def get_people():
        db = g.client
  -     q = default.Person.order_by(name=True)
  +     q = BasePerson.order_by(name=True)
        return await db.query(q)

The ``BasePerson`` model is derived from the ``default.Person.__variants__.Base`` by only declaring the ``name`` and ``email`` fields. The ``__variants__`` contain several useful model templates. The ``Base`` template just has the ``id`` so that it can be used to declare only the fields we need. In addition to being useful as a Pydantic model that declares the expected output shape, it can also be used as the base model in the query builder (since it's derived from one of the ``__variants__``).

We still need to add another endpoint for adding friends as well as the corresponding output model:

.. code-block:: python-diff
  :caption: main.py

    import fastapi
    import gel.fastapi

    from pydantic import BaseModel
    from models import default, std

    app = fastapi.FastAPI()
    g = gel.fastapi.gelify(app)


    @app.get("/")
    async def index():
        # get the Gel client associated with the app
        db = g.client
        # This is an actual (trivial) query sent to Gel
        return await db.query_single("select 'Hello world!'")


    class CreatePerson(BaseModel):
        name: str
        email: str


    class BasePerson(default.Person.__variants__.Base):
        name: default.Person.__typeof__.name
        email: default.Person.__typeof__.email


  + class PersonWithFriends(BasePerson):
  +     friends: list[BasePerson]
  +
  +
    @app.post("/person/")
    async def create_person(data: CreatePerson):
        db = g.client
        person = default.Person(**data.model_dump())
        await db.save(person)
        return person.id


    @app.get("/people/", response_model=list[BasePerson])
    async def get_people():
        db = g.client
        q = BasePerson.order_by(name=True)
        return await db.query(q)
  +
  +
  + @app.post("/person/{pname}/add_friend", response_model=PersonWithFriends)
  + async def add_friend(
  +     pname: str,
  +     frname: str,
  + ):
  +     db = g.client
  +     # fetch the main person
  +     person = await db.get(
  +         default.Person.select(
  +             # fetch all properties
  +             '*',
  +             # also fetch friends (with properties)
  +             friends=True,
  +         ).filter(
  +             name=pname
  +         )
  +     )
  +     # fetch the friend
  +     friend = await db.get(
  +         default.Person.filter(
  +             name=frname
  +         )
  +     )
  +     # append the new friend to existing friends
  +     person.friends.append(friend)
  +     await db.save(person)
  +     return person

We can now try adding a friend to Alice:

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/person/Alice/add_friend?frname=Billie

  {
    "id": "60a49492-4aa1-11f0-8507-4729d6e4bd07",
    "name": "Alice",
    "email": "alice@gel.com",
    "friends": [
      {
        "id": "8ae1bd40-4aa4-11f0-9256-33400a7cef0d",
        "name": "Billie",
        "email": "billie@gel.com"
      }
    ]
  }

And another one:

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/person/Alice/add_friend?frname=Cameron

  {
    "id": "60a49492-4aa1-11f0-8507-4729d6e4bd07",
    "name": "Alice",
    "email": "alice@gel.com",
    "friends": [
      {
        "id": "8ae1bd40-4aa4-11f0-9256-33400a7cef0d",
        "name": "Billie",
        "email": "billie@gel.com"
      },
      {
        "id": "c2407822-4aa8-11f0-9854-73380baaaa0c",
        "name": "Cameron",
        "email": "cameron@gel.com"
      }
    ]
  }

If we can add a friend, we should also make an endpoint for removing a friend. We'll use the same general type of interface:

.. code-block:: python-diff
  :caption: main.py

    import fastapi
    import gel.fastapi

    from pydantic import BaseModel
    from models import default, std

    app = fastapi.FastAPI()
    g = gel.fastapi.gelify(app)


    @app.get("/")
    async def index():
        # get the Gel client associated with the app
        db = g.client
        # This is an actual (trivial) query sent to Gel
        return await db.query_single("select 'Hello world!'")


    class CreatePerson(BaseModel):
        name: str
        email: str


    class BasePerson(default.Person.__variants__.Base):
        name: default.Person.__typeof__.name
        email: default.Person.__typeof__.email


    class PersonWithFriends(BasePerson):
        friends: list[BasePerson]


    @app.post("/person/")
    async def create_person(data: CreatePerson):
        db = g.client
        person = default.Person(**data.model_dump())
        await db.save(person)
        return person.id


    @app.get("/people/", response_model=list[BasePerson])
    async def get_people():
        db = g.client
        q = BasePerson.order_by(name=True)
        return await db.query(q)


    @app.post("/person/{pname}/add_friend", response_model=PersonWithFriends)
    async def add_friend(
        pname: str,
        frname: str,
    ):
        db = g.client
        # fetch the main person
        person = await db.get(
            default.Person.select(
                '*',
                friends=True,
            ).filter(
                name=pname
            )
        )
        # fetch the friend
        friend = await db.get(
            default.Person.filter(
                name=frname
            )
        )
        # append the new friend to existing friends
        person.friends.append(friend)
        await db.save(person)
        return person
  +
  +
  + @app.post("/person/{pname}/remove_friend", response_model=PersonWithFriends)
  + async def remove_friend(
  +     pname: str,
  +     frname: str,
  + ):
  +     db = g.client
  +     # fetch the main person
  +     person = await db.get(
  +         default.Person.select(
  +             # fetch all properties
  +             '*',
  +             # also fetch friends (with properties)
  +             friends=True,
  +         ).filter(
  +             name=pname
  +         )
  +     )
  +     # find and remove the specified friend
  +     for f in person.friends:
  +         if f.name == frname:
  +             person.friends.remove(f)
  +             break
  +
  +     await db.save(person)
  +     return person

Finally, let's add an endpoint for deleting a ``Person``. We'll use the query builder to delete a specific record:

.. code-block:: python-diff
  :caption: main.py

    import fastapi
    import gel.fastapi

    from pydantic import BaseModel
    from models import default, std

    app = fastapi.FastAPI()
    g = gel.fastapi.gelify(app)


    @app.get("/")
    async def index():
        # get the Gel client associated with the app
        db = g.client
        # This is an actual (trivial) query sent to Gel
        return await db.query_single("select 'Hello world!'")


    class CreatePerson(BaseModel):
        name: str
        email: str


    class BasePerson(default.Person.__variants__.Base):
        name: default.Person.__typeof__.name
        email: default.Person.__typeof__.email


    class PersonWithFriends(BasePerson):
        friends: list[BasePerson]


    @app.post("/person/")
    async def create_person(data: CreatePerson):
        db = g.client
        person = default.Person(**data.model_dump())
        await db.save(person)
        return person.id


    @app.get("/people/", response_model=list[BasePerson])
    async def get_people():
        db = g.client
        q = BasePerson.order_by(name=True)
        return await db.query(q)


  + @app.delete("/person/{pname}")
  + async def delete_person(pname: str):
  +     db = g.client
  +     q = default.Person.filter(name=pname).delete()
  +     return await db.query_single(q)
  +
  +
    @app.post("/person/{pname}/add_friend", response_model=PersonWithFriends)
    async def add_friend(
        pname: str,
        frname: str,
    ):
        db = g.client
        # fetch the main person
        person = await db.get(
            default.Person.select(
                # fetch all properties
                '*',
                # also fetch friends (with properties)
                friends=True,
            ).filter(
                name=pname
            )
        )
        # fetch the friend
        friend = await db.get(
            default.Person.filter(
                name=frname
            )
        )
        # append the new friend to existing friends
        person.friends.append(friend)
        await db.save(person)
        return person


    @app.post("/person/{pname}/remove_friend", response_model=PersonWithFriends)
    async def remove_friend(
        pname: str,
        frname: str,
    ):
        db = g.client
        # fetch the main person
        person = await db.get(
            default.Person.select(
                # fetch all properties
                '*',
                # also fetch friends (with properties)
                friends=True,
            ).filter(
                name=pname
            )
        )
        # find and remove the specified friend
        for f in person.friends:
            if f.name == frname:
                person.friends.remove(f)
                break

        await db.save(person)
        return person

.. note:: Be careful what you delete

  Notice that the order of ``filter()`` before the ``delete()`` matters here. The ``filter()`` comes first to select what you intend to delete. If you reverse the operations, you'll end up creating a query that deletes all people and then *filters the result* of that delete operation to find the matching name.