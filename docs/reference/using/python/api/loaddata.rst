.. _gel-python-loaddata:

============
Data Loading
============

.. py:currentmodule:: gel

One of the first things that a project often needs is to load some data into the database. When you're just getting started, this data often comes in the form of JSON or CSV files.


Complete JSON
=============

The simplest scenario is when the data to be loaded is already structured in the way you want and is also complete and has no duplicates. So it would be something like this:

.. lint-off

.. code-block:: json
  :caption: teams.json

  [
    {
      "name": "The Dreamweavers",
      "members": [
        {
          "name": "Alice Johnson",
          "email": "alice.johnson@gel.com",
          "active": true,
          "dob": "1990-03-15",
          "about": "Cloud castle architect building dreams from cotton candy and stardust",
          "custom_settings": {
            "font_size": 14,
            "color_scheme": "dark"
          }
        },
        {
          "name": "Bob Smith",
          "email": "bob.smith@gel.com",
          "active": true,
          "dob": "1985-07-22",
          "about": "Master of turning coffee into code and pizza into solutions",
          "custom_settings": {
            "color_scheme": "light"
          }
        },
        {
          "name": "Carol Davis",
          "email": "carol.davis@gel.com",
          "active": false,
          "dob": "1992-11-08",
          "about": "Color wizard painting with rainbows and making buttons dance"
        },
        {
          "name": "David Wilson",
          "email": "david.wilson@gel.com",
          "active": true,
          "about": "Digital shepherd herding servers and keeping the internet from getting lost"
        }
      ]
    },
    {
      "name": "The Storytellers",
      "members": [
        {
          "name": "Emma Brown",
          "email": "emma.brown@gel.com",
          "active": true,
          "dob": "1988-05-12",
          "about": "Social media fairy sprinkling engagement dust and making posts viral",
          "custom_settings": {
            "font_size": 16,
            "color_scheme": "sparkly"
          }
        },
        {
          "name": "Frank Miller",
          "email": "frank.miller@gel.com",
          "active": true,
          "dob": "1983-09-30",
          "about": "Word wizard turning boring facts into captivating magical tales"
        },
        {
          "name": "Grace Taylor",
          "email": "grace.taylor@gel.com",
          "active": true,
          "about": "Search engine whisperer knowing secret handshakes to make websites famous"
        }
      ]
    },
    {
      "name": "The Treasure Hunters",
      "members": [
        {
          "name": "Henry Anderson",
          "email": "henry.anderson@gel.com",
          "active": true,
          "dob": "1987-01-25",
          "about": "Deal detective finding gold in conversations and turning handshakes into deals",
          "custom_settings": {
            "font_size": 12
          }
        },
        {
          "name": "Iris Martinez",
          "email": "iris.martinez@gel.com",
          "active": true,
          "dob": "1991-12-03",
          "about": "Client whisperer speaking business language and making partnerships bloom",
          "custom_settings": {
            "color_scheme": "dark"
          }
        },
        {
          "name": "Jack Thompson",
          "email": "jack.thompson@gel.com",
          "active": false,
          "about": "Data detective following digital breadcrumbs to solve customer happiness"
        },
        {
          "name": "Kate Rodriguez",
          "email": "kate.rodriguez@gel.com",
          "active": true,
          "dob": "1989-06-18",
          "about": "Partnership pirate sailing business seas looking for collaboration treasure"
        },
        {
          "name": "Liam Garcia",
          "email": "liam.garcia@gel.com",
          "active": true,
          "about": "Phone whisperer turning cold calls into warm conversations and leads into friends"
        }
      ]
    }
  ]

.. lint-on

The JSON basically contains teams, each team has members, some members have a custom setting object as well. There are no duplicates, all teams are exclusive, so they don't share members. We can model this with the following schema:

.. code-block:: sdl

  module default {
    abstract type Named {
      required name: str {
        delegated constraint exclusive;
      }
    }

    type Team extending Named {
      multi members: User {
        constraint exclusive;
      }
    }

    type User extending Named {
      required email: str {
        constraint exclusive;
      }
      required active: bool;
      dob: cal::local_date;
      about: str;
      custom_settings: CustomSettings {
        # setting are user-specific
        constraint exclusive;
      }
    }

    type CustomSettings {
      font_size: int16;
      color_scheme: str;
    }
  }


We can apply our schema to the Gel database with :gelcmd:`migration create` and :gelcmd:`migrate` commands. After that we can generate Pydantic models with ``gel generate py/models``.

Once the models are in place they can be read and saved to the database with a simple script:

.. code-block:: python

  import json
  import gel
  from models import default


  def object_hook(result):
      # Use unique field names to identify what object
      # is being decoded
      if 'members' in result:
          return default.Team(**result)
      elif 'email' in result:
          return default.User(**result)
      elif 'font_size' in result or 'color_scheme' in result:
          return default.CustomSettings(**result)
      else:
          raise ValueError(f"Unknown object type: {result}")


  db = gel.create_client()
  with open('groups.json', 'rt') as f:
      # We can directly repackage objects as we read them from JSON
      data = json.load(f, object_hook=object_hook)

  # Save all the objecys we just read
  db.save(*data)

We can double check that we actually loaded all the data with a query:

.. lint-off

.. code-block:: bash

  $ gel query 'select Team {id, name, members: {**}}'
  {
    "id": "9bde2ee0-4d00-11f0-ad10-33678e0eb68d",
    "name": "The Dreamweavers",
    "members": [
      {
        "id": "9bdeb5e0-4d00-11f0-ad10-5f500b77b7c9",
        "email": "carol.davis@gel.com",
        "name": "Carol Davis",
        "about": "Color wizard painting with rainbows and making buttons dance",
        "active": false,
        "dob": "1992-11-08",
        "custom_settings": null
      },
      {
        "id": "9bdecd32-4d00-11f0-ad10-07e914df9a3b",
        "email": "david.wilson@gel.com",
        "name": "David Wilson",
        "about": "Digital shepherd herding servers and keeping the internet from getting lost",
        "active": true,
        "dob": null,
        "custom_settings": null
      },
      {
        "id": "9bde58f2-4d00-11f0-ad10-9f8507b49e39",
        "email": "alice.johnson@gel.com",
        "name": "Alice Johnson",
        "about": "Cloud castle architect building dreams from cotton candy and stardust",
        "active": true,
        "dob": "1990-03-15",
        "custom_settings": {"id": "9bde7aee-4d00-11f0-ad10-6fcdc7e5c932", "color_scheme": "dark", "font_size": 14}
      },
  ...

.. lint-on


JSON with duplicates
====================

The more likely scenario is that the JSON data exported from elsewhere potentially has duplicates (because some records are linked from multiple sources). So consider some data similar to the previous example, but with a few key differences. This time each user can be a member in more than one team. Also instead of ``"custom_settings"`` there are some themes that user can pick from:

.. lint-off

.. code-block:: json
  :caption: factions.json

  [
    {
      "name": "The Code Wizards",
      "members": [
        {
          "name": "Alice Johnson",
          "email": "alice.johnson@gel.com",
          "active": true,
          "dob": "1990-03-15",
          "about": "Cloud castle architect building dreams from cotton candy and stardust",
          "theme": {
            "name": "Stardust Serenity",
            "font_size": 16,
            "vibe": "ethereal and dreamy"
          }
        },
        {
          "name": "Bob Smith",
          "email": "bob.smith@gel.com",
          "active": true,
          "dob": "1985-07-22",
          "about": "Master of turning coffee into code and pizza into solutions",
          "theme": {
            "name": "Caffeine Chaos",
            "vibe": "energetic and slightly chaotic"
          }
        },
        {
          "name": "David Wilson",
          "email": "david.wilson@gel.com",
          "active": true,
          "about": "Digital shepherd herding servers and keeping the internet from getting lost"
        },
        {
          "name": "Jack Thompson",
          "email": "jack.thompson@gel.com",
          "active": false,
          "about": "Data detective following digital breadcrumbs to solve customer happiness",
          "theme": {
            "name": "Mystery Matrix",
            "font_size": 14,
            "vibe": "detective noir with a digital twist"
          }
        }
      ]
    },
    {
      "name": "The Creative Dreamers",
      "members": [
        {
          "name": "Alice Johnson",
          "email": "alice.johnson@gel.com",
          "active": true,
          "dob": "1990-03-15",
          "about": "Cloud castle architect building dreams from cotton candy and stardust",
          "theme": {
            "name": "Stardust Serenity",
            "font_size": 16,
            "vibe": "ethereal and dreamy"
          }
        },
        {
          "name": "Carol Davis",
          "email": "carol.davis@gel.com",
          "active": false,
          "dob": "1992-11-08",
          "about": "Color wizard painting with rainbows and making buttons dance",
          "theme": {
            "name": "Rainbow Rhapsody",
            "font_size": 18,
            "vibe": "vibrant and playful"
          }
        },
        {
          "name": "Emma Brown",
          "email": "emma.brown@gel.com",
          "active": true,
          "dob": "1988-05-12",
          "about": "Social media fairy sprinkling engagement dust and making posts viral"
        },
        {
          "name": "Frank Miller",
          "email": "frank.miller@gel.com",
          "active": true,
          "dob": "1983-09-30",
          "about": "Word wizard turning boring facts into captivating magical tales"
        }
      ]
    },
    {
      "name": "The Business Hunters",
      "members": [
        {
          "name": "Henry Anderson",
          "email": "henry.anderson@gel.com",
          "active": true,
          "dob": "1987-01-25",
          "about": "Deal detective finding gold in conversations and turning handshakes into deals"
        },
        {
          "name": "Iris Martinez",
          "email": "iris.martinez@gel.com",
          "active": true,
          "dob": "1991-12-03",
          "about": "Client whisperer speaking business language and making partnerships bloom"
        },
        {
          "name": "Kate Rodriguez",
          "email": "kate.rodriguez@gel.com",
          "active": true,
          "dob": "1989-06-18",
          "about": "Partnership pirate sailing business seas looking for collaboration treasure"
        },
        {
          "name": "Liam Garcia",
          "email": "liam.garcia@gel.com",
          "active": true,
          "about": "Phone whisperer turning cold calls into warm conversations and leads into friends"
        },
        {
          "name": "Bob Smith",
          "email": "bob.smith@gel.com",
          "active": true,
          "dob": "1985-07-22",
          "about": "Master of turning coffee into code and pizza into solutions",
          "theme": {
            "name": "Caffeine Chaos",
            "vibe": "energetic and slightly chaotic"
          }
        }
      ]
    },
    {
      "name": "The Digital Mystics",
      "members": [
        {
          "name": "Grace Taylor",
          "email": "grace.taylor@gel.com",
          "active": true,
          "about": "Search engine whisperer knowing secret handshakes to make websites famous"
        },
        {
          "name": "David Wilson",
          "email": "david.wilson@gel.com",
          "active": true,
          "about": "Digital shepherd herding servers and keeping the internet from getting lost"
        },
        {
          "name": "Jack Thompson",
          "email": "jack.thompson@gel.com",
          "active": false,
          "about": "Data detective following digital breadcrumbs to solve customer happiness",
          "theme": {
            "name": "Mystery Matrix",
            "font_size": 14,
            "vibe": "detective noir with a digital twist"
          }
        },
        {
          "name": "Emma Brown",
          "email": "emma.brown@gel.com",
          "active": true,
          "dob": "1988-05-12",
          "about": "Social media fairy sprinkling engagement dust and making posts viral"
        },
        {
          "name": "Frank Miller",
          "email": "frank.miller@gel.com",
          "active": true,
          "dob": "1983-09-30",
          "about": "Word wizard turning boring facts into captivating magical tales"
        }
      ]
    }
  ]

.. lint-on

This JSON dump essentially has a lot of redundant information as the objects are represented in full whenever they are included in the data. The schema is pretty similar to the previous example, though:

.. code-block:: sdl

  module default {
    abstract type Named {
      required name: str {
        delegated constraint exclusive;
      }
    }

    type Team extending Named {
      multi members: User;
    }

    type User extending Named {
      required email: str {
        constraint exclusive;
      }
      required active: bool;
      dob: cal::local_date;
      about: str;
      theme: Theme;
    }

    type Theme extending Named {
      font_size: int16;
      vibe: str;
    }
  }

We can apply our schema to the Gel database with :gelcmd:`migration create` and :gelcmd:`migrate` commands. After that we can generate Pydantic models with ``gel generate py/models``.

Once the models are in place they can be read and save to the database. However, our script will have to keep track of object duplicates:

.. code-block:: python

  import json
  import gel
  from models import default


  # We're going to need some dicts to keep track of existing objects
  teams = dict()
  users = dict()
  themes = dict()


  def object_hook(result):
      # For each record we check our cache to see if it already exists
      if 'members' in result:
          team = teams.get(result['name'])
          if team is None:
              team = default.Team(**result)
              teams[team.name] = team
          return team
      elif 'email' in result:
          user = users.get(result['name'])
          if user is None:
              user = default.User(**result)
              users[user.name] = user
          return user
      elif 'font_size' in result or 'vibe' in result:
          theme = themes.get(result['name'])
          if theme is None:
              theme = default.Theme(**result)
              themes[theme.name] = theme
          return theme
      else:
          raise ValueError(f"Unknown object type: {result}")


  db = gel.create_client()
  with open('factions.json', 'rt') as f:
      data = json.load(f, object_hook=object_hook)

  db.save(*data)

We can double check that we actually loaded all the data with a query:

.. lint-off

.. code-block:: bash

  $ gel query 'select Team {id, name, members: {**}}'
  {
    "id": "935d51d4-4d09-11f0-ae4a-43003ed713c3",
    "name": "The Code Wizards",
    "members": [
      {
        "id": "935de1da-4d09-11f0-ae4a-6bdf4fa1fe9a",
        "email": "david.wilson@gel.com",
        "name": "David Wilson",
        "about": "Digital shepherd herding servers and keeping the internet from getting lost",
        "active": true,
        "dob": null,
        "theme": null
      },
      {
        "id": "935d7c7c-4d09-11f0-ae4a-97e585244a22",
        "email": "alice.johnson@gel.com",
        "name": "Alice Johnson",
        "about": "Cloud castle architect building dreams from cotton candy and stardust",
        "active": true,
        "dob": "1990-03-15",
        "theme": {"name": "Stardust Serenity", "id": "935d9dec-4d09-11f0-ae4a-a7903cb59029", "font_size": 16, "vibe": "ethereal and dreamy"}
      },
      {
        "id": "935db62e-4d09-11f0-ae4a-4787719b4d7d",
        "email": "bob.smith@gel.com",
        "name": "Bob Smith",
        "about": "Master of turning coffee into code and pizza into solutions",
        "active": true,
        "dob": "1985-07-22",
        "theme": {"name": "Caffeine Chaos", "id": "935dc9e8-4d09-11f0-ae4a-8376db97dfef", "font_size": null, "vibe": "energetic and slightly chaotic"}
      },
  ...

.. lint-on


CSV or JSON with PKs
====================

If you're dealing with CSV files, you probably don't have any nested data there, instead records reference each other by primary keys. Same processing would apply to JSON data linked by primary keys instead of nesting whole objects. So we'll use JSON in our example.

.. lint-off

.. tabs::

  .. code-tab:: json
    :caption: teams.json

    [
      {
        "id": 1,
        "name": "The Code Wizards",
        "members": ["alice.johnson@gel.com", "bob.smith@gel.com", "david.wilson@gel.com", "jack.thompson@gel.com"]
      },
      {
        "id": 2,
        "name": "The Creative Dreamers",
        "members": ["alice.johnson@gel.com", "carol.davis@gel.com", "emma.brown@gel.com", "frank.miller@gel.com"]
      },
      {
        "id": 3,
        "name": "The Business Hunters",
        "members": ["henry.anderson@gel.com", "iris.martinez@gel.com", "kate.rodriguez@gel.com", "liam.garcia@gel.com", "bob.smith@gel.com"]
      },
      {
        "id": 4,
        "name": "The Digital Mystics",
        "members": ["grace.taylor@gel.com", "david.wilson@gel.com", "jack.thompson@gel.com", "emma.brown@gel.com", "frank.miller@gel.com"]
      }
    ]

  .. code-tab:: json
    :caption: users.json

    [
      {
        "name": "Alice Johnson",
        "email": "alice.johnson@gel.com",
        "active": true,
        "dob": "1990-03-15",
        "about": "Cloud castle architect building dreams from cotton candy and stardust",
        "theme_id": 1000
      },
      {
        "name": "Bob Smith",
        "email": "bob.smith@gel.com",
        "active": true,
        "dob": "1985-07-22",
        "about": "Master of turning coffee into code and pizza into solutions",
        "theme_id": 1001
      },
      {
        "name": "David Wilson",
        "email": "david.wilson@gel.com",
        "active": true,
        "about": "Digital shepherd herding servers and keeping the internet from getting lost"
      },
      {
        "name": "Jack Thompson",
        "email": "jack.thompson@gel.com",
        "active": false,
        "about": "Data detective following digital breadcrumbs to solve customer happiness",
        "theme_id": 1002
      },
      {
        "name": "Carol Davis",
        "email": "carol.davis@gel.com",
        "active": false,
        "dob": "1992-11-08",
        "about": "Color wizard painting with rainbows and making buttons dance",
        "theme_id": 1003
      },
      {
        "name": "Emma Brown",
        "email": "emma.brown@gel.com",
        "active": true,
        "dob": "1988-05-12",
        "about": "Social media fairy sprinkling engagement dust and making posts viral"
      },
      {
        "name": "Frank Miller",
        "email": "frank.miller@gel.com",
        "active": true,
        "dob": "1983-09-30",
        "about": "Word wizard turning boring facts into captivating magical tales"
      },
      {
        "name": "Henry Anderson",
        "email": "henry.anderson@gel.com",
        "active": true,
        "dob": "1987-01-25",
        "about": "Deal detective finding gold in conversations and turning handshakes into deals"
      },
      {
        "name": "Iris Martinez",
        "email": "iris.martinez@gel.com",
        "active": true,
        "dob": "1991-12-03",
        "about": "Client whisperer speaking business language and making partnerships bloom"
      },
      {
        "name": "Kate Rodriguez",
        "email": "kate.rodriguez@gel.com",
        "active": true,
        "dob": "1989-06-18",
        "about": "Partnership pirate sailing business seas looking for collaboration treasure"
      },
      {
        "name": "Liam Garcia",
        "email": "liam.garcia@gel.com",
        "active": true,
        "about": "Phone whisperer turning cold calls into warm conversations and leads into friends"
      },
      {
        "name": "Grace Taylor",
        "email": "grace.taylor@gel.com",
        "active": true,
        "about": "Search engine whisperer knowing secret handshakes to make websites famous"
      }
    ]

  .. code-tab:: json
    :caption: themes.json

    [
      {
        "id": 1000,
        "name": "Stardust Serenity",
        "font_size": 16,
        "vibe": "ethereal and dreamy"
      },
      {
        "id": 1001,
        "name": "Caffeine Chaos",
        "vibe": "energetic and slightly chaotic"
      },
      {
        "id": 1002,
        "name": "Mystery Matrix",
        "font_size": 14,
        "vibe": "detective noir with a digital twist"
      },
      {
        "id": 1003,
        "name": "Rainbow Rhapsody",
        "font_size": 18,
        "vibe": "vibrant and playful"
      }
    ]

.. lint-on

This is the same data as in the previous example, but without all the duplicates. Themes are referenced by ``id``. Users instead rely on the unique emails as the primary key. We can still use the same schema:

.. code-block:: sdl

  module default {
    abstract type Named {
      required name: str {
        delegated constraint exclusive;
      }
    }

    type Team extending Named {
      multi members: User;
    }

    type User extending Named {
      required email: str {
        constraint exclusive;
      }
      required active: bool;
      dob: cal::local_date;
      about: str;
      theme: Theme;
    }

    type Theme extending Named {
      font_size: int16;
      vibe: str;
    }
  }

We can apply our schema to the Gel database with :gelcmd:`migration create` and :gelcmd:`migrate` commands. After that we can generate Pydantic models with ``gel generate py/models``.

Once the models are in place they can be read and saved to the database. We could load all the files and compose the overall object structure and save them all at once, but in general, this approach may not be possible if we're dealing with cross-linked tables. Instead we'll load them one table at a time, ignoring links and then we'll do a separate pass to just link everything together:

.. code-block:: python

  import json
  import gel
  from models import default


  db = gel.create_client()
  # We're going to use dicts to load the data
  teams = dict()
  users = dict()
  themes = dict()


  def team_hook(result):
      team = teams.get(result['id'])
      if team is None:
          # ignore members and the original id when creating a team
          orig_id = result.pop('id')
          del result['members']
          team = default.Team(**result)
          teams[orig_id] = team

      return team


  with open('teams.json', 'rt') as f:
      data = json.load(f, object_hook=team_hook)
      db.save(*data)


  def user_hook(result):
      user = users.get(result['email'])
      if user is None:
          # ignore theme_id when creating a team
          result.pop('theme_id', None)
          user = default.User(**result)
          users[user.email] = user
      return user


  with open('users.json', 'rt') as f:
      data = json.load(f, object_hook=user_hook)
      db.save(*data)


  def theme_hook(result):
      theme = themes.get(result['id'])
      if theme is None:
          # ignore the original id when creating a team
          orig_id = result.pop('id')
          theme = default.Theme(**result)
          themes[orig_id] = theme
      return theme


  with open('themes.json', 'rt') as f:
      data = json.load(f, object_hook=theme_hook)
      db.save(*data)


  # Now that we've saved the base objects, we can load the relationships
  def team_links(result):
      team = teams[result['id']]
      team.members.extend([
          users[m] for m in result['members']
      ])
      return team


  with open('teams.json', 'rt') as f:
      data = json.load(f, object_hook=team_links)
      db.save(*data)


  def user_links(result):
      user = users[result['email']]
      theme_id = result.get('theme_id')
      if theme_id is not None:
          user.theme = themes[theme_id]
      return user


  with open('users.json', 'rt') as f:
      data = json.load(f, object_hook=user_links)
      db.save(*data)

This script is a bit verbose, but it serves as an illustration of the process of loading table data when all the cross-references make it unsafe trying to link it all in one step.

We can double check that we actually loaded all the data with a query:

.. lint-off

.. code-block:: bash

  $ gel query 'select Team {id, name, members: {**}}'
  {
    "id": "eb24cc7c-4d12-11f0-b734-8fe80e42e7df",
    "name": "The Code Wizards",
    "members": [
      {
        "id": "eb28c700-4d12-11f0-b734-2b0e1e4f3fb8",
        "email": "david.wilson@gel.com",
        "name": "David Wilson",
        "about": "Digital shepherd herding servers and keeping the internet from getting lost",
        "active": true,
        "dob": null,
        "theme": null
      },
      {
        "id": "eb281b70-4d12-11f0-b734-fba98d2fdb96",
        "email": "alice.johnson@gel.com",
        "name": "Alice Johnson",
        "about": "Cloud castle architect building dreams from cotton candy and stardust",
        "active": true,
        "dob": "1990-03-15",
        "theme": {"name": "Stardust Serenity", "id": "eb2a3266-4d12-11f0-b734-ebdea454964b", "font_size": 16, "vibe": "ethereal and dreamy"}
      },
      {
        "id": "eb2823fe-4d12-11f0-b734-731c199a8975",
        "email": "bob.smith@gel.com",
        "name": "Bob Smith",
        "about": "Master of turning coffee into code and pizza into solutions",
        "active": true,
        "dob": "1985-07-22",
        "theme": {"name": "Caffeine Chaos", "id": "eb2a9e68-4d12-11f0-b734-6b77787a6840", "font_size": null, "vibe": "energetic and slightly chaotic"}
      },
  ...


.. lint-off