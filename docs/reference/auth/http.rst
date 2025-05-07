.. _ref_auth_http:

========
HTTP API
========

Your application server will interact with the Gel extension primarily by sending HTTP requests to the Gel server. This page describes the HTTP API exposed by the Gel server. For more in-depth guidance about integrating Gel Auth into your application, see :ref:`ref_guide_auth` for a reference example.

The following sections are organized by authentication type.

Responses
=========

Responses typically include a JSON object that include a ``code`` property that can be exchanged for an access token by providing the matching PKCE verifier associated with the ``code``. Some endpoints can be configured to return responses as redirects and include response data in the redirect location's query string.

General
=======

POST /token
-----------

PKCE token exchange endpoint.

Email and password
==================

POST /register
--------------

Register a new user with email and password.

POST /authenticate
------------------

Authenticate a user using email and password.

POST /send-reset-email
----------------------

Send a reset email to a user.

POST /reset-password
--------------------

Reset a user's password.

POST /verify
------------

Verify a user's email.

POST /resend-verification-email
-------------------------------

Resend a verification email to a user.


OAuth
=====

POST /authorize
---------------

Initiate an OAuth authorization flow.

POST /callback
--------------

Handle the redirect from the OAuth provider.

WebAuthn
========

POST /webauthn/register
-----------------------

Register a new WebAuthn credential.

POST /webauthn/authenticate
---------------------------

Authenticate a user using a WebAuthn credential.

GET /webauthn/register/options
------------------------------

Get options for WebAuthn registration.

GET /webauthn/authenticate/options
----------------------------------

Get options for WebAuthn authentication.

POST /verify
------------

Verify a user's email.

POST /resend-verification-email
-------------------------------

Resend a verification email to a user.

Magic link
==========

POST /magic-link/register
-------------------------

Register a new magic link credential.

POST /magic-link/email
----------------------

Send a magic link email to a user.

POST /magic-link/authenticate
-----------------------------

Sign in a user using the token created in a Magic Link email.
