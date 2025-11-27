.. _gel-python-fastapi2:

=====================
FastAPI + Gel, part 2
=====================

.. py:currentmodule:: gel

We can use the query-building power of Gel together with FastAPI to create some impressive functionality.

We'll save the schema and start up ``fastapi dev`` process to let it pick up the schema so that we can use it in our app. We'll resume where the basic :ref:`gel-python-fastapi` primer left off:

.. tabs::

  .. code-tab:: sdl
    :caption: :dotgel:`dbschema/default`

    module default {
      type Person {
        required name: str {
          constraint exclusive;
        }
        required email: str {
          constraint exclusive;
        }
       multi friends: Person;
      }
    }

  .. code-tab:: python
    :caption: main.py

    import fastapi
    import gel.fastapi
    import uuid

    from pydantic import BaseModel
    from models import default, std
    from gel.models.pydantic import OptionalMultiLink


    app = fastapi.FastAPI()
    gel.fastapi.gelify(app)


    @app.get("/")
    async def index(db: gel.fastapi.Client):
        # This is an actual (trivial) query sent to Gel
        return await db.query_single("select 'Hello world!'")


    class CreatePerson(BaseModel):
        name: str
        email: str


    class BasePerson(
        default.Person.__shapes__.RequiredId,
        default.Person.__shapes__.PropsAsDeclared,
    ):
        pass


    class PersonWithFriends(BasePerson):
        friends: OptionalMultiLink[BasePerson]


    @app.post("/person/", response_model=uuid.UUID)
    async def create_person(
        db: gel.fastapi.Client,
        data: CreatePerson,
    ):
        person = default.Person(**data.model_dump())
        await db.save(person)
        return person.id


    @app.get("/people/", response_model=list[BasePerson])
    async def get_people(db: gel.fastapi.Client):
        q = BasePerson.order_by(name=True)
        return await db.query(q)


    @app.patch("/person/{pname}/add_friend", response_model=PersonWithFriends)
    async def add_friend(
        db: gel.fastapi.Client,
        pname: str,
        frname: str,
    ):
        # fetch the main person using response_model type
        person = await db.get(
            PersonWithFriends.select(
                # fetch all properties
                '*',
                # also fetch friends (with properties)
                friends=True,
            ).filter(
                name=pname
            )
        )
        # fetch the friend as BasePerson, since that's what PersonWithFriends
        # expects
        friend = await db.get(
            BasePerson.filter(
                name=frname
            )
        )
        # add the new friend to existing friends
        person.friends.add(friend)
        await db.save(person)
        return person


    @app.patch("/person/{pname}/remove_friend", response_model=PersonWithFriends)
    async def remove_friend(
        db: gel.fastapi.Client,
        pname: str,
        frname: str,
    ):
        # fetch the main person
        person = await db.get(
            PersonWithFriends.select(
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


    @app.delete("/person/{pname}", response_model=uuid.UUID | None)
    async def delete_person(
        db: gel.fastapi.Client,
        pname: str,
    ):
        q = default.Person.filter(name=pname).delete()
        deleted = await db.query_single(q)
        if deleted:
            return deleted.id
        else:
            return None

This app is able to create, edit, list and delete people.

Let's improve the ``create_person`` endpoint a little bit. We can use ``__shapes__`` instead of listing all the properties. Also, since the input data will now be a valid reflected model we don't need to copy the fields via ``model_dump()`` and save the mnodel directly:

.. code-block:: python-diff
  :caption: main.py

    import fastapi
    import gel.fastapi
    import uuid

    from pydantic import BaseModel
    from models import default, std
    from gel.models.pydantic import OptionalMultiLink


    app = fastapi.FastAPI()
    gel.fastapi.gelify(app)


    @app.get("/")
    async def index(db: gel.fastapi.Client):
        # This is an actual (trivial) query sent to Gel
        return await db.query_single("select 'Hello world!'")


  - class CreatePerson(BaseModel):
  -     name: str
  -     email: str
  + class CreatePerson(default.Person.__shapes__.PropsAsDeclared):
  +     pass


    class BasePerson(
        default.Person.__shapes__.RequiredId,
        default.Person.__shapes__.PropsAsDeclared,
    ):
        pass


    class PersonWithFriends(BasePerson):
        friends: OptionalMultiLink[BasePerson]


    @app.post("/person/", response_model=uuid.UUID)
    async def create_person(
        db: gel.fastapi.Client,
  -     data: CreatePerson,
  +     person: CreatePerson,
    ):
  -     person = default.Person(**data.model_dump())
        await db.save(person)
        return person.id


    @app.get("/people/", response_model=list[BasePerson])
    async def get_people(db: gel.fastapi.Client):
        q = BasePerson.order_by(name=True)
        return await db.query(q)


    @app.patch("/person/{pname}/add_friend", response_model=PersonWithFriends)
    async def add_friend(
        db: gel.fastapi.Client,
        pname: str,
        frname: str,
    ):
        # fetch the main person using response_model type
        person = await db.get(
            PersonWithFriends.select(
                # fetch all properties
                '*',
                # also fetch friends (with properties)
                friends=True,
            ).filter(
                name=pname
            )
        )
        # fetch the friend as BasePerson, since that's what PersonWithFriends
        # expects
        friend = await db.get(
            BasePerson.filter(
                name=frname
            )
        )
        # add the new friend to existing friends
        person.friends.add(friend)
        await db.save(person)
        return person


    @app.patch("/person/{pname}/remove_friend", response_model=PersonWithFriends)
    async def remove_friend(
        db: gel.fastapi.Client,
        pname: str,
        frname: str,
    ):
        # fetch the main person
        person = await db.get(
            PersonWithFriends.select(
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


    @app.delete("/person/{pname}", response_model=uuid.UUID | None)
    async def delete_person(
        db: gel.fastapi.Client,
        pname: str,
    ):
        q = default.Person.filter(name=pname).delete()
        deleted = await db.query_single(q)
        if deleted:
            return deleted.id
        else:
            return None

Next, we'll need a bit of a more advanced schema to play with. So let's create a schema for managing a multiplayer game server with a bunch of game sessions and teams for our people.

.. code-block:: sdl-diff
  :caption: :dotgel:`dbschema/default`

    module default {
  +   abstract type Named {
  +     required name: str {
  +       delegated constraint exclusive;
  +     }
  +   }
  +
  -   type Person {
  +   type Person extending Named {
  -     required name: str {
  -       constraint exclusive;
  -     }
        required email: str {
          constraint exclusive;
        }
        multi friends: Person;
  +     game_session := .<players[is GameSession];
  +     team := .<members[is Team];
      }
  +
  +   type Team extending Named {
  +     multi members: Person {
  +         # each person can only be in one team
  +         constraint exclusive;
  +     };
  +   }
  +
  +   scalar type GameStatus extending enum<
  +     Waiting, Active, Finished, Cancelled,
  +   >;
  +
  +   type GameSession {
  +     required title: str;
  +     multi players: Person;
  +     required max_players: int16 {
  +         default := 4;
  +     };
  +     required status: GameStatus {
  +         default := GameStatus.Waiting;
  +     };
  +
  +     property num_players := count(.players);
  +     property is_full := .num_players = .max_players;
  +   }
    }

We've already covered how to set up basic CRUD endpoints for our Gel objects. So let's consider some endpoints with more customized functionality.

Adding people to a team can be done in a manner very similar to adding friends to a person. All we need are the name of the Team and the Person:

.. code-block:: python

  class BaseTeam(
      default.Team.__shapes__.RequiredId,
      default.Team.__shapes__.PropsAsDeclared,
  ):
      members: OptionalMultiLink[BasePerson]


  @app.patch("/teams/{team_name}/add_member", response_model=BaseTeam)
  async def add_member(
      db: gel.fastapi.Client,
      team_name: str,
      member_name: str,
  ):
      # fetch the team
      team = await db.get(
          BaseTeam.select(
              '*',
              members=True,
          ).filter(name=team_name)
      )
      # fetch the member
      member = await db.get(
          BasePerson.filter(name=member_name)
      )
      # append the member to the team
      team.members.add(member)
      await db.save(team)
      return team

To quit a team, we cannot just fetch the Person and set the ``team`` field to ``None``, because that field is computed and cannot be edited. Instead we need to fetch the team with the members list and remove the Person from there. The challenge is to do all this when given only the Person's name:

.. code-block:: python

  class TeamPerson(BasePerson):
      team: OptionalComputedLink[BaseTeam]


  @app.patch("/person/{pname}/quit_team", response_model=TeamPerson)
  async def quit_team(
      db: gel.fastapi.Client,
      pname: str,
  ):
      q = default.Team.select(
          members=True,
      ).filter(
          # find the team based on the member name
          lambda t: t.members.name == pname
      )
      team = await db.get(q)

      if team is not None:
          # remove the specified team member
          for m in team.members:
              if m.name == pname:
                  team.members.remove(m)
                  break
          await db.save(team)

      # fetch the specified person with whatever team they have
      return await db.get(
          TeamPerson.select(
              '*',
              team=True,
          ).filter(name=pname)
      )

Let's setup some ``GameSession`` endpoints. First we can setup a dynamic filtering endpoint. We can list all games based on their status, being full, or where members of a specific team are playing:

.. code-block:: python

  class GameSessionBase(
      default.GameSession.__shapes__.RequiredId,
      default.GameSession.__shapes__.PropsAsDeclared,
  ):
      pass


  # we'll need links for the query
  class GameSessionQuery(
      GameSessionBase,
      default.GameSession.__shapes__.LinksAsDeclared,
  ):
      pass


  @app.get("/games/", response_model=list[GameSessionBase])
  async def get_games(
      db: gel.fastapi.Client,
      is_full: bool | None = None,
      status: default.GameStatus | None = None,
      team_name: str | None = None,
  ):
      q = GameSessionQuery

      if is_full is not None:
          q = q.filter(is_full=is_full)
      if status is not None:
          q = q.filter(status=status)
      if team_name is not None:
          q = q.filter(
              # use an expression as a filter
              lambda g: std.any(g.players.team.name == team_name)
          )

      return await db.query(q.order_by(title=True))

Next let's setup an endpoint that starts up a game if the game is ready to be started. To start the game session needs to be full and currently in "Waiting" status. Additionally, we will use a single ``update`` query to do this instead of fetching the GameSession object, then checking the conditions in Python and saving the updated value:

.. code-block:: python

  @app.post("/games/{game_id}/start", response_model=GameSessionBase)
  async def start_game(
      db: gel.fastapi.Client,
      game_id: uuid.UUID,
  ):
      # instead of fetching the game, then updating and saving,
      # we can update directly
      q = GameSessionBase.filter(
          id=game_id,
          # make sure the game is eligible to be started
          status=default.GameStatus.Waiting,
          is_full=True,
      ).update(
          status=default.GameStatus.Active,
      ).select('*')  # select the updated game
      result = await db.get(q)

      if result is None:
          raise fastapi.HTTPException(
              f"No eligible game found with id '{game_id}'",
              status_code=404,
          )

      return result

We can also make an endpoint for finding GameSessions that have enough room for an entire Team. For this we will update ``get_games`` to and add another filter to it. Similar to the previous example, we want to write a single query instead of fetching the Team data first and then picking the GameSessions based on that:

.. code-block:: python-diff

    @app.get("/games/", response_model=list[GameSessionBase])
    async def get_games(
        db: gel.fastapi.Client,
        is_full: bool | None = None,
        status: default.GameStatus | None = None,
        team_name: str | None = None,
  +     fit_team: str | None = None,
    ):
        q = GameSessionQuery

        if is_full is not None:
            q = q.filter(is_full=is_full)
        if status is not None:
            q = q.filter(status=status)
        if team_name is not None:
            q = q.filter(
                # use an expression as a filter
                lambda g: std.any(g.players.team.name == team_name)
            )
  +     if fit_team is not None:
  +         # make the team subquery
  +         team = default.Team.filter(name=team_name)
  +         # use the team subquery to find the games
  +         q = q.filter(
  +             lambda g: g.max_players >= std.count(
  +                 # remove duplicates
  +                 std.distinct(
  +                     # put together all team members and players
  +                     std.union(team.members, g.players)
  +                 )
  +             )
  +         )

        return await db.query(q.order_by(title=True))
