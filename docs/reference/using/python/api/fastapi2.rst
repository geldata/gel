.. _gel-python-fastapi2:

=====================
FastAPI + Gel, part 2
=====================

.. py:currentmodule:: gel

We can use the query-building power of Gel together with FastAPI to create some impressive funcitonality.

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


    @app.delete("/person/{pname}")
    async def delete_person(pname: str):
        db = g.client
        q = default.Person.filter(name=pname).delete()
        return await db.query_single(q)


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

This app is able to create, edit, list and delete people.

First, we'll need a bit of a more advanced schema to play with. So let's create a schema for managing a multiplayer game server with a bunch of game sessions and teams for our people.

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

We've already covered how to set up basic CRUD endpoints for our Gel objects. So let's consider some endpoints with more customized funcitonality.

Adding people to a team can be done in a manner very similar to adding friends to a person. All we need are the name of the Team and the Person:

.. code-block:: python

  class BaseTeam(default.Team.__variants__.Base):
      name: default.Team.__typeof__.name
      members: list[BasePerson]


  @app.post("/teams/{team_name}/add_member", response_model=BaseTeam)
  async def add_member(team_name: str, member_name: str):
      db = g.client
      # fetch the team
      team = await db.get(
          default.Team.select(
              '*',
              members=True,
          ).filter(name=team_name)
      )
      # fetch the member
      member = await db.get(
          default.Person.filter(name=member_name)
      )
      # append the member to the team
      team.members.append(member)
      await db.save(team)
      return team


To quite a team, we cannot just fetch the Person and set the ``team`` field to ``None``, because that field is computed and cannot be edited. Instead we need to fetch the team with the members list and remove the Person from there. The challenge is to do all this when given only the Person's name:

.. code-block:: python

  @app.post("/person/{pname}/quit_team", response_model=str)
  async def quit_team(pname: str):
      db = g.client
      q = default.Person.select(
          '*',
          team=lambda u: u.team.select('*', members=True),
      ).filter(name=pname)
      # fetch the person
      person = await db.get(q)
      # remove the member from the team
      team = person.team

      if team is None:
          return 'Person is not in a team'
      else:
          team.members.remove(person)
          await db.save(team)
          return f'{pname} quit {team.name}'

Let's setup some GameSession endpoints. Find all the games where members of a specific team are playing, that aren't full and that are in "Waiting" status:

.. code-block:: python

  class GameSessionBase(default.GameSession.__variants__.Base):
      title: default.GameSession.__typeof__.title
      status: default.GameSession.__typeof__.status
      num_players: default.GameSession.__typeof__.num_players
      is_full: default.GameSession.__typeof__.is_full


  @app.get("/games/", response_model=list[GameSessionBase])
  async def get_games_with_team(team_name: str):
      db = g.client
      q = default.GameSession.filter(
          # use an expression as a filter
          lambda g: std.any(g.players.team.name == team_name),
          # filter by status and is_full
          status=default.GameStatus.Waiting,
          is_full=False,
      ).order_by(title=True)

      return await db.query(q)

Next let's setup an endpoint that starts up a game if the game is ready to be started. To start the game session needs to be full and currently in "Waiting" status. Additionally, we will use a single ``update`` query to do this instead of fetching the GameSession object, then checking the conditions in Python and saving the updated value:

.. code-block:: python

  @app.post("/games/{game_id}/start", response_model=str)
  async def start_game(game_id: uuid.UUID):
      db = g.client
      # instead of fetching the game, then updating and saving,
      # we can update directly
      q = default.GameSession.filter(
          id=game_id,
          # make sure the game is eligible to be started
          status=default.GameStatus.Waiting,
          is_full=True,
      ).update(
          status='Active',
      ).select('*')  # select the updated game
      result = await db.query(q)

      if len(result) == 0:
          return "Game not started"
      else:
          return f"{result[0].num_players} player game started"

We can also make an endpoint for finding GameSessions that have enough room for an entire Team. Just like in the previous example, we want to do this in a single query instead of fetching the Team data first and then picking the GameSessions based on that:

.. code-block:: python

  @app.get("/games/fit_team", response_model=list[GameSessionBase])
  async def get_games_for_team(team_name: str):
      db = g.client
      # make the team subquery
      team = default.Team.filter(name=team_name)
      # use the team subquery to find the games
      q = default.GameSession.filter(
          lambda g: g.max_players - g.num_players >= std.count(team.members),
      ).order_by(title=True)

      return await db.query(q)