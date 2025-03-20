.. _gel_client_connection:
.. _ref_reference_connection:

=====================
Connection parameters
=====================

The CLI and client libraries (collectively referred to as "clients" below) must connect to a |Gel| instance to run queries or commands. Ultimately, configuration works to specify a specific |Gel| branch on a specific |Gel| instance, and any required credentials. Additionally, client connection behavior can also be specified.

There are multiple places where the configuration can be specified, and the clients all share the same resolution logic and priority order. Let's first look at how to specify the connection configuration, and then we'll look at the different environments your own applications may run in and what the common practices are for specifying the configuration for each type of environment.

.. _ref_reference_connection_instance:

Connecting to a Gel branch
==========================

The first job of the configuration system is to specify a |Gel| branch on a specific |Gel| instance. The parts that make up the full configuration are:

* **Host**: defaults to ``"localhost"``
    The host name or IP address of the |Gel| instance.
* **Port**: defaults to ``5656``
    The port number of the |Gel| instance.
* **Branch**: defaults to |main|
    The name of the |Gel| branch to connect to.
* **User**: defaults to |admin|
    The user name to connect as.
* **Password**: defaults to unset
    The password for the user.
* **TLS certificate**: defaults to unset
    The TLS certificate to use for the connection, if any.
* **TLS security**: defaults to ``"strict"``
    The TLS security mode to use for the connection.

There are several ways to specify these parameters:

.. _ref_reference_connection_instance_name:

Instance name
-------------

All local instances created on your local machine using the :gelcmd:`project init` command are associated with a name. This name is what's needed to connect; under the hood, the CLI stores the instance location and credentials (host, port, username, password, etc) on your file system in the Gel :ref:`config directory <ref_cli_gel_paths>`. The clients look up these credentials to connect.

You can also assign names to remote instances using :ref:`gel instance link <ref_cli_gel_instance_link>`. The CLI will save the credentials locally, so you can connect to a remote instance using just its name, just like a local instance.

If you have authenticated with Gel Cloud in the CLI using the :ref:`ref_cli_gel_cloud_login` command, you can address your own Gel Cloud instances using the instance name format ``<org-name>/<instance-name>``. When connecting a deployed application instead of logging in, you will need to provide an instance name and secret key, which you can create using the :gelcmd:`cloud secretkey create` command or in the |Gel| Cloud web UI.

Each named instance will also have a branch associated with the credentials, which defaults to |main|. You can create and switch branches using the :gelcmd:`branch create` and :gelcmd:`branch switch` commands or by specifying the branch name explicitly in the :ref:`branch connection parameter <ref_reference_connection_parameters_branch>`.

.. _ref_dsn:
.. _ref_reference_connection_dsn:

DSN
---

DSNs (data source names) are a convenient and flexible way to specify connection information with a simple string. It takes the following form:

.. code-block:: text

  gel://<user>:<password>@<host>:<port>/<branch>

All components of the DSN are optional; in fact, gel:// is a valid DSN. Any unspecified values will fall back to the defaults. DSNs also support URL query parameters (``?host=myhost.com``) to support advanced use cases and :ref:`additional connection parameters <ref_reference_connection_parameters>`. The value for a given parameter can be specified in three ways:

**Plain params**
  .. code-block::

    gel://hostname.com:1234?tls_security=insecure

  These "plain" parameters can be used to provide values for options that can't otherwise be reflected in the DSN, like TLS settings (described in more detail below).

  You can't specify the same setting both in the body of the DSN and in a query parameter. For instance, this DSN is invalid, as the port is ambiguous: :geluri:`hostname.com:1234?port=5678`.

**File params**
  .. code-block::

    gel://hostname.com:1234?tls_security_file=./tls_security.txt

    # ./tls_security.txt
    insecure

  If you prefer to store sensitive credentials in local files, you can use file params to specify a path to a local UTF-8 encoded file. This file should contain a single line containing the relevant value.

  Relative params are resolved relative to the current working directory at the time of connection.

**Environment params**
  .. code-block::

    MY_TLS_SECURITY=insecure
    GEL_DSN=gel://hostname.com:1234?tls_security_env=MY_TLS_SECURITY

  Environment params lets you specify a *pointer* to another environment variable. At runtime, the specified environment variable will be read. If it isn't set, an error will be thrown.

  Note that this is not a shell-style variable substitution, but rather a way to specify the name of another environment variable that contains the value.

Host and port
-------------

In general, we recommend using a fully-qualified DSN when connecting to the database. For convenience, it's possible to individually specify a host and/or a port.

Credentials file
----------------

.. warning::

  Checking this file into version control could present a security risk and is not recommended.

If you wish, you can store your credentials as a JSON file like the :gelcmd:`instance link` command does, and then pass the path to the file to the client libraries or CLI.

.. code-block:: json

  {
    "host": "localhost",
    "port": 10702,
    "user": "testuser",
    "password": "testpassword",
    "branch": "main",
    "tls_cert_data": "-----BEGIN CERTIFICATE-----\nabcdef..."
  }

Relative paths are resolved relative to the current working directory.

.. _ref_reference_connection_environments:

Environments
============

There are two common scenarios or environments for applications connecting to a |Gel| branch:

* **Development**: When you are developing your application and running it locally, you will typically want to connect to a |Gel| instance running on the same machine, or at least on the same network.
* **Deployed**: When you are running your application in a production, or production-like environment, the database instance might be running on a separate network. You also typically don't interact with the application environment directly, but rather through some kind of platform or production system. Examples of a deployed environment are running tests in a CI pipeline, a staging environment, or a production environment.

Development environments
------------------------

* **CLI-managed local instances**: When you initialize a project using :gelcmd:`project init`, the CLI will create a local instance, and create a local credentials file. Clients will detect that there is a local project, and resolve the DSN and authentication credentials automatically. You can use the CLI to create and switch local branches using the :gelcmd:`branch create` and :gelcmd:`branch switch` commands.
* **Cloud instances**: Use the :gelcmd:`cloud login` command to authenticate with |Gel| Cloud, and then use the :gelcmd:`project init --server-instance org/instance-name` command to create a local project-linked instance that is linked to an Gel Cloud instance. Once you've linked your |Gel| Cloud instance as a project, you can use the :gelcmd:`branch create` and :gelcmd:`branch switch` commands to create and switch branches.
* **Self-hosted instances**: When you have a |Gel| instance running on a remote machine or in a container, you can use the :gelcmd:`instance link` command to create a name corresponding to a remote instance. Once you have a linked instance, you can use :gelcmd:`project init --server-instance <instance-name>` to create a local project that is linked to the named remote instance.

Deployed environments
---------------------

* **CLI-managed local instances**: It's not recommended to use CLI-managed local instances in production, but this can be useful for CI pipelines. If you use GitHub Actions, you can use the `setup-gel action <https://github.com/geldata/setup-gel>`_ to automatically create a local instance and initialize a project.
* **Cloud instances**: To identify and authenticate with a |Gel| Cloud instance, you will need to provide the instance name and secret key. Your instance name will be of the form ``<org-name>/<instance-name>``. For each environment you deploy to, you should create a new secret key, which you can do locally using the :gelcmd:`cloud secretkey create` command or in the |Gel| Cloud web UI. You will need to also provide the branch name if you use multiple branches in your Cloud instance, for instance to share a single Cloud instance between testing, staging, and production environments. We recommend that you use environment variables in your runtime environment to configure these values.
* **Self-hosted instances**: When you have a |Gel| instance running on a machine or in a container, you can connect to it using a DSN that specifies the host, port, branch, and authentication credentials of the instance. We recommend that you use environment variables in your runtime environment to configure these values.

.. _ref_reference_connection_priority:

Priority levels
===============

The section above describes the various ways of specifying a Gel instance.  There are also several ways to provide this configuration information to the client. From highest to lowest priority, you can pass them explicitly as parameters/flags (useful for debugging), use environment variables (recommended for production), or rely on :gelcmd:`project` (recommended for development).

1. **Explicit connection parameters**. For security reasons, hard-coding connection information or credentials in your codebase is not recommended, though it may be useful for debugging or testing purposes. As such, explicitly provided parameters are given the highest priority.

   In the context of the client libraries, this means passing an option explicitly into the client creation call. Here's how this looks using the JavaScript library as an example:

   .. code-block:: javascript

      import { createClient } from "gel";

      const pool = createClient({
        instance: "my_instance"
      });

   In the context of the CLI, this means using the appropriate command-line flags:

   .. code-block:: bash

      $ gel --instance my_instance
      Gel x.x
      Type \help for help, \quit to quit.
      main>


2. **Environment variables**.

   This is the recommended mechanism for providing connection information to your Gel client, especially in production or when running Gel inside a container. All clients read the following variables from the environment:

   - :gelenv:`DSN`
   - :gelenv:`INSTANCE`
   - :gelenv:`CREDENTIALS_FILE`
   - :gelenv:`HOST` / :gelenv:`PORT`

   When one of these environment variables is defined, there's no need to pass
   any additional information to the client. The CLI and client libraries will
   be able to connect without any additional information. You can execute CLI
   commands without any additional flags, like so:

   .. code-block:: bash

      $ gel  # no flags needed
      Gel x.x
      Type \help for help, \quit to quit.
      gel>

   Using the JavaScript client library:

   .. code-block:: javascript

      import { createClient } from "gel";

      const client = createClient();
      const result = await client.querySingle("select 2 + 2;");
      console.log(result); // 4

   .. warning::

      Ambiguity is not permitted. For instance, specifying both
      :gelenv:`INSTANCE` and :gelenv:`DSN` will result in an error. You *can*
      use :gelenv:`HOST` and :gelenv:`PORT` simultaneously.


3. **Project-linked credentials**

   If you are using :gelcmd:`project` (which we recommend!) and haven't otherwise specified any connection parameters, clients will connect to the instance that's been linked to your project.

   This makes it easy to get up and running with Gel. Once you've run :gelcmd:`project init`, clients will be able to connect to your database without any explicit flags or parameters, as long as you're inside the project directory.


If no connection information can be detected using the above mechanisms, the connection fails.

.. warning::

   Within a given priority level, you cannot specify multiple instances of "instance selection parameters" simultaneously. For instance, specifying both :gelenv:`INSTANCE` and :gelenv:`DSN` environment variables will result in an error.

.. _ref_reference_connection_granular_override:

Override behavior
-----------------

When specified, the connection parameters (user, password, and |branch|) will *override* the corresponding element of a DSN, credentials file, etc.  For instance, consider the following environment variables:

.. code-block::

  GEL_DSN=gel://olduser:oldpass@hostname.com:5656
  GEL_USER=newuser
  GEL_PASSWORD=newpass

In this scenario, ``newuser`` will override ``olduser`` and ``newpass`` will override ``oldpass``. The client library will try to connect using this modified DSN: :geluri:`newuser:newpass@hostname.com:5656`.

Overriding across priority levels
---------------------------------

Override behavior can only happen at the *same or lower priority level*. For instance:

- :gelenv:`PASSWORD` **will** override the password specified in :gelenv:`DSN`

- :gelenv:`PASSWORD` **will be ignored** if a DSN is passed explicitly using the ``--dsn`` flag. Explicit parameters take precedence over environment variables. To override the password of an explicit DSN, you need to pass it explicitly as well:

  .. code-block:: bash

     $ gel --dsn gel://username:oldpass@hostname.com --password qwerty
     # connects to gel://username:qwerty@hostname.com

- :gelenv:`PASSWORD` **will** override the stored password associated with a project-linked instance. (This is unlikely to be desirable.)

.. _ref_reference_connection_granular:
.. _ref_reference_connection_parameters:

Parameter Reference
===================

The following is a list of all of the connection parameters and their corresponding environment variables, CLI flags, and client library parameters. Different language clients may have different parameter casing depending on the idiomatic conventions of the language, so see the specific client documentation for details.

.. _ref_reference_connection_parameters_dsn:

DSN
---

* Environment variable: :gelenv:`DSN`
* CLI flag: ``--dsn/-d <dsn>``
* Client library parameter: ``dsn``

DSNs (data source names) are a convenient and flexible way to specify connection information with a simple string. It takes the following form:

.. code-block:: text

  gel://<user>:<password>@<host>:<port>/<branch>

For more details, see :ref:`ref_reference_connection_dsn` above.

.. _ref_reference_connection_parameters_host:

Host
----

* Environment variable: :gelenv:`HOST`
* CLI flag: ``--host/-h <host>``
* Client library parameter: ``host``
* DSN query parameter: ``host``, ``host_file``, ``host_env``
* Default value: ``"localhost"``

The host name or IP address of the |Gel| instance.

.. _ref_reference_connection_parameters_port:

Port
----

* Environment variable: :gelenv:`PORT`
* CLI flag: ``--port/-P <port>``
* Client library parameter: ``port``
* DSN query parameter: ``port``, ``port_file``, ``port_env``
* Default value: ``5656``

The port number of the |Gel| instance.

.. _ref_reference_connection_parameters_instance_name:

Instance name
-------------

* Environment variable: :gelenv:`INSTANCE`
* CLI flag: ``--instance/-i <name>``
* Client library parameter: ``instance``

Described above in :ref:`ref_reference_connection_instance_name`. This name is used to look up the instance credentials in the |Gel| :ref:`config directory <ref_cli_gel_paths>`. If the instance name is a |Gel| Cloud instance, you will either need to be signed into your |Gel| Cloud account or provide a secret key.

.. _ref_reference_connection_secret_key:
.. _ref_reference_connection_parameters_secret_key:

Secret key
----------

* Environment variable: :gelenv:`SECRET_KEY`
* CLI flag: ``--secret-key/-k <key>``
* Client library parameter: ``secretKey`` or ``secret_key``

This |Gel| Cloud specific parameter is used to authenticate with a |Gel| Cloud instance. It is required when connecting to a |Gel| Cloud instance that is not the one you are currently signed into or when connecting from a deployed application.

.. _ref_reference_connection_parameters_branch:

Branch
------

* Environment variable: :gelenv:`BRANCH`
* CLI flag: ``--branch/-b <name>``
* Client library parameter: ``branch``
* DSN query parameter: ``branch``, ``branch_file``, ``branch_env``
* Default value: |main|

Each Gel instance can contain multiple branches. Each branch can be related to other branches on the same instance by sharing some or all of the schema, or be completely independent. The data for all branches are isolated from each other. For more information on branches, see :ref:`the branches reference section <ref_datamodel_branches>`.

When an instance is created, a default branch named |main| is created. For CLI-managed linked instances, connections are made to the currently active branch. In other cases, incoming connections connect to the |main| branch by default.

.. _ref_reference_connection_parameters_user:

User
----

* Environment variable: :gelenv:`USER`
* CLI flag: ``--user/-u <user>``
* Client library parameter: ``user``
* DSN query parameter: ``user``, ``user_file``, ``user_env``
* Default value: |admin|

When using authentication, the user/role name to connect as.

.. _ref_reference_connection_parameters_password:

Password
--------

* Environment variable: :gelenv:`PASSWORD`
* CLI flag: ``--password/-p <pass>``
* Client library parameter: ``password``
* DSN query parameter: ``password``, ``password_file``, ``password_env``

The password for the :ref:`ref_reference_connection_parameters_user`.

.. _ref_reference_connection_parameters_tls_ca_file:

TLS CA file
-----------

* Environment variable: :gelenv:`TLS_CA_FILE`
* CLI flag: ``--tls-ca-file <path>``
* Client library parameter: ``tlsCAFile`` or ``tls_ca_file``
* DSN query parameter: ``tls_ca_file``, ``tls_ca_file_file``, ``tls_ca_file_env``

TLS is required to connect to any Gel instance. To do so, the client needs a reference to the root certificate of your instance's certificate chain.  Typically this will be handled for you when you create a local instance or ``link`` a remote one.

If you're using a globally trusted CA like Let's Encrypt, the root certificate will almost certainly exist already in your system's global certificate pool. In this case, you won't need to specify this path; it will be discovered automatically by the client.

If you're self-issuing certificates, you must download the root certificate and provide a path to its location on the filesystem. Otherwise TLS will fail to connect.

.. _ref_reference_connection_parameters_tls_server_name:

TLS server name
---------------

* Environment variable: :gelenv:`TLS_SERVER_NAME`
* CLI flag: ``--tls-server-name <name>``
* Client library parameter: ``tlsServerName`` or ``tls_server_name``
* DSN query parameter: ``tls_server_name``, ``tls_server_name_file``, ``tls_server_name_env``

If for some reason target instance IP address can't be resolved from the hostname, you can provide the SNI (server name indication) to use for TLS connections.

.. _ref_reference_connection_parameters_tls_security:

TLS security
------------

* Environment variable: :gelenv:`CLIENT_TLS_SECURITY`
* CLI flag: ``--tls-security <mode>``
* Client library parameter: ``tlsSecurity`` or ``tls_security``
* DSN query parameter: ``tls_security``, ``tls_security_file``, ``tls_security_env``
* Default value: ``"strict"`` or ``"no_host_verification"`` depending on whether a custom certificate is supplied

Sets the TLS security mode. Determines whether certificate and hostname verification is enabled. Possible values:

- ``"strict"`` — certificates and hostnames will be verified
- ``"no_host_verification"`` — verify certificates but not hostnames
- ``"insecure"`` — client libraries will trust self-signed TLS certificates. Useful for self-signed or custom certificates.

.. _ref_reference_connection_parameters_client_security:

Client security
---------------

* Environment variable: :gelenv:`CLIENT_SECURITY`
* CLI flag: ``--client-security <mode>``
* Client library parameter: ``clientSecurity`` or ``client_security``

Provides some simple "security presets".

Currently there is only one valid value: ``insecure_dev_mode``. Setting ``insecure_dev_mode`` disables all TLS security measures. Currently it is equivalent to setting :ref:`ref_reference_connection_parameters_tls_security` to ``insecure`` but it may encompass additional configuration settings later.  This is most commonly used when developing locally with Docker.

.. _ref_reference_connection_parameters_wait_until_available:

Wait until available
--------------------

* Environment variable: :gelenv:`WAIT_UNTIL_AVAILABLE`
* CLI flag: ``--wait-until-available/-w <timeout>``
* Client library parameter: ``waitUntilAvailable`` or ``wait_until_available``
* DSN query parameter: ``wait_until_available``, ``wait_until_available_file``, ``wait_until_available_env``
* Default value: ``10s``

If the connection can't be established, keep retrying up to the given timeout value. The timeout value must be given using time units (e.g. ``1hr``, ``10min``, ``30sec``, ``500ms``, etc.) or ISO 8601 duration strings (e.g. ``PT1H``, ``PT10M``, ``PT30S``, ``PT0.5S``, etc.).

.. _ref_reference_connection_parameters_connect_timeout:

Connect timeout
---------------

* Environment variable: :gelenv:`CONNECT_TIMEOUT`
* CLI flag: ``--connect-timeout/-c <timeout>``
* Client library parameter: ``connectTimeout`` or ``connect_timeout``
* DSN query parameter: ``connect_timeout``, ``connect_timeout_file``, ``connect_timeout_env``
* Default value: ``10s``

Specifies a timeout period. In the event Gel doesn't respond in this period, the command will fail (or retry if :ref:`ref_reference_connection_parameters_wait_until_available` is also specified). The timeout value must be given using time units (e.g. ``1hr``, ``10min``, ``30sec``, ``500ms``, etc.) or ISO 8601 duration strings (e.g. ``PT1H``, ``PT10M``, ``PT30S``, ``PT0.5S``, etc.).