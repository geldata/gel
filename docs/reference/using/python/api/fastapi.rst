.. _gel-python-fastapi:

=============
FastAPI + Gel
=============

.. py:currentmodule:: gel

The ``gel-python`` package offers a sleek addition to FastAPI. With the built-in tools for schema migration management and automatic reflection into Pydantic models you can quickly integrate into the FastAPI development workflow. The ORM and query-building capability of Gel make building endpoints. So install ``gel`` and ``fastapi`` Python packages, run :gelcmd:`init` to setup the database and let's get started with this primer.

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


It's a bit of a mouthful, but basically it's informing you that the database that was set up by :gelcmd:`init` will now be monitored. More specifically, the schema files (typically found in ``dbschema/default.gel``) will be used to automatically apply migrations when the schema is edited. Every time a migration is about to be applied a backup will be made as well, to make sure that it's easy to revert to a previous state if anything goes wrong.

There will also be another message:

.. code-block::

  gel   hook schema.update.after: gel-generate-py models
       --output=/home/projects/myproject/models
  gel    Found Gel project: /home/projects/myproject/models

That's the automatic schema reflection in action. There's not much in the schema at this moment, except for all the standard built-in stuff. But all that still gets reflected into the ``models`` Python package and will be useful for building queries.

Let's start with a simple schema first - just a ``User`` with a name and email:

.. code-block:: sdl
  :caption: dbschema/default.gel

  module default {
    type User {
      required name: str {
        constraint exclusive;
      }
      required email: str {
        constraint exclusive;
      }
    }
  }

After you save that schema, you can watch the ``fastapi dev`` process pickup that change and update the database as well as the ``models``. Now we'll be able to create some endpoints.

Let's start with endpoints for creating and listing users:

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
  + class CreateUser(BaseModel):
  +     name: str
  +     email: str
  +
  +
  + @app.post("/users/")
  + async def create_user(userdata: CreateUser):
  +     db = g.client
  +     user = default.User(**userdata.model_dump())
  +     await db.save(user)
  +     return user.id
  +
  +
  + @app.get("/users/", response_model=list[default.User])
  + async def get_users():
  +     db = g.client
  +     q = default.User.order_by(name=True)
  +     return await db.query(q)

In order to create a new user we'll need a simple input model with the ``name`` and ``email`` fields. We can then use that input model to initialize the fields of ``default.User`` reflected Gel model. After that all that's left is to call ``save()`` on our database client, passing the new user we want to save. Finally, we can just return the ``user.id`` since it will be initialized after the model is saved.

Listing all existing users is even simpler. We just use the query builder to create a query by starting with the base model we want to fetch: ``default.User``. In this case we're fetching all the data, so we don't need any filters added, but we still probably want to sort the results, so we add an ``order_by(name=True)``. Then we use the database client to run the query, just like we would run a hand-written query. We'll get a bunch of ``default.User`` objects as the response, so we can set ``response_model=list[default.User]``.

We can use the built-in FastAPI docs to introspect the endpoints and even try them out.

Set up a few users with the following inputs:

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/users/

  {
    "name": "Alice",
    "email": "alice@gel.com"
  }

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/users/

  {
    "name": "Billie",
    "email": "billie@gel.com"
  }

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/users/

  {
    "name": "Cameron",
    "email": "cameron@gel.com"
  }

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/users/

  {
    "name": "Dana",
    "email": "dana@gel.com"
  }

And then we can try out the endpoint listing all users, getting:

.. code-block:: json
  :caption: GET http://127.0.0.1:8000/users/

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

Now that we can add and view users let's expand the functionality to create a "friends list". First we're going to need to update our schema (and let the Gel hooks do their migration and reflection magic):

.. code-block:: sdl-diff
  :caption: dbschema/default.gel

    module default {
      type User {
        required name: str {
          constraint exclusive;
        }
        required email: str {
          constraint exclusive;
        }
  +     multi friends: User;
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


    class CreateUser(BaseModel):
        name: str
        email: str


  + class BaseUser(default.User.__variants__.Base):
  +     name: default.User.__typeof__.name
  +     email: default.User.__typeof__.name
  +
  +
    @app.post("/users/")
    async def create_user(userdata: CreateUser):
        db = g.client
        user = default.User(**userdata.model_dump())
        await db.save(user)
        return user.id


  - @app.get("/users/", response_model=list[default.User])
  + @app.get("/users/", response_model=list[BaseUser])
    async def get_users():
        db = g.client
  -     q = default.User.order_by(name=True)
  +     q = BaseUser.order_by(name=True)
        return await db.query(q)

The ``BaseUser`` model is derived from the ``default.User.__variants__.Base`` by only declaring the ``name`` and ``email`` fields. The ``__variants__`` contain several useful model templates. The ``Base`` template just has the ``id`` so that it can be used to declare only the fields we need. In addition to being useful as a Pydantic model that declares the expected output shape, it can also be used as the base model in the query builder (since it's derived from one of the ``__variants__``).

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


    class CreateUser(BaseModel):
        name: str
        email: str


    class BaseUser(default.User.__variants__.Base):
        name: default.User.__typeof__.name
        email: default.User.__typeof__.name


  + class UserWithFriends(BaseUser):
  +     friends: list[BaseUser]
  +
  +
    @app.post("/users/")
    async def create_user(userdata: CreateUser):
        db = g.client
        user = default.User(**userdata.model_dump())
        await db.save(user)
        return user.id


    @app.get("/users/", response_model=list[BaseUser])
    async def get_users():
        db = g.client
        q = BaseUser.order_by(name=True)
        return await db.query(q)
  +
  +
  + @app.post("/user/{uname}/add_friend", response_model=UserWithFriends)
  + async def add_friend(
  +     uname: str,
  +     frname: str,
  + ):
  +     db = g.client
  +     # fetch the main user
  +     user = await db.get(
  +         default.User.select(
  +             # fetch all properties
  +             '*',
  +             # also fetch friends (with properties)
  +             friends=True,
  +         ).filter(
  +             name=uname
  +         )
  +     )
  +     # fetch the friend
  +     friend = await db.get(
  +         default.User.filter(
  +             name=frname
  +         )
  +     )
  +     # append the new friend to existing friends
  +     user.friends.append(friend)
  +     await db.save(user)
  +     return user

We can now try adding a friend to Alice:

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/user/Alice/add_friend?frname=Billie

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
    ]
  }

And another one:

.. code-block:: json
  :caption: POST http://127.0.0.1:8000/user/Alice/add_friend?frname=Cameron

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


    class CreateUser(BaseModel):
        name: str
        email: str


    class BaseUser(default.User.__variants__.Base):
        name: default.User.__typeof__.name
        email: default.User.__typeof__.name


    class UserWithFriends(BaseUser):
        friends: list[BaseUser]


    @app.post("/users/")
    async def create_user(userdata: CreateUser):
        db = g.client
        user = default.User(**userdata.model_dump())
        await db.save(user)
        return user.id


    @app.get("/users/", response_model=list[BaseUser])
    async def get_users():
        db = g.client
        q = BaseUser.order_by(name=True)
        return await db.query(q)


    @app.post("/users/{uname}/add_friend", response_model=UserWithFriends)
    async def add_friend(
        uname: str,
        frname: str,
    ):
        db = g.client
        # fetch the main user
        user = await db.get(
            default.User.select(
                '*',
                friends=True,
            ).filter(
                name=uname
            )
        )
        # fetch the friend
        friend = await db.get(
            default.User.filter(
                name=frname
            )
        )
        # append the new friend to existing friends
        user.friends.append(friend)
        await db.save(user)
        return user
  +
  +
  + @app.post("/users/{uname}/remove_friend", response_model=UserWithFriends)
  + async def remove_friend(
  +     uname: str,
  +     frname: str,
  + ):
  +     db = g.client
  +     # fetch the main user
  +     user = await db.get(
  +         default.User.select(
  +             # fetch all properties
  +             '*',
  +             # also fetch friends (with properties)
  +             friends=True,
  +         ).filter(
  +             name=uname
  +         )
  +     )
  +     # find and remove the specified friend
  +     for f in user.friends:
  +         if f.name == frname:
  +             user.friends.remove(f)
  +             break
  +
  +     await db.save(user)
  +     return user

Finally, let's add an endpoint for deleting a ``User``. We'll use the query builder to delete a specific record:

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


    class CreateUser(BaseModel):
        name: str
        email: str


    class BaseUser(default.User.__variants__.Base):
        name: default.User.__typeof__.name
        email: default.User.__typeof__.name


    class UserWithFriends(BaseUser):
        friends: list[BaseUser]


    @app.post("/users/")
    async def create_user(userdata: CreateUser):
        db = g.client
        user = default.User(**userdata.model_dump())
        await db.save(user)
        return user.id


    @app.get("/users/", response_model=list[BaseUser])
    async def get_users():
        db = g.client
        q = BaseUser.order_by(name=True)
        return await db.query(q)


  + @app.delete("/users/{uname}")
  + async def delete_user(uname: str):
  +     db = g.client
  +     q = default.User.filter(name=uname).delete()
  +     return await db.query_single(q)
  +
  +
    @app.post("/users/{uname}/add_friend", response_model=UserWithFriends)
    async def add_friend(
        uname: str,
        frname: str,
    ):
        db = g.client
        # fetch the main user
        user = await db.get(
            default.User.select(
                # fetch all properties
                '*',
                # also fetch friends (with properties)
                friends=True,
            ).filter(
                name=uname
            )
        )
        # fetch the friend
        friend = await db.get(
            default.User.filter(
                name=frname
            )
        )
        # append the new friend to existing friends
        user.friends.append(friend)
        await db.save(user)
        return user


    @app.post("/users/{uname}/remove_friend", response_model=UserWithFriends)
    async def remove_friend(
        uname: str,
        frname: str,
    ):
        db = g.client
        # fetch the main user
        user = await db.get(
            default.User.select(
                # fetch all properties
                '*',
                # also fetch friends (with properties)
                friends=True,
            ).filter(
                name=uname
            )
        )
        # find and remove the specified friend
        for f in user.friends:
            if f.name == frname:
                user.friends.remove(f)
                break

        await db.save(user)
        return user

.. note:: Be careful what you delete

  Notice that the order of ``filter()`` before the ``delete()`` matters here. The ``filter()`` comes first to select what you intend to delete. If you reverse the operations, you'll end up creating a query that deletes all users and then *filters the result* of that delete operation to find the matching name.