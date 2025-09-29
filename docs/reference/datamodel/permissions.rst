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


Permissions for :ref:`ai <ref_ai_extai_reference>` extension:

:eql:synopsis:`ext::ai::perm::provider_call`

:eql:synopsis:`ext::ai::perm::chat_prompt_read`

:eql:synopsis:`ext::ai::perm::chat_prompt_write`


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


.. list-table::
  :class: seealso

  * - **See also**
  * - :ref:`Schema > Access policies
      <ref_datamodel_access_policies>`
  * - :ref:`Running Gel > Administration > Roles <ref_admin_roles>`


