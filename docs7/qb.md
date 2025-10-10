# Schema

The schema used in examples. There are only two types representing characters and items for a simple game.
```
module default {
    type Character {
        required first_name: str {
            constraint exclusive;
        }

        link equipped: Item;
        multi link inventory: Item;
    }

    type Item {
        required description: str {
            default := 'Junk';
        }

        rightful_owner: Character {
            constraint exclusive;
        }
    }
}
```

# Setup the client

You can use the default gel client:
```python
import gel
db = gel.create_client()
```

You can also use the async client `gel.create_async_client()`

To access models and the query builder functionality you need to reflect the schema with this command: `gel generate py/models`. Then you can import the schema modules from the `models`. In our case you will need the `default` module where the user defined types are and the `std` built-in module for accessing some of the built-ins in the query builder.
```python
from models import default, std
```

# Create data

## Basic object creation

Use the reflected models to create instances of the objects and then use the `.sync()` method of the client to write the data to the Gel database.
```python
alice = default.Character(first_name='Alice')
db.sync(alice)
```

You can also sync several objects at the same time:
```python
billie = default.Character(first_name='Billie')
cameron = default.Character(first_name='Cameron')
items = [
    default.Item(description='Water Bottle'),
    default.Item(description='Baseball'),
    default.Item(description='Notebook'),
    default.Item(),  # This will default to "Junk"
]
db.sync(billie, cameron, *items)
```

## Nested objects

You can create nested linked objects and sync them all by passing just the root object.
```python
dana = default.Character(
    first_name='Dana',
    inventory=[
        default.Item(description='Pizza'),
        default.Item(description='Cola'),
    ],
)
db.sync(dana)
```

It's also possible to reuse the same Python object if it's referred by different links. Only one copy will be created and the Gel links will end up referring to the same object. It's even OK to have links that loop.
```python
icecream = default.Item(description='Chocolate Ice Cream')
elsa = default.Character(
    first_name='Elsa',
    inventory=[
        icecream,
    ],
    equipped=icecream,
)
icecream.rightful_owner = elsa
db.sync(elsa)
```

## Sync vs save

By default `.sync()` is the preferred method for saving the data from Python to the Gel backend. Not only does it apply the changes in Python objects, but it also re-fetches the model fields in case there are any changes to them that occurred. Only the fields that were set will be re-fetched to prevent over-fetching. This is especially useful if there are some computed fields, since their values may be affected by other fields.

The `.save()` method is a more low-level operation. It will still apply the changes from the Python models to the Gel backend, but it will not re-fetch any data (except the `id` of new objects). This makes it a little faster at the cost of potentially having stale data.

For example:
```python
alice = default.Character(first_name='Alice')
# accessing alice.id will result in AttributeError here
db.save(alice)
print(alice.id)  # the id is populated by save
```

Use `.sync()` method when you need to not only save the model changes, but also to fetch the updated state from the database. This method will populate the new `id` values as well as any server-side defaults in case of creating objects.

In our case this can be seen with the Item example:
```python
junk = default.Item()
assert junk.description != 'Junk'
db.sync(junk)
assert junk.description == 'Junk'
```

## Bulk write

It is better to use `.save()` For writing data to Gel in bulk. This method avoids re-fetching overhead and will attempt to batch similar objects together.

# Read

## Fetch using a simple filter

To read data you would use `.filter()` to construct a query. Then use either `.get()` to fetch exactly one object or a regular `.query()` to fetch an arbitrary number of objects.
```python
q = default.Character.filter(first_name='Dana')
dana = db.get(q)
print(dana.first_name)
everybody = db.query(default.Character)  # no filter
print([c.first_name for c in everybody])
```

## Refer by id

If you happen to know the `id` of an object you can create a Python model using that `id`.
```python
mystery = default.Item(uuid.UUID('ad4d0b64-a2a1-11f0-89be-2f796aa8a032'))
# at this point accessing mystery.description will result in an AttributeError
alice.inventory.add(mystery)
# it's fine to add this as a link however
db.sync(alice)
```

## Specify the shape

If you omit `.select()` in the query-builder, all the properties will be fetched. However, no links will be fetched by default. Using `.select()` allows to fine-tune what gets included and omitted.
```python
dana = db.get(default.Character.select(
    inventory=True,
).filter(first_name='Dana'))
assert {it.description for it in dana.inventory} == {'Pizza', 'Cola'}
```

The above will fetch Dana with `inventory` field populated, but no `first_name` or `equipped` fields (`AttributeError` when accessing unset fields).

The `.select()` accepts `'*'` and `'**'` as splats.

This will fetch Dana with only properties (default behavior when `.select()` is omitted completely):
```python
dana = db.get(default.Character.select('*').filter(first_name='Dana'))
```

This will fetch Dana with all properties and all the links with their properties:
```python
dana = db.get(default.Character.select('**').filter(first_name='Dana'))
assert dana.equipped is None
assert {it.description for it in dana.inventory} == {'Pizza', 'Cola'}
```

You can also specify nested shape expressions to be fetched by using a `lambda`. The argument to the lambda is the object at the current nesting level:
```python
dana = db.get(
    default.Character.select(
        '*',
        equipped=True,
        inventory=lambda char: char.inventory.select(
            '*',
            rightful_owner=lambda item: item.rightful_owner.select(
                name=True,
            )
        )
    ).filter(first_name='Dana')
)
```

## Ad-hoc computed fields

You can add an extra field with some arbitrary expression to the query. In order to do that you need to derive a model type with that field. In the query you can use a `lambda` to provide an arbitrary expression:
```python
class MyChar(default.Character):
    num_items: std.int64
    name_length: std.int64

dana = db.get(MyChar.select(
    '**',
    # use a built-in function count
    num_items=lambda char: std.count(char.inventory),
    # use a built-in function len
    name_length=lambda char: std.len(char.first_name),
).filter(first_name='Dana'))
assert dana.num_items == len(dana.inventory)
assert dana.name_length == 4
```

Gel has many built-in functions. As a rule we reflect them into the `models.std` module. The naming follows the same module structure as the Gel schema. So `std::count` is reflected as `modules.std.count`, etc.

## Filter expressions

Expressions and subqueries can be used in filters with a `lambda`.

Get all characters with the name alphabetically following "C":
```python
chars = db.query(
    default.Character.filter(
        lambda char: char.first_name > 'C'
    )
)
```

Several arguments to the `.filter()` will be combined into a filter expression using logical `and`:
```python
chars = db.query(
    default.Character.filter(
        lambda char: std.ilike(char.first_name, '%li%'),
        lambda char: char.first_name < 'B'
    )
)
```

Logical operators (as well as other keyword operators) can be found in the `models.std` module:
```python
chars = db.query(
    default.Character.filter(
        lambda char: std.or_(
            char.first_name < 'B',
            char.first_name > 'D'
        ),
    )
)
```

Get characters and their inventory, such that the character is the rightful owner of at least one inventory item:
```python
chars = db.query(
    default.Character.select(
        '*',  # get all properties
        inventory=lambda c: c.inventory.select(
            '*',
            rightful_owner=True,
        ),
    ).filter(
        lambda c: std.in_(  # use the EdgeQL `in` set operator
            c, c.inventory.rightful_owner,
            # this is equivalent to:
            # `filter Character in .inventory.rightful_owner`
        )
    )
)
```

## Ordering and pagination

Results can be ordered using `.order_by()`. Also, to fetch only a portion of the available data you can use `.offset()` and `.limit()`.

Just get any one character:
```python
char = db.get(default.Character.limit(1))
```

Get the first character in alphabetic order:
```python
first = db.get(default.Character.order_by(first_name=True).limit(1))
```
or
```python
first = db.get(default.Character.order_by(first_name='asc').limit(1))
```

Get the first character in descending alphabetic order:
```python
last = db.get(default.Character.order_by(first_name='desc').limit(1))
```

Fetch items for a paginated result, 5 items per page, 3rd page:
```python
page_size = 5
cur_page = 3
items = db.query(
    default.Item.order_by(description=True)
                .offset(page_size * (cur_page - 1))
                .limit(page_size)
)
```

# Update

## Update using models

Updating is just re-using an already existing Python model to change some fields and then saving or syncing it again.
```python
alice = default.Character(first_name='Alice')
items = [
    default.Item(description='Water Bottle'),
    default.Item(description='Baseball'),
    default.Item(description='Notebook'),
    default.Item(),  # This will default to "Junk"
]
db.sync(billie, cameron, *items)
db.sync(alice, *items)
# update and sync again
alice.inventory = items
db.sync(alice)
```

You can specify the known `id` as well as the fields that need to be modified. This way the `.sync()` operation will write the modified fields to the object with the specified `id`.
```python
gizmo = default.Item(
    uuid.UUID('ad4d0b64-a2a1-11f0-89be-2f796aa8a032'),
    description='Shiny Updated Gizmo'
)
db.sync(gizmo)
```

## Bulk update

You can perform a bulk update operation without fetching individual models, updating them in Python and then saving them. Instead an update query can be created directly by the query builder. The `.update()` method uses either values directly or `lambda` expressions.

Rename all items descriptions from "Junk" to "Scrap":
```python
db.query(
    default.Item.filter(description='Junk').update(description='Scrap')
)
```

Rename all items descriptions to include the rightful owner:
```python
db.query(
    default.Item.filter(
        lambda item: std.exists(item.rightful_owner)
    ).update(
        description=lambda item:
            item.description +
            '; property of ' +
            item.rightful_owner.first_name
    )
)
```

# Delete

Use the `.filter()` to specify what data you want deleted. Then add `.delete()` at the end of the query in query builder. In Gel `delete` operation normally returns the deleted objects mostly so that you can check their ids if you need.
```python
db.query(
    default.Character.filter(
        first_name='Billie'
    ).delete()
)
```