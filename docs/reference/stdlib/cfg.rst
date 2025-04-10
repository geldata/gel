.. _ref_std_cfg:

======
Config
======

The ``cfg`` module contains a set of types and scalars used for configuring
|Gel|.


.. list-table::
  :class: funcoptable

  * - **Type**
    - **Description**
  * - :eql:type:`cfg::AbstractConfig`
    - The abstract base type for all configuration objects. The properties
      of this type define the set of configuruation settings supported by
      Gel.
  * - :eql:type:`cfg::Config`
    - The main configuration object. The properties of this object reflect
      the overall configuration setting from instance level all the way to
      session level.
  * - :eql:type:`cfg::DatabaseConfig`
    - The database configuration object. It reflects all the applicable
      configuration at the Gel database level.
  * - :eql:type:`cfg::BranchConfig`
    - The database branch configuration object. It reflects all the applicable
      configuration at the Gel branch level.
  * - :eql:type:`cfg::InstanceConfig`
    - The instance configuration object.
  * - :eql:type:`cfg::ExtensionConfig`
    - The abstract base type for all extension configuration objects. Each
      extension can define the necessary configuration settings by extending
      this type and adding the extension-specific properties.
  * - :eql:type:`cfg::Auth`
    - An object type representing an authentication profile.
  * - :eql:type:`cfg::ConnectionTransport`
    - An enum type representing the different protocols that Gel speaks.
  * - :eql:type:`cfg::AuthMethod`
    - An abstract object type representing a method of authentication
  * - :eql:type:`cfg::Trust`
    - A subclass of ``AuthMethod`` indicating an "always trust" policy (no
      authentication).
  * - :eql:type:`cfg::SCRAM`
    - A subclass of ``AuthMethod`` indicating password-based authentication.
  * - :eql:type:`cfg::Password`
    - A subclass of ``AuthMethod`` indicating basic password-based
      authentication.
  * - :eql:type:`cfg::JWT`
    - A subclass of ``AuthMethod`` indicating token-based authentication.
  * - :eql:type:`cfg::memory`
    - A scalar type for storing a quantity of memory storage.


.. eql:type:: cfg::AbstractConfig

  An abstract type representing the configuration of an instance or database.

  The properties of this object type represent the set of configuration
  options supported by Gel (listed above).


----------


.. eql:type:: cfg::Config

  The main configuration object type.

  This type will have only one object instance. The ``cfg::Config`` object
  represents the sum total of the current Gel configuration. It reflects
  the result of applying instance, branch, and session level configuration.
  Examining this object is the recommended way of determining the current
  configuration.

  Here's an example of checking and disabling :ref:`access policies
  <ref_std_cfg_apply_access_policies>`:

  .. code-block:: edgeql-repl

      db> select cfg::Config.apply_access_policies;
      {true}
      db> configure session set apply_access_policies := false;
      OK: CONFIGURE SESSION
      db> select cfg::Config.apply_access_policies;
      {false}


----------


.. eql:type:: cfg::BranchConfig

  .. versionadded:: 5.0

  The branch-level configuration object type.

  This type will have only one object instance. The ``cfg::BranchConfig``
  object represents the state of the branch and instance-level Gel
  configuration.

  For overall configuration state please refer to the :eql:type:`cfg::Config`
  instead.


----------


.. eql:type:: cfg::InstanceConfig

  The instance-level configuration object type.

  This type will have only one object instance. The ``cfg::InstanceConfig``
  object represents the state of only instance-level Gel configuration.

  For overall configuraiton state please refer to the :eql:type:`cfg::Config`
  instead.


----------


.. eql:type:: cfg::ExtensionConfig

  .. versionadded:: 5.0

  An abstract type representing extension configuration.

  Every extension is expected to define its own extension-specific config
  object type extending ``cfg::ExtensionConfig``. Any necessary extension
  configuration setting should be represented as properties of this concrete
  config type.

  Up to three instances of the extension-specific config type will be created,
  each of them with a ``required single link cfg`` to the
  :eql:type:`cfg::Config`, :eql:type:`cfg::DatabaseConfig`, or
  :eql:type:`cfg::InstanceConfig` object depending on the configuration level.
  The :eql:type:`cfg::AbstractConfig` exposes a corresponding computed
  multi-backlink called ``extensions``.

  For example, :ref:`ext::pgvector <ref_ext_pgvector>` extension exposes
  ``probes`` as a configurable parameter via ``ext::pgvector::Config`` object:

  .. code-block:: edgeql-repl

    db> configure session
    ... set ext::pgvector::Config::probes := 5;
    OK: CONFIGURE SESSION
    db> select cfg::Config.extensions[is ext::pgvector::Config]{*};
    {
      ext::pgvector::Config {
        id: 12b5c70f-0bb8-508a-845f-ca3d41103b6f,
        probes: 5,
        ef_search: 40,
      },
    }


----------


.. eql:type:: cfg::Auth

  An object type designed to specify a client authentication profile.

  .. code-block:: edgeql-repl

    db> configure instance insert
    ...   Auth {priority := 0, method := (insert Trust)};
    OK: CONFIGURE INSTANCE

  Below are the properties of the ``Auth`` class.

  :eql:synopsis:`priority -> int64`
    The priority of the authentication rule.  The lower this number,
    the higher the priority.

  :eql:synopsis:`user -> multi str`
    The name(s) of the database role(s) this rule applies to.  If set to
    ``'*'``, then it applies to all roles.

  :eql:synopsis:`method -> cfg::AuthMethod`
    The name of the authentication method type. Expects an instance of
    :eql:type:`cfg::AuthMethod`;  Valid values are:
    ``Trust`` for no authentication and ``SCRAM`` for SCRAM-SHA-256
    password authentication.

  :eql:synopsis:`comment -> optional str`
    An optional comment for the authentication rule.

---------

.. eql:type:: cfg::ConnectionTransport

  An enum listing the various protocols that Gel can speak.

  Possible values are:

.. list-table::
  :class: funcoptable

  * - **Value**
    - **Description**
  * - ``cfg::ConnectionTransport.TCP``
    - Gel binary protocol
  * - ``cfg::ConnectionTransport.TCP_PG``
    - Postgres protocol for the
      :ref:`SQL query mode <ref_sql_adapter>`
  * - ``cfg::ConnectionTransport.HTTP``
    - Gel binary protocol
      :ref:`tunneled over HTTP <ref_http_tunnelling>`
  * - ``cfg::ConnectionTransport.SIMPLE_HTTP``
    - :ref:`EdgeQL over HTTP <ref_edgeql_http>`
      and :ref:`GraphQL <ref_graphql_index>` endpoints

---------

.. eql:type:: cfg::AuthMethod

  An abstract object class that represents an authentication method.

  It currently has four concrete subclasses, each of which represent an
  available authentication method: :eql:type:`cfg::SCRAM`,
  :eql:type:`cfg::JWT`, :eql:type:`cfg::Password`, and
  :eql:type:`cfg::Trust`.

  :eql:synopsis:`transports -> multi cfg::ConnectionTransport`
    Which connection transports this method applies to.
    The subclasses have their own defaults for this.

-------

.. eql:type:: cfg::Trust

  The ``cfg::Trust`` indicates an "always-trust" policy.

  When active, it disables password-based authentication.

  .. code-block:: edgeql-repl

    db> configure instance insert
    ...   Auth {priority := 0, method := (insert Trust)};
    OK: CONFIGURE INSTANCE

-------

.. eql:type:: cfg::SCRAM

  ``cfg::SCRAM`` indicates password-based authentication.

  It uses a challenge-response scheme to avoid transmitting the
  password directly.  This policy is implemented via ``SCRAM-SHA-256``

  It is available for the ``TCP``, ``TCP_PG``, and ``HTTP`` transports
  and is the default for ``TCP`` and ``TCP_PG``.

  .. code-block:: edgeql-repl

    db> configure instance insert
    ...   Auth {priority := 0, method := (insert SCRAM)};
    OK: CONFIGURE INSTANCE

-------

.. eql:type:: cfg::JWT

  ``cfg::JWT`` uses a JWT signed by the server to authenticate.

  It is available for the ``TCP``, ``HTTP``, and ``HTTP_SIMPLE`` transports
  and is the default for ``HTTP``.


-------

.. eql:type:: cfg::Password

  ``cfg::Password`` indicates simple password-based authentication.

  Unlike :eql:type:`cfg::SCRAM`, this policy transmits the password
  over the (encrypted) channel.  It is implemened using HTTP Basic
  Authentication over TLS.

  This policy is available only for the ``SIMPLE_HTTP`` transport, where it is
  the default.


-------

.. eql:type:: cfg::memory

  A scalar type representing a quantity of memory storage.

  As with ``uuid``, ``datetime``, and several other types, ``cfg::memory``
  values are declared by casting from an appropriately formatted string.

  .. code-block:: edgeql-repl

    db> select <cfg::memory>'1B'; # 1 byte
    {<cfg::memory>'1B'}
    db> select <cfg::memory>'5KiB'; # 5 kibibytes
    {<cfg::memory>'5KiB'}
    db> select <cfg::memory>'128MiB'; # 128 mebibytes
    {<cfg::memory>'128MiB'}

  The numerical component of the value must be a non-negative integer; the
  units must be one of ``B|KiB|MiB|GiB|TiB|PiB``. We're using the explicit
  ``KiB`` unit notation (1024 bytes) instead of ``kB`` (which is ambiguous,
  and may mean 1000 or 1024 bytes).
