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

**Request Body (JSON):**

*   ``email`` (string, required): The user's email address.
*   ``password`` (string, required): The user's desired password.
*   ``provider`` (string, required): The name of the provider to use (e.g., "emailpassword").
*   ``challenge`` (string, optional): A PKCE code challenge. This is required if the provider is configured with ``require_verification: false``.
*   ``redirect_to`` (string, optional): A URL to redirect to upon successful registration.
*   ``verify_url`` (string, optional): The base URL for the email verification link. If not provided, it defaults to ``<auth_server_base_url>/ui/verify``. The verification token will be appended as a query parameter to this URL.
*   ``redirect_on_failure`` (string, optional): A URL to redirect to if registration fails.

**Response:**

The behavior of the response depends on the request parameters and server-side provider configuration (specifically, ``require_verification``).

1.  **Successful Registration with Email Verification Required:**

    *   This occurs if the provider has ``require_verification: true``.
    *   A verification email is sent to the user.
    *   If ``redirect_to`` is provided in the request:

        *   A 302 redirect to the ``redirect_to`` URL occurs.
        *   The redirect URL will include ``identity_id`` and ``verification_email_sent_at`` as query parameters.

    *   If ``redirect_to`` is NOT provided:

        *   A 201 Created response is returned with a JSON body:

            .. code-block:: json

              {
                "identity_id": "...",
                "verification_email_sent_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ"
              }

2.  **Successful Registration with Email Verification NOT Required (PKCE Flow):**

    *   This occurs if the provider has ``require_verification: false``. The ``challenge`` parameter is mandatory in the request.
    *   A verification email is still sent, but it's not required for the user to verify their email to get an access token.
    *   If ``redirect_to`` is provided in the request:

        *   A 302 redirect to the ``redirect_to`` URL occurs.
        *   The redirect URL will include ``code`` (the PKCE authorization code) and ``provider`` as query parameters.

    *   If ``redirect_to`` is NOT provided:

        *   A 201 Created response is returned with a JSON body:

            .. code-block:: json

              {
                "code": "...",
                "provider": "..."
              }

3.  **Registration Failure:**

    *   If ``redirect_on_failure`` is provided in the request and is an allowed URL:

        *   A 302 redirect to the ``redirect_on_failure`` URL occurs.
        *   The redirect URL will include ``error`` (a description of the error) and ``email`` (the submitted email) as query parameters.

    *   Otherwise (no ``redirect_on_failure`` or it's not allowed):

        *   An HTTP error response (e.g., 400 Bad Request, 500 Internal Server Error) is returned with a JSON body describing the error. For example:

            .. code-block:: json

              {
                "message": "Error description",
                "type": "ErrorType",
                "code": "ERROR_CODE"
              }

**Common Error Scenarios:**

*   Missing ``provider`` in the request.
*   Missing ``challenge`` in the request when the provider has ``require_verification: false``.
*   Email already exists.
*   Invalid password (e.g., too short, if policies are enforced).

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
