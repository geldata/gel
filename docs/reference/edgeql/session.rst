.. _ref_eql_session:

Session
=======

.. api-index:: set module, set alias, set global,
               reset module, reset alias, reset global,
               configure, configure session, configure current branch, configure instance


Overview
--------

EdgeQL has a concept of a *session* that represents a configuration for the
current connection. This configuration will apply to all queries run through
the connection.

Things that can be configured in a session:

* setting values for *globals*, like ``current_user_id``
* setting session-level *configuration* options
* aliases for *modules*
* setting a different *default* module than ``std``


Globals
-------

Here's a quick example of how to set a global in the REPL:

.. code-block:: edgeql-repl

  db> set global current_user_id :=
  ...  <uuid>'2141a5b4-5634-4ccc-b835-437863534c51';
  OK: SET GLOBAL

Globals have a dedicated documentation page :ref:`ref_datamodel_globals`
with examples and a comprehensive overview on how to define them in the schema,
use them in access policies and queries, and set them in client libraries.


Configuration
-------------

Here's a quick example of how to use a configuration option to disable
access policies in a REPL session:

.. code-block:: edgeql-repl

  db> configure session set apply_access_policies := false;
  OK: CONFIGURE SESSION

Like globals, configuration is a vast topic as there's a a dedicated
documentation page :ref:`ref_admin_config` on all configurable parameters.

Outside of the REPL, you rarely need to use the ``configure`` command directly.
Use the dedicated client API instead, e.g.:

.. code-tabs::

  .. code-tab:: python

    client = client.with_config(apply_access_policies=False)
    await client.query('select ...')

  .. code-tab:: typescript

    client = client.withConfig({ "query_timeout": 10000 });
    await client.query('select ...');


EdgeQL syntax
-------------

.. _ref_eql_statements_configure:

configure
^^^^^^^^^

:eql-statement:

``configure`` -- change a server configuration parameter

.. eql:synopsis::

    configure {session | current branch | instance}
        set <parameter> := <value> ;
    configure instance insert <parameter-class> <insert-shape> ;
    configure {session | current branch | instance} reset <parameter> ;
    configure {current branch | instance}
        reset <parameter-class> [ filter <filter-expr> ] ;

.. note::
    Prior to |Gel| and |EdgeDB| 5.0 *branches* were called *databases*.
    ``configure current branch`` is used to be called
    ``configure current database``, which is still supported for backwards
    compatibility.


Description
~~~~~~~~~~~

This command allows altering the server configuration.

The effects of :eql:synopsis:`configure session` last until the end of the
current session. Some configuration parameters cannot be modified by
:eql:synopsis:`configure session` and can only be set by
:eql:synopsis:`configure instance`.

:eql:synopsis:`configure current branch` is used to configure an
individual Gel branch within a server instance with the
changes persisted across server restarts.

:eql:synopsis:`configure instance` is used to configure the entire Gel
instance with the changes persisted across server restarts.  This variant
acts directly on the file system and cannot be rolled back, so it cannot
be used in a transaction block.

The :eql:synopsis:`configure instance insert` variant is used for composite
configuration parameters, such as ``Auth``.


Parameters
~~~~~~~~~~

:eql:synopsis:`<parameter>`
    The name of a primitive configuration parameter.  Available
    configuration parameters are described in the :ref:`ref_std_cfg`
    section.

:eql:synopsis:`<parameter-class>`
    The name of a composite configuration value class.  Available
    configuration classes are described in the :ref:`ref_std_cfg`
    section.

:eql:synopsis:`<filter-expr>`
    An expression that returns a value of type :eql:type:`std::bool`.
    Only configuration objects matching this condition will be affected.


Examples
~~~~~~~~

Set the ``listen_addresses`` parameter:

.. code-block:: edgeql

    configure instance set listen_addresses := {'127.0.0.1', '::1'};

Set the ``query_work_mem`` parameter for the duration of the session:

.. code-block:: edgeql

    configure instance set query_work_mem := <cfg::memory>'4MiB';

Add a Trust authentication method for "my_user":

.. code-block:: edgeql

    configure instance insert Auth {
        priority := 1,
        method := (insert Trust),
        user := 'my_user'
    };

Remove all Trust authentication methods:

.. code-block:: edgeql

    configure instance reset Auth filter Auth.method is Trust;


.. _ref_eql_statements_session_set_alias:

set
^^^

:eql-statement:


``set`` -- set one or multiple session-level parameters

.. eql:synopsis::

    set module <module> ;
    set alias <alias> as module <module> ;
    set global <name> := <expr> ;


Description
~~~~~~~~~~~

This command allows altering the configuration of the current session.


Variations
~~~~~~~~~~

:eql:synopsis:`set module <module>`
    Set the default module for the current section to *module*.

    For example, if a module ``foo`` contains type ``FooType``,
    the following is how the type can be referred to:

    .. code-block:: edgeql

        # Use the fully-qualified name.
        select foo::FooType;

        # Use the WITH clause to define the default module
        # for the query.
        with module foo select foo::FooType;

        # Set the default module for the current session ...
        set module foo;
        # ... and use an unqualified name.
        select FooType;


:eql:synopsis:`set alias <alias> as module <module>`
    Define :eql:synopsis:`<alias>` for the
    :eql:synopsis:`<module>`.

    For example:

    .. code-block:: edgeql

        # Use the fully-qualified name.
        select foo::FooType;

        # Use the WITH clause to define a custom alias
        # for the "foo" module.
        with bar as module foo
        select bar::FooType;

        # Define "bar" as an alias for the "foo" module for
        # the current session ...
        set alias bar as module foo;
        # ... and use "bar" instead of "foo".
        select bar::FooType;


:eql:synopsis:`set global <name> := <expr>`
    Set the global variable *name* to the specified value.

    For example:

    .. code-block:: edgeql

        # Set the global variable "current_user_id".
        set global current_user_id :=
            <uuid>'00ea8eaa-02f9-11ed-a676-6bd11cc6c557';

        # We can now use that value in a query.
        select User { name }
        filter .id = global current_user_id;


Examples
~~~~~~~~

.. code-block:: edgeql

    set module foo;

    set alias foo AS module std;

    set global current_user_id :=
        <uuid>'00ea8eaa-02f9-11ed-a676-6bd11cc6c557';


.. _ref_eql_statements_session_reset_alias:

reset
^^^^^

:eql-statement:


``reset`` -- reset one or multiple session-level parameters

.. eql:synopsis::

    reset module ;
    reset alias <alias> ;
    reset alias * ;
    reset global <name> ;


Description
~~~~~~~~~~~

This command allows resetting one or many configuration parameters of
the current session.


Variations
~~~~~~~~~~

:eql:synopsis:`reset module`
    Reset the default module name back to "default" for the current
    session.

    For example, if a module ``foo`` contains type ``FooType``,
    the following is how the ``set`` and ``reset`` commands can be used
    to alias it:

    .. code-block:: edgeql

        # Set the default module to "foo" for the current session.
        set module foo;

        # This query is now equivalent to "select foo::FooType".
        select FooType;

        # Reset the default module for the current session.
        reset module;

        # This query will now produce an error.
        select FooType;


:eql:synopsis:`reset alias <alias>`
    Reset :eql:synopsis:`<alias>` for the current session.

    For example:

    .. code-block:: edgeql

        # Alias the "std" module as "foo".
        set alias foo as module std;

        # Now "std::min()" can be called as "foo::min()" in
        # the current session.
        select foo::min({1});

        # Reset the alias.
        reset alias foo;

        # Now this query will error out, as there is no
        # module "foo".
        select foo::min({1});

:eql:synopsis:`reset alias *`
    Reset all aliases defined in the current session.  This command
    affects aliases set with :eql:stmt:`set alias <set>` and
    :eql:stmt:`set module <set>`. The default module will be set to "default".

    Example:

    .. code-block:: edgeql

        # Reset all custom aliases for the current session.
        reset alias *;


:eql:synopsis:`reset global <name>`
    Reset the global variable *name* to its default value or ``{}`` if the
    variable has no default value and is ``optional``.


Examples
~~~~~~~~

.. code-block:: edgeql

    reset module;

    reset alias foo;

    reset alias *;

    reset global current_user_id;
