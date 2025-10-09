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

# Reflected Pydantic Models

The command `gel generate py/models` creates models that can be used by the Gel query builder. These models are also Pydantic models and so they have access to various Pydantic features like `model_dump()` or `model_validate()`, etc.

Gel models also provide special attributes that can be used to construct new model types that are compatible with the query builder, but may have different fields exposed.

There are several model templates in `__shapes__`:

* `Base` is a model that is associated with a specific Gel type, but has no other features. It is a good base type to use for full customization.
* `NoId`, `OptionalId`, and `RequiredId` are models that have different expectations for the `id` when validating data. Used as a template for model composition.
* `RequiredProps` has only the fields corresponding to the required properties.
* `PropsAsOptional` has only fields corresponding to properties and makes them all optional.
* `PropsAsDeclared` has only fields corresponding to properties. They are required or optional based on the schema.
* `RequiredLinks` has only the fields corresponding to the required links.
* `LinksAsOptional` has only fields corresponding to links and makes them all optional.
* `LinksAsDeclared` has only fields corresponding to links. They are required or optional based on the schema.

Compose a model that has only the Character `id` and `first_name`:
```python
from models import default

class PropsChar(
    default.Character.__shapes__.RequiredId,
    default.Character.__shapes__.PropsAsDeclared,
):
    pass
```

You can also refer to individual field definitions by using `__defs__`:
```python
from models import default

class PropsChar(
    default.Character.__shapes__.RequiredId,
):
    first_name: default.Character.__defs__.first_name
```

Here's a custom model without `id`, exposing `fist_name` and `equipped` field:
```python
from models import default

class EquippedChar(
    default.Character.__shapes__.NoId,
    default.Character.__shapes__.PropsAsDeclared,
):
    equipped: default.Character.__defs__.equipped
```