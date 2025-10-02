.. _ref_admin_roles:

=====
Roles
=====

:edb-alt-title: Roles


This section describes the administrative commands pertaining to *roles*.


Create role
===========

:eql-statement:

Create a role.

.. eql:synopsis::

    create superuser role <name> [ extending <base> [, ...] ]
    "{" <subcommand>; [...] "}" ;

    # where <subcommand> is one of

      set password := <password>


Description
-----------

The command ``create role`` defines a new database role.

:eql:synopsis:`superuser`
    If specified, the created role will have the *superuser* status, and
    will be exempt from all permission checks.

    Prior to version 7.0, ``superuser`` qualifier was mandatory, i.e. it was not
    possible to create non-superuser roles.

:eql:synopsis:`<name>`
    The name of the role to create.

:eql:synopsis:`extending <base> [, ...]`
    If specified, declares the parent roles for this role. The role
    inherits all the privileges of the parents.

The following subcommands are allowed in the ``create role`` block:

:eql:synopsis:`set password := <password>`
    Set the password for the role.

.. versionadded:: 7.0

    :eql:synopsis:`set permissions := <permissions>`
        Set :ref:`permissions <ref_datamodel_permissions>` for the role.
        Value is a set of identifiers of either built-in permissions or
        permissions defined in schema.

        Roles also gain the permissions of their base Roles. 

        Roles that are *superusers* are implicitly granted all permissions, so
        setting this does not have any effect.

        Note that permission names are not validated and it is possible to
        reference a permission that does not yet exist in any schema.

    :eql:synopsis:`set branches := <branches>`
        Set of branches that this role is allowed to access. When connecting
        to instance branch that is not in this set, connection will be refused.
        If set to ``*``, this branch can connect to all branches of the
        instance. Defaults to ``**``.


Examples
--------

Create a new role:

.. code-block:: edgeql

    create role alice {
        set password := 'wonderland';
        set permissions := {
          sys::perm::data_modifiction,
          sys::perm::query_stats,
          cfg::perm::configure_timeouts,
          cfg::perm::configure_apply_access_policies,
          ext::auth::perm::auth_read,
          ext::auth::perm::auth_write,
      };
      set branches := {'main', 'staging'};
    };


Alter role
==========

:eql-statement:

Alter an existing role.

.. eql:synopsis::

    alter role <name> "{" <subcommand>; [...] "}" ;

    # where <subcommand> is one of

      rename to <newname>
      set password := <password>
      extending ...


Description
-----------

The command ``alter role`` changes the settings of an existing role.


:eql:synopsis:`<name>`
    The name of the role to alter.

The following subcommands are allowed in the ``alter role`` block:

:eql:synopsis:`rename to <newname>`
    Change the name of the role to *newname*.

:eql:synopsis:`extending ...`
    Alter the role parent list.  The full syntax of this subcommand is:

    .. eql:synopsis::

         extending <name> [, ...]
            [ first | last | before <parent> | after <parent> ]

    This subcommand makes the role a child of the specified list of
    parent roles. The role inherits all the privileges of the parents.

    It is possible to specify the position in the parent list
    using the following optional keywords:

    * ``first`` -- insert parent(s) at the beginning of the
      parent list,
    * ``last`` -- insert parent(s) at the end of the parent list,
    * ``before <parent>`` -- insert parent(s) before an
      existing *parent*,
    * ``after <parent>`` -- insert parent(s) after an existing
      *parent*.

.. versionadded:: 7.0

    :eql:synopsis:`set permissions := <permissions>`
        Set :ref:`permissions <ref_datamodel_permissions>` for the role.
        Value is a set of identifiers of either built-in permissions or
        permissions defined in schema.

        Roles that are *superusers* are implicitly granted all permissions, so
        setting this does not have any effect.

        Note that permission names are not validated and it is possible to
        reference a permission that does not yet exist in the schema.

    :eql:synopsis:`set branches := <branches>`
        Set of branches that this role is allowed to access. When connecting
        to instance branch that is not in this set, connection will be refused.
        If set to ``*``, this branch can connect to all branches of the
        instance. Defaults to ``**``.


Examples
--------

Alter a role:

.. code-block:: edgeql

    alter role alice {
        set password := 'new password';
        set branches := {'*'};
    };


Drop role
=========

:eql-statement:

Remove a role.

.. eql:synopsis::

    drop role <name> ;

Description
-----------

The command ``drop role`` removes an existing role.

Examples
--------

Remove a role:

.. code-block:: edgeql

    drop role alice;
