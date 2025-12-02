.. _ref_guide_cloud_http_gql:

===================
HTTP & GraphQL APIs
===================

:edb-alt-title: Querying Gel Cloud over HTTP and GraphQL

Gel Cloud is shutting down. If you still need to connect to a legacy hosted
instance over HTTP or GraphQL to export data, the process matches
:ref:`any other Gel deployment <ref_edgeql_http>`.

- Find your host and port with :gelcmd:`instance credentials -I
  <org>/<instance>` and switch the protocol to ``https``.
- Authenticate using a secret key from :ref:`ref_cli_gel_cloud_secretkey_create`
  (or the web console) as a bearer token.

Once you have exported what you need, restore the data into a self-managed
instance and retire your Cloud deployment.
