.. _ref_reference_http_querying:
.. _ref_edgeql_http:

================
EdgeQL over HTTP
================

|Gel| can expose an HTTP endpoint for EdgeQL queries. Since HTTP is a stateless protocol, no :ref:`DDL <ref_eql_ddl>`, :ref:`transaction commands <ref_eql_statements_start_tx>`, can be executed using this endpoint.  Only one query per request can be executed.

Setup
=====

In order to set up HTTP access to the database add the following to the schema:

.. code-block:: sdl

    using extension edgeql_http;

Then create a new migration and apply it using :ref:`ref_cli_gel_migration_create` and :ref:`ref_cli_gel_migrate`, respectively.

Your instance can now receive EdgeQL queries over HTTP at ``https://<hostname>:<port>/branch/<branch-name>/edgeql``.

.. note::

  Here's how to determine your local |Gel| instance's HTTP server URL:

  - The ``hostname`` will be ``localhost``
  - Find the ``port`` by running :gelcmd:`instance list`. This will print a table of all |Gel| instances on your machine, including their associated port number.
  - The default ``branch-name`` will be |main|, and after initializing your database, all queries are executed against it by default. If you want to query another branch instead, simply use that branch name in the URL.

  To determine the URL of a |Gel| Cloud instance, find the host by running :gelcmd:`instance credentials -I <org-name>/<instance-name>`. Use the ``host`` and ``port`` from that table in the URL format above this note.  Change the protocol to ``https`` since Gel Cloud instances are secured with TLS.

  To determine the URL of a self-hosted remote instance you have linked with the CLI, you can get both the hostname and port of the instance from the "Port" column of the :gelcmd:`instance list` table (formatted as ``<hostname>:<port>``). The same guidance on local branch names applies here.

.. _ref_http_auth:

Authentication
==============

.. versionadded:: 4.0

.. lint-off

By default, the HTTP endpoint uses :eql:type:`cfg::Password` based
authentication, in which
`HTTP Basic Authentication
<https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#basic_authentication_scheme>`_
is used to provide a |Gel| username and password.

.. lint-on

This is configurable, however: the HTTP endpoint's authentication
mechanism can be configured by adjusting which
:eql:type:`cfg::AuthMethod` applies to the ``SIMPLE_HTTP``
:eql:type:`cfg::ConnectionTransport`.

If :eql:type:`cfg::JWT` is used, the requests should contain these headers:

* ``X-EdgeDB-User``: The |Gel| username.

* ``Authorization``: The JWT authorization token prefixed by ``Bearer``.


If :eql:type:`cfg::Trust` is used, no authentication is done at all. This
is not generally recommended, but can be used to recover the pre-4.0
behavior::

    db> configure instance insert cfg::Auth {
    ...     priority := -1,
    ...     method := (insert cfg::Trust { transports := "SIMPLE_HTTP" }),
    ... };
    OK: CONFIGURE INSTANCE

To authenticate to your |Gel| Cloud instance, first create a secret key using
the Gel Cloud UI or :ref:`ref_cli_gel_cloud_secretkey_create`. Use the
secret key as your token with the bearer authentication method. Here is an
example showing how you might send the query ``select Person {*};`` using cURL:

.. lint-off

.. code-block:: bash

    $ curl -G https://<cloud-instance-host>:<cloud-instance-port>/branch/main/edgeql \
       -H "Authorization: Bearer <secret-key> \
       --data-urlencode "query=select Person {*};"

.. lint-on

.. _ref_edgeqlql_protocol:

Querying
========

|Gel| supports GET and POST methods for handling EdgeQL over HTTP protocol. Both GET and POST methods use the following fields:

- ``query`` - contains the EdgeQL query string
- ``variables``- contains a JSON object where the keys are the parameter names from the query and the values are the arguments to be used in this execution of the query.
- ``globals``- contains a JSON object where the keys are the fully qualified global names and the values are the desired values for those globals.

The protocol supports HTTP Keep-Alive.

GET request
-----------

The HTTP GET request passes the fields as query parameters: ``query`` string and JSON-encoded ``variables`` mapping.


POST request
------------

The POST request should use ``application/json`` content type and submit the following JSON-encoded form with the necessary fields:

.. code-block:: json

  {
    "query": "select Person {*} filter .name = <str>$name;",
    "variables": { "name": "John" },
    "globals": { "default::global_name": "value" }
  }


Response
--------

The response format is the same for both methods. The body of the response is JSON of the following form:

.. code-block:: json

  {
    "data": [
      {
        "id": "00000000-0000-0000-0000-000000000000",
        "name": "John"
      }
    ],
    "error": {
      "message": "Error message",
      "type": "ErrorType",
      "code": 123456
    }
  }

The ``data`` response field will contain the response set as a JSON array.

Note that the ``error`` field will only be present if an error actually occurred. The ``error`` will further contain the ``message`` field with the error message string, the ``type`` field with the name of the type of error and the ``code`` field with an integer :ref:`error code <ref_protocol_error_codes>`.

.. note::

  Caution is advised when reading ``decimal`` or ``bigint`` values using HTTP protocol because the results are provided in JSON format. The JSON specification does not have a limit on significant digits, so a ``decimal`` or a ``bigint`` number can be losslessly represented in JSON. However, JSON decoders in many languages will read all such numbers as some kind of of 32- or 64-bit number type, which may result in errors or precision loss.  If such loss is unacceptable, then consider casting the value into ``str`` and decoding it on the client side into a more appropriate type.
