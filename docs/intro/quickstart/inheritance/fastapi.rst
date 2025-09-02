.. _ref_quickstart_fastapi_inheritance:

========================
Adding shared properties
========================

.. edb:split-section::

  One common pattern in applications is to add shared properties to the schema that are used by multiple objects. For example, you might want to add a ``created_at`` and ``updated_at`` property to every object in your schema. You can do this by adding an abstract type and using it as a mixin for your other object types.

  .. code-block:: sdl-diff
    :caption: dbschema/default.gel

      module default {
    +   abstract type Timestamped {
    +     required created_at: datetime {
    +       default := datetime_of_statement();
    +     };
    +     required updated_at: datetime {
    +       default := datetime_of_statement();
    +     };
    +   }
    +
    -   type Deck {
    +   type Deck extending Timestamped {
          required name: str;
          description: str;

          cards := (
            select .<deck[is Card]
            order by .order
          );
        };

    -   type Card {
    +   type Card extending Timestamped {
          required order: int64;
          required front: str;
          required back: str;

          required deck: Deck;
        }
      }

.. edb:split-section::

  If you have ``fastapi dev`` still running, the schema will automatically be updated, no manual migrations are needed. Once the schema is updated, the model generation tool will also be run, and you can see the changes in the ``models`` module. Since you don't have historical data for when these objects were actually created or modified, the migration will fall back to the default values set in the ``Timestamped`` type.

  Update the ``get_decks`` query to sort the decks by ``updated_at`` in descending order.

  .. code-block:: python-diff
    :caption: main.py

      @app.get("/decks")
      async def get_decks():
          db = g.client
    -     return await db.query(Deck.select("*", cards=True))
    +     return await db.query(Deck.select("*", cards=True).order_by(updated_at="desc"))
