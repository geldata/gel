.. _gel-python-orm:

=====================
ORM and Query Builder
=====================

.. py:currentmodule:: gel

The Pydantic models produced by :gelcmd:`generate py/models` open up the ORM functionality. The models provide a Pythonic way of creating and updating the Gel data. 

The main ORM mechanism for reflecting the changes from Python to Gel is via ``.sync()`` client method. One or more objects can be passes to ``.sync()`` as arguments and the method will atomically reflect the data from those objects to the database. The first thing that ``.sync()`` does is determining the order of operations based on how the objects are linked to each other and which links are required. Typically new objects are created first and then any necessary update operations are performed. After the changes have been reflected all of the affected objects will be re-fetched to make sure they are up-to-date. Re-fetching populates ``id`` for new objects as well as computed or default values for model fields.

Operations Dependency
=====================

When figuring out the order of operations we recursively traverse all the links. This means that complex nested structures can be passed into ``.sync()`` by simply passing the root object. All of the objects linked to that root will also be reflected into the database.

The main goal of ordering operations in a certain way is to ensure data integrity. However, knowing which operations depend on which other operations also allows us to batch some of them (e.g. batch inserting a bunch of new objects in a single command).

We also keep track of which values were modified in Python, and so ``.sync()`` only updates values that were modified.


Synching Properties
===================

When synching fields that reflect Gel schema properties all values specified in Python are passed to Gel by ``.sync()``. This is done regardless of whether the object in question already exists and needs to be updated or is a new object to be inserted. It is possible to omit some fields by either never providing a value or using ``del obj.field_name`` to *unset* an existing value. Unset Python fields will take the default value when inserting new objects into Gel. On the other hand, when updating an existing object no change will be made to unset fields.

.. note::

    Unset field is a field that was never given a value in Python. This is different from a field with a value ``None``, which is reflected as an ``{}`` in Gel.

After all the properties have been written to the Gel database, all of the objects processed by ``.sync()`` will re-fetch all of their properties to capture the changes, default values, computed properties, rewrites, etc.

See the :ref:`gel-python-orm-multi` section below for additional details on how multi properties are handled by ``.sync()``.

Synching Links
==============

When synching fields that reflect Gel schema links all values specified in Python are passed to Gel by ``.sync()``. Since link values are objects in their own right, they will be created or updated based on the overall order of operations. Just as for properties it is possible to omit some fields by either never providing a value or using ``del obj.field_name`` to *unset* an existing value. Unset Python fields will take the default value when inserting new objects into Gel. On the other hand, when updating an existing object no change will be made to unset fields.

After all the links have been written to the Gel database, all of the objects processed by ``.sync()`` will re-fetch only the links that were *set* (with some value or ``None``). Links that were *unset* will not be populated by the ``.sync()``.

See the :ref:`gel-python-orm-multi` section below for additional details on how multi links are handled by ``.sync()``.


Synching Link Properties
========================

A new link can be added (by assignment or by ``.add()``) using an *unbound* (i.e. not used in any link field) ``.link()`` object. In that case the link properties are specified by the ``.link()`` wrapper. Any unspecified link property is *unset* and they will take their default values when synched. 

When an existing link is added to a new Python object (by assignment or by ``.add()``) all of its ``__linkprops__`` (if there are any) are *unset*. They need to be modified explicitly via ``__linkprops__`` if needed. All explicitly specified values will be sent to Gel by ``.sync()``. *Unset* link properties on new links will take their default values.

It is possible to update the link properties on existing links. The links must have been fetched earlier in order for this to work. If the link target was never modified, but instead ``__linkprops__`` were used to modify the link properties, the ``.sync()`` method will write those changes to the link properties in Gel.

Overall the expectation for ``.sync()`` w.r.t. link properties is that any value that's present in Python will be written to the Gel database. Unset values are valid only for new links as defaults.

After all the links have been written to the Gel database, ``.sync()`` will re-fetch the affcted links. When re-fetching any link that has link properties, all of the link properties are also automatically re-fetched.

.. _gel-python-orm-multi:

Multi Fields
============

Multi properties or links support two different ways of being modified in Python. The first way is by assigning a list of valid values. Once these fields are synched, the value is assigned as a whole. This mechanism is used for new objects or for replacing values of multi links or properties in existing objects.

It is possible to fetch a subset of values for a given multi link or property. In this case using ``.add()``, ``.remove()``, and ``.clear()`` methods allows you to modify the fetched values. When these modified values are synched, the driver will be able to tell that the corresponding multi link or property should be updated using ``+=`` and ``-=`` instead of being fully replaced. When these updates are made, values that have not been fetched cannot be affected (and thus cannot be removed by either ``.remove()`` or ``clear()``).

When re-fetching the values that were partially fetched, only the values already present in the field in Python will be re-fetched. This is to avoid overfetching since multi links or properties can have quite a few items in them.
