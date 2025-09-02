.. _ref_quickstart_fastapi_working:

=====================
Working with the data
=====================

In this section, you will update the existing FastAPI application to use |Gel| to store and query data, instead of a JSON file. Having a working application with mock data allows you to focus on learning how |Gel| works, without getting bogged down by the details of the application.

A state of the art data layer
=============================

.. edb:split-section::

  Gel is a modern data layer for Python. It is designed to be easy to use, and to be able to handle complex queries and data transformations. One of the key tools that Gel provides is a best-in-class code generator that reflects your Gel schema into Pydantic-compatible models. Our models and query generation tools are fully type-safe.

  Before we get started, let's reflect the current schema into these Gel-powered models which we will use to interact with the database.

  .. code-block:: bash

    $ uvx gel generate py/models

Bulk importing of data
======================

.. edb:split-section::

  Gel has a built-in FastAPI integration that we can use to leverage FastAPI and Gel idioms together. We will import the ``gel.fastapi`` package and use the ``gelify`` function to create a Gel FastAPI instance. The ``gelify`` integration will automatically run the model generation tool anytime the schema is updated.

  .. code-block:: python-diff
    :caption: main.py

      from fastapi import FastAPI, HTTPException
      from pydantic import BaseModel
    - import json
    - from pathlib import Path
    + import gel.fastapi
    + from .models import Deck, Card

      app = FastAPI(title="Flashcards API")
    + g = gel.fastapi.gelify(app)
    +
      # Pydantic models
      class CardBase(BaseModel):
          front: str
          back: str

    - class Card(CardBase):
    -     id: str
    -     id: UUID
    -
      class DeckCreate(DeckBase):
          name: str
          description: str | None = None
          cards: list[CardBase]

    - class Deck(DeckBase):
    -     id: str
    -     id: UUID
    -     cards: List[Card]
    -
    - DATA_DIR = Path(__file__).parent / "data"
    - DECKS_FILE = DATA_DIR / "decks.json"


.. edb:split-section::

   Next, update the deck import operation to use |Gel| to create the deck and cards. We will use the models we generated in the previous section to create the deck and cards from the incoming body model. A single ``save`` call will create the deck and cards, and the ``Deck`` model will automatically create the links for us.

   .. note::

      Notice the ``{ ** }`` in the query. This is a shorthand for selecting all fields of the object. It's useful when you want to return the entire object without specifying each field. In our case, we want to return the entire deck object with all the nested fields.

   .. code-block:: python-diff
    :caption: main.py

      from fastapi import FastAPI, HTTPException
      from pydantic import BaseModel
      import gel.fastapi
      from .models import Deck, Card

      app = FastAPI(title="Flashcards API")
      g = gel.fastapi.gelify(app)

      # Pydantic models
      class CardBase(BaseModel):
          front: str
          back: str

      class DeckCreate(DeckBase):
          name: str
          description: str | None = None
          cards: list[CardBase]

    - DATA_DIR.mkdir(exist_ok=True)
    - if not DECKS_FILE.exists():
    -     DECKS_FILE.write_text("[]")

    - def read_decks() -> List[Deck]:
    -     content = DECKS_FILE.read_text()
    -     data = json.loads(content)
    -     return [Deck(**deck) for deck in data]
    -
    - def write_decks(decks: List[Deck]) -> None:
    -     data = [deck.model_dump() for deck in decks]
    -     DECKS_FILE.write_text(json.dumps(data, indent=2))

      @app.post("/decks/import", response_model=Deck)
      async def import_deck(deck: DeckCreate):
    -     decks = read_decks()
    +     db = g.client
          new_cards = [Card(front=card.front, back=card.back, order=i) for i, card in enumerate(deck.cards)]
    -     new_deck = Deck(
    -         id=str(uuid.uuid4()),
    -         name=deck.name,
    -         description=deck.description,
    -         cards=new_cards
    -     )
    +     new_deck = Deck(name=deck.name, description=deck.description, cards=new_cards)
    -     decks.append(new_deck)
    -     write_decks(decks)
    +     await db.save(new_deck)
          return new_deck


Updating data
=============

.. edb:split-section::

  Next, update the deck operations. The update operation needs to handle partial updates of name and description. The generated models provide a number of useful variant classes, and we'll use the ``Partial`` class to handle the partial updates. We check to see if the name or description is provided, and if so, we update the deck with the new values.

  .. code-block:: python-diff
    :caption: main.py

      @app.put("/decks/{deck_id}", response_model=Deck)
      async def update_deck(deck_id: UUID, deck_update: Deck.__variants__.Partial):
    -     decks = read_decks()
    +     db = g.client
    -     deck = next((deck for deck in decks if deck.id == deck_id), None)
    +     deck = await db.query_single(Deck.filter(id=deck_id))
          if not deck:
              raise HTTPException(status_code=404, detail="Deck not found")

    +     if deck_update.name is not None:
    -     deck.name = deck_update.name
    +         deck.name = deck_update.name
    +     if deck_update.description is not None:
    -     deck.description = deck_update.description
    +         deck.description = deck_update.description
    -     write_decks(decks)
    +     await db.save(deck)
          return deck


Adding linked data
==================

.. edb:split-section::

  Now, update the add card operation to use |Gel|. This operation will insert a new ``Card`` object and update the ``Deck.cards`` set to include the new ``Card`` object. Notice that the ``order`` property is set by selecting the maximum ``order`` property of this ``Deck.cards`` set and incrementing it by 1.

  .. code-block:: python-diff
      :caption: main.py

        @app.post("/decks/{deck_id}/cards")
        async def add_card(deck_id: UUID, card: CardCreate):
      -     decks = read_decks()
      +     db = g.client
      -     deck = next((deck for deck in decks if deck.id == deck_id), None)
      +     deck = await db.query_single(Deck.filter(id=deck_id))
            if not deck:
                raise HTTPException(status_code=404, detail="Deck not found")

      -     new_card = Card(id=str(uuid.uuid4()), **card.model_dump())
      +     new_card = Card(front=card.front, back=card.back, order=len(deck.cards))
            deck.cards.append(new_card)
      -     write_decks(decks)
      +     await db.save(deck)
            return new_card


Deleting linked data
====================

.. edb:split-section::

  As the next step, update the card deletion operation to use |Gel| to remove a card from a deck:

  .. code-block:: python-diff
    :caption: main.py

      @app.delete("/cards/{card_id}")
      async def delete_card(card_id: str):
    -     decks = read_decks()
    +     db = g.client
    -     deck = next((deck for deck in decks if deck.id == deck_id), None)
    +     deck = await db.query_single(Deck.filter(id=deck_id))
          if not deck:
              raise HTTPException(status_code=404, detail="Deck not found")

    -     deck.cards = [card for card in deck.cards if card.id != card_id]
    +     for card in deck.cards:
    +         if card.id == card_id:
    +             deck.cards.remove(card)
    +             break
    -     write_decks(decks)
    +     await db.save(deck)
          return {"message": "Card deleted"}

Querying data
=============

.. edb:split-section::

  Finally, update the query endpoints to fetch data from |Gel|:

  .. code-block:: python-diff
    :caption: main.py

      @app.get("/decks")
      async def get_decks():
    -     return read_decks()
    +     db = g.client
    +     return await db.query(Deck.select("*", cards=True))

      @app.get("/decks/{deck_id}")
      async def get_deck(deck_id: UUID):
    -     decks = read_decks()
    +     db = g.client
    -     deck = next((deck for deck in decks if deck.id == deck_id), None)
    +     deck = await db.query_single(Deck.filter(id=deck_id))
          if not deck:
              raise HTTPException(status_code=404, detail=f"Deck with id {deck_id} not found")
          return deck

.. edb:split-section::

  You can now run your FastAPI application with:

  .. code-block:: sh

    $ uv run fastapi dev

.. edb:split-section::

  The API documentation will be available at http://localhost:8000/docs. You can use this interface to test your endpoints and import the sample flashcard deck.

  .. image:: images/flashcards-api.png
