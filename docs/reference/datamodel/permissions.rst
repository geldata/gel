.. _ref_datamodel_permissions:

.. versionadded:: 7.0

===========
Permissions
===========

.. index:: RBAC, role based access control, capability

*Permissions* are the mechanism for limiting access to the database based on
provided connection credentials.

Each :ref:`role <ref_admin_roles>` has as set of granted permissions.

.. code-block:: edgeql

    create role alice {
        set password := 'wonderland';
        set permissions := {
            sys::perm::data_modifiction,
            default::can_see_secrets
        };
    };

Permissions are either :ref:`built-in <ref_datamodel_permissions_built_in>` or
:ref:`defined in schema <ref_datamodel_permissions_custom>`.

Some language features or functions require current role to have certain
permissions. For example, to use ``insert``, ``update`` or ``delete``, current
role is required to have ``sys::perm::data_modification``.

Additionally, permissions of current role can be accessed via
:ref:`global variables<ref_datamodel_globals>` of the same name:

.. code-block:: edgeql

    select global sys::perm::data_modification;


Note that roles are instance-wide object, which means that they exist
independent of branches and their schemas. This means that role's permissions
apply to all branches.


Superuser roles
---------------

Roles that are qualified as *superuser* are implicitly granted all permissions.

Some commands are currently limited to *superuser* roles only. These include
commands to manage branches, extensions and roles.


Built-in permissions
====================

.. _ref_datamodel_permissions_built_in:

:eql:synopsis:`sys::perm::data_modification`
    Required for using ``insert``, ``update`` or ``delete`` statements.

:eql:synopsis:`sys::perm::ddl`
    Required for modification of schema. This includes applying migrations,
    and issuing bare DDL commands (e.g. ``create type Post;``).

    It does not include global instance commands, such as ``create branch``
    or ``create role``. These are only allowed to *superuser* roles.

:eql:synopsis:`sys::perm::branch_config`
    Required for issuing ``configure current branch``.

:eql:synopsis:`sys::perm::sql_session_config`
    Required for issuing ``SET`` and ``RESET`` SQL commands.

:eql:synopsis:`sys::perm::analyze`
    Required for issuing ``analyze ...`` queries.

:eql:synopsis:`sys::perm::query_stats_read`
    Required for reading ``sys::QueryStats``.

:eql:synopsis:`sys::perm::approximate_count`
    Required for accessing ``sys::approximate_count()``.


:eql:synopsis:`cfg::perm::configure_timeout`
    Required for setting various timeouts, for example
    ``session_idle_transaction_timeout`` and ``query_execution_timeout``.

:eql:synopsis:`cfg::perm::configure_apply_access_policies`
    Required for disabling access policies.

:eql:synopsis:`cfg::perm::configure_allow_user_specified_id`
    Required for setting ``allow_user_specified_id``.


:eql:synopsis:`std::net::perm::http_write`
    Required for issuing HTTP requests.

:eql:synopsis:`std::net::perm::http_read`
    Required for reading status of issued HTTP requests and responses.


Permissions for :ref:`auth <ref_guide_auth>` extension:

:eql:synopsis:`ext::auth::perm::auth_read`

:eql:synopsis:`ext::auth::perm::auth_write`

:eql:synopsis:`ext::auth::perm::auth_read_user`


Permissions for ``ai`` extension are described
in :ref:`AI extension reference <ref_ai_extai_reference_permissions>`.


Custom permissions
==================

.. _ref_datamodel_permissions_custom:

Custom permissions can be defined in schema, to fit the security model of each
application.

.. code-block:: sql

    module default {
        permission data_export;
    }

These permissions can be assigned to roles, similar to built-in permissions:

.. code-block:: edgeql

    alter role warehouse {
      set permissions := {default::data_export};
    };

.. note::

    Role permissions are instance-wide.

    If an unrelated branch defines ``default::data_export``, the ``warehouse``
    role will receive it as well. This happens even if the unrelated branch
    adds the permission after ``alter role``.

    Additionally, a role may be given permissions which do not yet exist in
    any schema. This is useful for creating roles before any schemas are
    applied.


To check if the current database connection's role has a permission, use
:ref:`global variable<ref_datamodel_globals>` with the same name
as the permission. This global is a boolean and cannot be manually set.

.. code-block:: edgeql

    select global default::data_export;


In combination with access policies, permissions can be used to limit read or
write access of any type:

.. code-block:: sdl

    type AuditLog {
        property event: str;

        access policy only_export_can_read
            allow select
            using (global data_export);

        access policy anyone_can_insert
            allow insert;
    }

In this example, we have type ``AuditLog`` into which all roles are allowed to
insert new log entries. But reading is allowed only to roles that posses
``data_export`` permission (or are qualified as a *superuser*).


Common patterns
===============


Public readonly database
------------------------

Gel server can be exposed to public internet, with clients connecting directy
from browsers. In such scenarios, it is recommended to create a separate role
that will be used by the JavaScript client (e.g. ``webapp```) and give it
a restricted set of permissions.

For example, if the webapp only needs read access and no data modification,
it doesn't need any permissions set. This way, it will not be able to issue
``DROP TYPE`` or ``DELETE`` commands, but will be able to read all data in the
database.

If we want to limit that access further, for example read access to type
``Secrets``, we can use this schema:

.. code-block:: sdl

    permission server_access;

    type Secret {
        ...

        access policy all_access
            allow select, insert, update, delete
            using (global server_access);
    };


Now, ``webapp`` will not possess permission ``server_access``, which is
required to read or modify ``Secret``. To be able to use the ``Secrets``, we
have use super user role, or some other role with ``server_access`` permission:

.. code-block:: edgeql

    create role api_server {
        set password := 'strong_password';
        set permissions := {sys::dml, default::server_access};
    };


Public partially writable database
----------------------------------

A similar example to the previous one is a public database, with a JavaScript
client that need write access to some object types.

In such scenarios, it is recommended to create a separate role for it
(e.g. ``webapp``) and assign it ``sys::ddl`` permission.

Such role will be able to connect to the database, read all data and modify
all types. For obvious reasons, this is undesirable, since client credentials
could be extracted and used to delete all data in the database.

To further limit access, the access policies must be used on
every object:

.. code-block:: sdl

    permission server_access;

    type Posts {  # read-only
        ...
        access polict everyone_can_read allow select using (true);
        access policy server_can_do_everything
            allow select, insert, update, delete
            using (global server_access);
    }

    type Events {  # insert-only
        ...
        access policy everyone_can_insert allow insert using (true);
        access policy server_can_do_everything
            allow select, insert, update, delete
            using (global server_access);
    }

    type Secrets {  # no access
        ...
        access policy server_can_do_everything
            allow select, insert, update, delete
            using (global server_access);
    };


Again, we can then use superuser role for server to fully access the database,
or setup a separate role with ``server_access`` permission.`


.. list-table::
  :class: seealso

  * - **See also**
  * - :ref:`Schema > Access policies
      <ref_datamodel_access_policies>`
  * - :ref:`Running Gel > Administration > Roles <ref_admin_roles>`


