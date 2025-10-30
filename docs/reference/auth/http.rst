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

Exchanges a PKCE authorization code (obtained from a successful registration, authentication, or email verification flow that included a PKCE challenge) for a session token.

**Request Parameters (Query String):**

*   ``code`` (string, required): The PKCE authorization code that was previously issued.
*   ``verifier`` (string, required, also accepts ``code_verifier``): The PKCE code verifier string (plaintext, typically 43-128 characters) that was originally used to generate the ``code_challenge``.

**Response:**

1.  **Successful Token Exchange:**

    *   This occurs if the ``code`` is valid, and the provided ``verifier`` correctly matches the ``challenge`` associated with the ``code``.
    *   The PKCE ``code`` is consumed and cannot be reused.
    *   A 200 OK response is returned with a JSON body containing the session token and identity information:

        .. code-block:: json

            {
              "auth_token": "your_new_session_jwt",
              "identity_id": "the_users_identity_id",
              "provider_token": "optional_oauth_provider_access_token",
              "provider_refresh_token": "optional_oauth_provider_refresh_token",
              "provider_id_token": "optional_oauth_provider_id_token"
            }

        .. note::

          ``provider_token``, ``provider_refresh_token``, and ``provider_id_token`` are only populated if the PKCE flow originated from an interaction with an external OAuth provider that returned these tokens.

2.  **PKCE Verification Failed:**

    *   The ``code`` was found, but the ``verifier`` did not match the stored challenge.
    *   An HTTP error response 403 Forbidden with a JSON body indicating ``PKCEVerificationFailed``.

3.  **Unknown Code:**

    *   The provided ``code`` was not found.
    *   An HTTP error response 403 Forbidden with a JSON body indicating "NoIdentityFound".

4.  **Code found, but not associated with an Identity:**

    *   The ``code`` was found, but it is not associated with a user identity.
    *   An HTTP error response 400 Bad Request with a JSON body indicating "InvalidData".

5.  **Invalid Verifier Length:**

    *   The ``verifier`` string is shorter than 43 characters or longer than 128 characters.
    *   An HTTP 400 Bad Request response with a JSON body detailing the length requirement.

6.  **Missing Parameters:**

    *   Either ``code`` or ``verifier`` (or ``code_verifier``) is missing from the query string.
    *   An HTTP 400 Bad Request response with a JSON body indicating the missing parameter.

Email and password
==================

POST /register
--------------

Register a new user with email and password.

**Request Body (JSON):**

*   ``email`` (string, required): The user's email address.
*   ``password`` (string, required): The user's desired password.
*   ``provider`` (string, required): The name of the provider to use: ``builtin::local_emailpassword``
*   ``challenge`` (string, optional): A PKCE code challenge. This is required if the provider is configured with ``require_verification: false`` since registering will also authenticate and authentication is protected by a PKCE code exchange.
*   ``redirect_to`` (string, optional): A URL to redirect to upon successful registration.
*   ``verify_url`` (string, optional): The base URL for the email verification link. If not provided, it defaults to ``<auth_server_base_url>/ui/verify``, the built-in UI endpoint for verifying email addresses. The verification token will be appended as a query parameter to this URL.
*   ``redirect_on_failure`` (string, optional): A URL to redirect to if registration fails.

.. note::

  The verification email sent after registration depends on your provider's verification method:

  - **Code**: users receive a one-time code and must call ``POST /verify`` with ``provider``, ``email`` and the ``code``.
  - **Link**: users receive a verification link that carries a ``verification_token`` and must call ``POST /verify`` with ``provider`` and the ``verification_token`` (often done by following the link).

**Response:**

The behavior of the response depends on the request parameters and server-side provider configuration (specifically, ``require_verification``).

1.  **Successful Registration with Email Verification Required:**

    *   This occurs if the provider has ``require_verification: true``.
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

**Request Body (JSON):**

*   ``email`` (string, required): The user's email address.
*   ``password`` (string, required): The user's password.
*   ``provider`` (string, required): The name of the provider to use: ``builtin::local_emailpassword``
*   ``challenge`` (string, required): A PKCE code challenge.
*   ``redirect_to`` (string, optional): A URL to redirect to upon successful authentication.
*   ``redirect_on_failure`` (string, optional): A URL to redirect to if authentication fails. If not provided, but ``redirect_to`` is, ``redirect_to`` will be used as the fallback for failure redirection.

**Response:**

The behavior of the response depends on the request parameters and the outcome of the authentication attempt.

1.  **Successful Authentication:**

    *   A PKCE authorization code is generated and associated with the user's session.
    *   If ``redirect_to`` is provided in the request:

        *   A 302 redirect to the ``redirect_to`` URL occurs.
        *   The redirect URL will include a ``code`` (the PKCE authorization code) as a query parameter.

    *   If ``redirect_to`` is NOT provided:

        *   A 200 OK response is returned with a JSON body:

            .. code-block:: json

                {
                  "code": "..."
                }

2.  **Authentication Failure (e.g., invalid credentials, user not found):**

    *   If ``redirect_on_failure`` (or ``redirect_to`` as a fallback) is provided in the request and is an allowed URL:

        *   A 302 redirect to this URL occurs.
        *   The redirect URL will include ``error`` (a description of the error) and ``email`` (the submitted email) as query parameters.

    *   Otherwise (no applicable redirect URL or it's not allowed):

        *   An HTTP error response (e.g., 400, 401) is returned with a JSON body describing the error. For example:

            .. code-block:: json

                {
                  "message": "Invalid credentials",
                  "type": "InvalidCredentialsError",
                  "code": "INVALID_CREDENTIALS"
                }

3.  **Email Verification Required:**

    *   This occurs if the provider is configured with ``require_verification: true`` and the user has not yet verified their email address.
    *   The response follows the same logic as **Authentication Failure**:

        *   If ``redirect_on_failure`` (or ``redirect_to``) is provided, a redirect occurs with an error like "VerificationRequired".
        *   Otherwise, an HTTP error (often 403 Forbidden) is returned with a JSON body indicating that email verification is required.

**Common Error Scenarios:**

*   Missing required fields in the request: ``email``, ``password``, ``provider``, or ``challenge``.
*   Invalid email or password.
*   User account does not exist.
*   User account exists but email is not verified (if ``require_verification: true`` for the provider).

POST /send-reset-email
----------------------

Send a password reset email to a user.

**Request Body (JSON):**

*   ``provider`` (string, required): The name of the provider: ``builtin::local_emailpassword``.
*   ``email`` (string, required): The email address of the user requesting the password reset.
*   ``reset_url`` (string, required): The base URL for the password reset page (used for the Link method). The ``reset_token`` will be appended as a query parameter. This URL must be an allowed redirect URI in the server configuration.
*   ``challenge`` (string, required): A PKCE code challenge. For the Link method it is embedded in the ``reset_token``; for the Code method it can be re-used later when completing the reset to obtain a PKCE code.
*   ``redirect_to`` (string, optional): A URL to redirect to after the reset email has been successfully queued for sending.
*   ``redirect_on_failure`` (string, optional): A URL to redirect to if there's an error during the process. If not provided, but ``redirect_to`` is, ``redirect_to`` will be used as the fallback for failure redirection.

.. note::

  The email sent depends on your provider's configuration:

  - **Link**: a reset link is sent containing a ``reset_token``; the user should then call ``POST /reset-password`` with this token.
  - **Code**: a one-time code is sent to the email address; the user should then call ``POST /reset-password`` with ``email`` and ``code`` (and optionally ``challenge`` to receive a PKCE code).

**Response:**

The endpoint always attempts to respond in a way that does not reveal whether an email address is registered or not.

1.  **Reset Email Queued (or User Not Found):**

    *   If the user exists, a password reset email is generated and sent.
    *   If the user does not exist, the server simulates a successful send to prevent email enumeration attacks.
    *   If ``redirect_to`` is provided in the request:

        *   A 302 redirect to the ``redirect_to`` URL occurs.
        *   The redirect URL will include ``email_sent`` (the email address provided in the request) as a query parameter.

    *   If ``redirect_to`` is NOT provided:

        *   A 200 OK response is returned with a JSON body:

            .. code-block:: json

                {
                  "email_sent": "user@example.com"
                }

2.  **Failure (e.g., ``reset_url`` not allowed, SMTP server error):**

    *   This occurs for errors not related to whether the user exists, such as configuration issues or mail server problems.
    *   If ``redirect_on_failure`` (or ``redirect_to`` as a fallback) is provided in the request and is an allowed URL:

        *   A 302 redirect to this URL occurs.
        *   The redirect URL will include ``error`` (a description of the error) and ``email`` (the submitted email) as query parameters.

    *   Otherwise (no applicable redirect URL or it's not allowed):

        *   An HTTP error response (e.g., 400 Bad Request, 500 Internal Server Error) is returned with a JSON body describing the error.

**Common Error Scenarios (leading to the Failure response):**

*   Missing required fields in the request: ``provider``, ``email``, ``reset_url``, or ``challenge``.
*   The provided ``reset_url`` is not in the server's list of allowed redirect URIs.
*   Internal server error during email dispatch (e.g., SMTP configuration issues).

POST /reset-password
--------------------

Resets a user's password using a reset token and a new password. This endpoint completes the password reset flow initiated by ``POST /send-reset-email``.

**Request Body (JSON):**

*   ``provider`` (string, required): The name of the provider: ``builtin::local_emailpassword``.
*   ``password`` (string, required): The new password for the user's account.

Choose one of the following modes:

-  **Token mode (Link method)**

   *   ``reset_token`` (string, required): The token that was emailed to the user.

-  **Code mode**

   *   ``email`` (string, required): The user's email address.
   *   ``code`` (string, required): The one-time code sent by email.
   *   ``challenge`` (string, optional): If provided, a PKCE authorization code will be generated upon success.

Optional for both modes:

*   ``redirect_to`` (string, optional): A URL to redirect to after the password has been successfully reset. If provided and a PKCE code is generated, it will be appended as a query parameter.
*   ``redirect_on_failure`` (string, optional): A URL to redirect to if the password reset process fails. If not provided, but ``redirect_to`` is, ``redirect_to`` will be used as the fallback.

**Response:**

-  **Token mode (Link method)**

   *   The ``reset_token`` is validated, and the user's password is updated.
   *   A PKCE authorization ``code`` is generated using the challenge embedded in the token.
   *   If ``redirect_to`` is provided, a 302 redirect occurs with ``code`` appended; otherwise, a 200 OK JSON response is returned with ``{"code": "..."}``.

-  **Code mode**

   *   The ``email``/``code`` are validated, and the user's password is updated.
   *   If a ``challenge`` is provided, a PKCE authorization ``code`` is generated.
   *   If ``redirect_to`` is provided and a PKCE code was generated, a 302 redirect occurs with ``code`` appended; if ``challenge`` was not provided, a 200 OK JSON response is returned with ``{"status": "password_reset"}``.

-  **Failure (invalid inputs or server error)**

   *   If ``redirect_on_failure`` (or ``redirect_to`` as a fallback) is provided and is an allowed URL, a 302 redirect occurs with an ``error`` parameter (and submitted ``reset_token``/``email`` where applicable).
   *   Otherwise, an HTTP error response is returned with a JSON error body (e.g., 400, 403, 500).

**Common Error Scenarios:**

*   Missing required fields in the request: ``provider``, ``reset_token``, or ``password``.
*   The ``reset_token`` is malformed, has an invalid signature, or is expired.
*   Internal server error during the password update process.

Email verification
==================

These endpoints apply to the Email and password provider, as well as the WebAuthn provider. Verification emails are sent even if you do not *require* verification. The difference between requiring verification and not is that if you require verification, the user must verify their email before they can authenticate. If you do not require verification, the user can authenticate without verifying their email.

POST /verify
------------

Verify a user's email address. Supports both Link and Code methods.

**Request Body (JSON):**

*   ``provider`` (string, required): The provider name, e.g., ``builtin::local_emailpassword`` or ``builtin::local_webauthn``.

Choose exactly one verification mode:

-  **Link mode**

   *   ``verification_token`` (string, required): The JWT sent to the user (typically via an email link) to verify their email.

-  **Code mode**

   *   ``email`` (string, required): The user's email address to verify.
   *   ``code`` (string, required): The one-time code sent via email.
   *   ``challenge`` (string, optional, also accepts ``code_challenge``): If provided, a PKCE authorization code will be generated upon success.
   *   ``redirect_to`` (string, optional): If provided, a redirect response will be sent upon success. This URL must be in the server's list of allowed redirect URIs.

**Response:**

-  **Link mode**

   The primary action is to validate the ``verification_token`` and mark the associated email as verified. The exact response depends on the contents of the ``verification_token`` (it may include a PKCE challenge and/or a redirect URL specified during its creation):

   1.  With challenge and redirect URL in token

       *   A PKCE authorization code is generated using the challenge from the token.
       *   A 302 redirect to the URL specified in the token (``maybe_redirect_to``) occurs, with ``code`` appended as a query parameter.

   2.  With challenge only in token

       *   A PKCE authorization code is generated using the challenge from the token.
       *   A 200 OK response is returned with a JSON body:

           .. code-block:: json

               {
                 "code": "generated_pkce_code"
               }

   3.  With redirect URL only in token

       *   A 302 redirect to the URL specified in the token (``maybe_redirect_to``) occurs (no ``code`` is added).

   4.  No challenge or redirect URL in token

       *   A 204 No Content response is returned.

   5.  Invalid or expired token

       *   A 403 Forbidden response is returned with a JSON body (e.g., token expired).

-  **Code mode**

   After validating ``email`` and ``code`` and marking the email as verified, behavior depends on optional ``challenge`` and ``redirect_to``:

   1.  ``challenge`` and ``redirect_to`` provided

       *   A PKCE authorization code is generated and a 302 redirect to ``redirect_to`` occurs with ``code`` appended as a query parameter.

   2.  Only ``challenge`` provided

       *   A PKCE authorization code is generated and a 200 OK response is returned with a JSON body:

           .. code-block:: json

               {
                 "code": "generated_pkce_code"
               }

   3.  Only ``redirect_to`` provided

       *   A 302 redirect to ``redirect_to`` occurs (no PKCE code is generated).

   4.  Neither provided

       *   A 204 No Content response is returned.

**Common Error Scenarios:**

*   Missing ``provider`` or ``verification_token`` in the request (results in HTTP 400).
*   The ``verification_token`` is malformed, has an invalid signature, or is expired (results in HTTP 403).
*   An internal error occurs while trying to update the email verification status (results in HTTP 500).

POST /resend-verification-email
-------------------------------

Resend a verification email to a user. This can be useful if the original email was lost or the token expired.

**Request Body (JSON):**

The request must include ``provider`` and a way to identify the user's email factor.

*   ``provider`` (string, required): The provider name, e.g., ``builtin::local_emailpassword`` or ``builtin::local_webauthn``.

Then, choose **one** of the following methods to specify the user:

*   **Method 1: Using an existing Verification Token**

    *   ``verification_token`` (string): An old (even expired) verification token. The system will extract necessary details (like ``identity_id``, original ``verify_url``, ``challenge``, and ``redirect_to``) from this token to generate a new one.

*   **Method 2: Using Email Address (for Email/Password provider)**

    *   ``email`` (string, required if ``provider`` is ``builtin::local_emailpassword`` and ``verification_token`` is not used): The user's email address.
    *   ``verify_url`` (string, optional): The base URL for the new verification link. Defaults to the server's configured UI verify path (e.g., ``<base_path>/ui/verify``).
    *   ``challenge`` (string, optional, also accepts ``code_challenge``): A PKCE code challenge to be embedded in the new verification token.
    *   ``redirect_to`` (string, optional): A URL to redirect to after successful verification using the new token. This URL must be in the server's list of allowed redirect URIs.

*   **Method 3: Using WebAuthn Credential ID (for WebAuthn provider)**

    *   ``credential_id`` (string, required if ``provider`` is ``builtin::local_webauthn`` and ``verification_token`` is not used): The Base64 encoded WebAuthn credential ID.
    *   ``verify_url`` (string, optional): As above.
    *   ``challenge`` (string, optional, also accepts ``code_challenge``): As above.
    *   ``redirect_to`` (string, optional): As above. This URL must be in the server's list of allowed redirect URIs.

**Response:**

The endpoint aims to prevent email enumeration by always returning a successful status code if the request format is valid, regardless of whether the user or email factor was found.

1.  **Verification Email Queued (or User/Email Factor Not Found):**

    *   If the user/email factor is found, a new verification email with a fresh token is generated and sent.
    *   If the user/email factor is not found (based on the provided identifier), the server simulates a successful send.
    *   A 200 OK response is returned. The response body is typically empty.

2.  **Failure (Invalid Request or Server Error):**

    *   If the request is malformed (e.g., unsupported ``provider``, ``redirect_to`` URL not allowed, missing required fields for the chosen identification method), an HTTP 400 Bad Request with a JSON error body is returned.
    *   If an internal server error occurs (e.g., SMTP issues), an HTTP 500 Internal Server Error with a JSON error body is returned.

**Common Error Scenarios:**

*   Unsupported ``provider`` name.
*   Missing ``verification_token`` when it's the chosen method, or missing ``email`` / ``credential_id`` for other methods.
*   Providing a ``redirect_to`` URL that is not in the allowed list.
*   Internal SMTP errors preventing email dispatch.

.. note::

  If the provider uses the **Code** verification method, the resend email will contain a one-time code instead of a link. In this case, ``verify_url``, ``challenge``, and ``redirect_to`` are not included in the email and are only relevant for the Link method.

OAuth
=====

POST /authorize
---------------

Initiate an OAuth authorization flow.

**Request Parameters (Query String):**

*   ``provider`` (string, required): The name of the OAuth provider to use (e.g., ``builtin::oauth::google``).
*   ``redirect_to`` (string, required): The URL to redirect to after a successful OAuth flow completes and a PKCE code is obtained. This URL must be in the server's list of allowed redirect URIs.
*   ``challenge`` (string, required, also accepts ``code_challenge``): A PKCE code challenge generated by your application.
*   ``redirect_to_on_signup`` (string, optional): An alternative URL to redirect to after a *new* user successfully completes the OAuth flow. If not provided, ``redirect_to`` will be used for both new and existing users. This URL must also be in the server's list of allowed redirect URIs.
*   ``callback_url`` (string, optional): The URL the OAuth provider should redirect back to after the user authorizes the application. If not provided, it defaults to ``<auth_server_base_url>/callback``. This URL must be in the server's list of allowed redirect URIs.

**Response:**

1.  **Successful Authorization Initiation:**

    *   The server generates a PKCE challenge record and prepares for the OAuth flow.
    *   A 302 Found redirect response is returned.
    *   The ``Location`` header will contain the authorization URL provided by the external OAuth identity provider. The user's browser will be directed to this URL to begin the OAuth provider's authentication/authorization process.

**Common Error Scenarios:**

*   Missing required fields in the query string: ``provider``, ``redirect_to``, or ``challenge``.
*   The provided ``redirect_to``, ``redirect_to_on_signup``, or ``callback_url`` is not in the server's list of allowed redirect URIs.
*   Configuration error on the server (e.g., the specified provider is not configured).

POST /callback
--------------

Handle the redirect from the OAuth provider. This endpoint is typically called by the OAuth provider after the user has completed the authentication and authorization process on the provider's site. It processes the response from the provider, exchanges the authorization code for Gel session information (and potentially provider tokens), and redirects the user back to the application.

This endpoint accepts parameters either in the query string (for GET requests) or in the request body as ``application/x-www-form-urlencoded`` (for POST requests).

**Request Parameters (Query String or Form Data):**

*   ``state`` (string, required): The state parameter originally sent in the ``POST /authorize`` request. This is a signed JWT containing information needed to complete the flow (like provider name, redirect URLs, and the PKCE challenge).
*   ``code`` (string, optional): The authorization code provided by the OAuth identity provider. This is present on successful authorization.
*   ``error`` (string, optional): An error code provided by the OAuth identity provider, if authorization failed.
*   ``error_description`` (string, optional): A human-readable description of the error provided by the OAuth identity provider.

**Response:**

1.  **Successful Callback and Token Exchange:**

    *   This occurs when the OAuth provider returns a ``code``, and the ``state`` is valid.
    *   The server exchanges the OAuth code for identity information and potentially provider access/refresh tokens.
    *   The identity is linked to the PKCE challenge provided in the original ``state``.
    *   A 302 Found redirect response is returned.
    *   The ``Location`` header will contain the ``redirect_to`` (or ``redirect_to_on_signup`` if applicable) URL specified in the original ``state`` parameter.
    *   The redirect URL will include the Gel PKCE authorization ``code`` and the ``provider`` name as query parameters (e.g., ``https://app.example.com/success?code=gel_pkce_code&provider=oauth_provider_name``). This PKCE code can then be exchanged for a session token via ``POST /token``.

2.  **OAuth Provider Returned an Error:**

    *   This occurs when the OAuth provider redirects back with an ``error`` parameter.
    *   A 302 Found redirect response is returned.
    *   The ``Location`` header will contain the ``redirect_to`` URL specified in the original ``state`` parameter.
    *   The redirect URL will include the ``error`` and optionally ``error_description`` and the user's ``email`` (if available and relevant) as query parameters.

**Common Error Scenarios (before redirect):**

*   Missing ``state`` parameter in the request.
*   Invalid or malformed ``state`` token.
*   The OAuth provider did not return either a ``code`` or an ``error``.
*   Errors during the server's exchange of the OAuth code with the provider (these typically result in an HTTP error response from this endpoint rather than a redirect with an error).

WebAuthn
========

POST /webauthn/register
-----------------------

Register a new WebAuthn credential for a user. This typically follows a call to ``GET /webauthn/register/options`` where the registration options were obtained.

**Request Body (JSON):**

*   ``provider`` (string, required): The name of the WebAuthn provider to use: ``builtin::local_webauthn``.
*   ``challenge`` (string, required): A PKCE code challenge. This challenge will be linked to the identity upon successful registration if email verification is not required.
*   ``email`` (string, required): The user's email address associated with the WebAuthn credential.
*   ``credentials`` (string, required): The credential data obtained from the client-side WebAuthn API (``navigator.credentials.create()``). This should be a JSON string.
*   ``verify_url`` (string, required): The base URL for the email verification link that will be emailed to the user if email verification is required.
*   ``user_handle`` (string, optional): The Base64 URL encoded user handle generated during the options request. This can also be passed via a cookie named ``edgedb-webauthn-registration-user-handle``.

**Request Cookies:**

*   ``edgedb-webauthn-registration-user-handle`` (string, optional): The Base64 URL encoded user handle generated during the options request. If present, this overrides the ``user_handle`` in the request body.

**Response:**

The response depends on whether the WebAuthn provider is configured to require email verification or not.

1.  **Successful Registration with Email Verification Required:**

    *   A 201 Created response is returned with a JSON body:

        .. code-block:: json

          {
            "identity_id": "...",
            "verification_email_sent_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ"
          }

    *   The ``edgedb-webauthn-registration-user-handle`` cookie is cleared.

2.  **Successful Registration with Email Verification NOT Required (PKCE Flow):**

    *   A 201 Created response is returned with a JSON body:

        .. code-block:: json

          {
            "code": "...",
            "provider": "builtin::local_webauthn"
          }

    *   The ``edgedb-webauthn-registration-user-handle`` cookie is cleared. The returned ``code`` can be exchanged for a session token at the ``POST /token`` endpoint.

**Common Error Scenarios:**

*   Missing required fields in the request body or user handle (either in body or cookie).
*   Invalid or malformed ``credentials`` or ``user_handle`` data.
*   The specified ``verify_url`` is not in the server's list of allowed redirect URIs.
*   Errors during the WebAuthn registration process on the server (e.g., credential already registered).
*   Configuration error on the server (e.g., WebAuthn provider not configured).

POST /webauthn/authenticate
---------------------------

Authenticate a user using an existing WebAuthn credential. This typically follows a call to ``GET /webauthn/authenticate/options`` where the authentication options were obtained.

**Request Body (JSON):**

*   ``provider`` (string, required): The name of the WebAuthn provider to use: ``builtin::local_webauthn``.
*   ``challenge`` (string, required): A PKCE code challenge. This challenge will be linked to the authenticated identity upon successful authentication.
*   ``email`` (string, required): The user's email address associated with the WebAuthn credential they are attempting to use.
*   ``assertion`` (string, required): The assertion data obtained from the client-side WebAuthn API (``navigator.credentials.get()``). This should be a JSON string.

**Response:**

1.  **Successful Authentication:**

    *   This occurs when the provided ``assertion`` successfully verifies the user's identity based on the provided ``email``.
    *   If email verification is required for the provider, the user's email must also be verified.
    *   A PKCE authorization ``code`` is generated and linked to the authenticated identity using the provided ``challenge``.
    *   A 200 OK response is returned with a JSON body:

        .. code-block:: json

          {
            "code": "..."
          }

    *   The returned ``code`` can be exchanged for a session token at the ``POST /token`` endpoint.

2.  **Authentication Failure:**

    *   This occurs if the provided ``assertion`` does not match the registered credential for the given email, the email is not found, or if email verification is required but the email is not verified.
    *   An HTTP error response (e.g., 401 Unauthorized or 403 Forbidden) is returned with a JSON body describing the error (e.g., "Failed to authenticate WebAuthn", "VerificationRequired").

**Common Error Scenarios:**

*   Missing required fields in the request body: ``challenge``, ``email``, or ``assertion``.
*   Invalid or malformed ``assertion`` data.
*   No WebAuthn credential found for the provided email.
*   WebAuthn authentication failed (e.g., invalid signature).
*   Email verification is required for the provider, but the user's email is not verified.
*   Configuration error on the server (e.g., WebAuthn provider not configured).

GET /webauthn/register/options
------------------------------

Get the necessary options from the server to initiate a WebAuthn registration ceremony on the client side (using ``navigator.credentials.create()``).

**Request Parameters (Query String):**

*   ``email`` (string, required): The user's email address for whom registration options are being requested.

**Response:**

1.  **Successful Options Retrieval:**

    *   A 200 OK response is returned.
    *   The ``Content-Type`` header is ``application/json``.
    *   The response body contains a JSON object with the WebAuthn registration options, compatible with the Web Authentication API (``PublicKeyCredentialCreationOptions``).
    *   A cookie named ``edgedb-webauthn-registration-user-handle`` is set containing the Base64 URL encoded user handle generated by the server. This cookie is needed for the subsequent ``POST /webauthn/register`` request.

**Common Error Scenarios:**

*   Missing required ``email`` query parameter.
*   Configuration error on the server (e.g., WebAuthn provider not configured).
*   Errors during the generation of registration options on the server.

GET /webauthn/authenticate/options
----------------------------------

Get the necessary options from the server to initiate a WebAuthn authentication ceremony on the client side (using ``navigator.credentials.get()``).

**Request Parameters (Query String):**

*   ``email`` (string, required): The user's email address for whom authentication options are being requested. The server will look up associated WebAuthn credentials based on this email.

**Response:**

1.  **Successful Options Retrieval:**

    *   A 200 OK response is returned.
    *   The ``Content-Type`` header is ``application/json``.
    *   The response body contains a JSON object with the WebAuthn authentication options, compatible with the Web Authentication API (``PublicKeyCredentialRequestOptions``). These options will include information about the user's registered credentials to challenge the client.

**Common Error Scenarios:**

*   Missing required ``email`` query parameter.
*   Configuration error on the server (e.g., WebAuthn provider not configured).
*   Errors during the generation of authentication options on the server (e.g., no credentials found for the email).

Magic link
==========

POST /magic-link/register
-------------------------

Registers a new user with a magic link credential and sends a magic link email to their email address.

**Request Body (JSON or application/x-www-form-urlencoded):**

The required fields depend on the provider's verification method.

-  **Code method**

   *   ``email`` (string, required): The user's email address.
   *   ``redirect_to`` (string, optional): A URL to redirect to after the email has been queued. If omitted, the request must accept ``application/json``.

-  **Link method**

   *   ``email`` (string, required): The user's email address.
   *   ``challenge`` (string, required): A PKCE code challenge that will be embedded in the magic link token.
   *   ``callback_url`` (string, required): The URL that the user will be redirected to after clicking the magic link in the email. A PKCE authorization ``code`` will be appended to this URL. This URL must be in the server's list of allowed redirect URIs.
   *   ``redirect_on_failure`` (string, required): A URL to redirect to if there's an error during the registration or email sending process. Error details will be appended as query parameters. This URL must be in the server's list of allowed redirect URIs.
   *   ``redirect_to`` (string, optional): A URL to redirect to *after* the server has successfully queued the email for sending (before the user clicks the link). If provided, a JSON response will not be returned, and parameters like ``email_sent`` (or ``code=true`` in Code method) will be appended as query parameters. This URL must be in the server's list of allowed redirect URIs.
   *   ``link_url`` (string, optional): The base URL for the magic link itself (the endpoint the link in the email will point to). If not provided, it defaults to ``<auth_server_base_url>/magic-link/authenticate``. This URL must be in the server's list of allowed redirect URIs.

**Response:**

The endpoint attempts to prevent email enumeration by always returning a success status if the request format is valid.

-  **Code method**

   *   If the request accepts ``application/json`` and ``redirect_to`` is not provided, a 200 OK JSON response is returned:

       .. code-block:: json

           {
             "code": "true",
             "signup": "true",
             "email": "user@example.com"
           }

   *   If ``redirect_to`` is provided, a 302 Found redirect occurs to ``redirect_to`` with ``code=true``, ``signup=true`` and ``email`` as query parameters.

-  **Link method**

   *   If the request accepts ``application/json`` and ``redirect_to`` is not provided, a 200 OK JSON response is returned:

       .. code-block:: json

           {
             "email_sent": "user@example.com"
           }

   *   If ``redirect_to`` is provided, a 302 Found redirect occurs to ``redirect_to`` with ``email_sent`` as a query parameter.

-  **Failure**

   *   If an error occurs before a redirect would occur and the request accepts JSON, an HTTP error response (e.g., 400 Bad Request) is returned with a JSON body.
   *   Otherwise, if ``redirect_on_failure`` was provided (Link method), a 302 Found redirect occurs to that URL with ``error`` and ``email`` query parameters.

**Common Error Scenarios (leading to failure responses):**

*   Missing required fields in the request body: ``provider``, ``email``, ``challenge``, ``callback_url``, or ``redirect_on_failure``.
*   The provided ``callback_url``, ``redirect_on_failure``, ``redirect_to``, or ``link_url`` is not in the server's list of allowed redirect URIs.
*   Unsupported ``provider`` name.
*   Internal server error during email dispatch (e.g., SMTP issues).

POST /magic-link/email
----------------------

Sends a magic link email to a user with an *existing* magic link credential. This is similar to ``POST /magic-link/register`` but does not attempt to create a new identity if the email is not found (though it still simulates a successful send to prevent enumeration).

**Request Body (JSON or application/x-www-form-urlencoded):**

The required fields depend on the provider's verification method.

-  **Code method**

   *   ``email`` (string, required): The user's email address.
   *   ``redirect_to`` (string, optional): A URL to redirect to after the email has been queued. If omitted, the response will be JSON.

-  **Link method**

   *   ``email`` (string, required): The user's email address.
   *   ``challenge`` (string, required): A PKCE code challenge that will be embedded in the magic link token.
   *   ``callback_url`` (string, required): The URL that the user will be redirected to after clicking the magic link in the email. A PKCE authorization ``code`` will be appended to this URL. This URL must be in the server's list of allowed redirect URIs.
   *   ``redirect_on_failure`` (string, required): A URL to redirect to if there's an error during the email sending process. Error details will be appended as query parameters. This URL must be in the server's list of allowed redirect URIs.
   *   ``redirect_to`` (string, optional): A URL to redirect to *after* the server has successfully queued the email for sending (before the user clicks the link). If provided, a JSON response will not be returned.
   *   ``link_url`` (string, optional): The base URL for the magic link itself. If not provided, it defaults to ``<auth_server_base_url>/magic-link/authenticate``. This URL must be in the server's list of allowed redirect URIs.

**Response:**

The endpoint attempts to prevent email enumeration by always returning a success status if the request format is valid, even if the email address is not found.

-  **Code method**

   *   If ``redirect_to`` is NOT provided, a 200 OK JSON response is returned:

       .. code-block:: json

           {
             "code": "true",
             "email": "user@example.com"
           }

   *   If ``redirect_to`` is provided, a 302 Found redirect occurs to the ``redirect_to`` URL with ``code=true`` and ``email`` as query parameters.

-  **Link method**

   *   If ``redirect_to`` is NOT provided, a 200 OK JSON response is returned:

       .. code-block:: json

           {
             "email_sent": "user@example.com"
           }

   *   If ``redirect_to`` is provided, a 302 Found redirect occurs to the ``redirect_to`` URL with ``email_sent`` as a query parameter.

-  **Failure**

   *   If an error happens and a ``redirect_on_failure`` URL was provided (Link method), a 302 Found redirect is returned to that URL with ``error`` and the submitted ``email`` as query parameters. Otherwise, an HTTP error response is returned with a JSON body.

**Common Error Scenarios (leading to failure responses):**

*   Missing required fields in the request body: ``provider``, ``email``, ``challenge``, ``callback_url``, or ``redirect_on_failure``.
*   The provided ``callback_url``, ``redirect_on_failure``, ``redirect_to``, or ``link_url`` is not in the server's list of allowed redirect URIs.
*   Unsupported ``provider`` name.
*   Internal server error during email dispatch (e.g., SMTP issues).

POST /magic-link/authenticate
-----------------------------

Authenticates a user by validating a magic link token received from an email. This endpoint is typically the target of the magic link URL sent to the user.

This endpoint supports both Link and Code methods.

**Link method (Query String):**

*   ``token`` (string, required): The magic link token (a signed JWT) extracted from the magic link URL. This token contains the identity ID, the original PKCE challenge, and the callback URL.
*   ``redirect_on_failure`` (string, optional): A URL to redirect to if the authentication process fails (e.g., invalid or expired token). Error details will be appended as query parameters. If not provided, an HTTP error response will be returned on failure.

**Code method (JSON body):**

*   ``email`` (string, required): The user's email address.
*   ``code`` (string, required): The one-time code sent via email.
*   ``callback_url`` (string, required): The URL to redirect to after successful authentication. Must be an allowed redirect URI.
*   ``challenge`` (string, required): A PKCE code challenge. A PKCE authorization ``code`` will be generated upon success.

**Response:**

-  **Link method**

   *   If the provided ``token`` is valid, the user's email factor is marked as verified and a PKCE authorization ``code`` is generated using the challenge embedded in the token. A 302 Found redirect is returned to the token's ``callback_url`` with ``code`` appended.
   *   On failure, if ``redirect_on_failure`` is provided, a 302 redirect occurs to that URL with an ``error`` parameter; otherwise, an HTTP error response is returned with a JSON body.

-  **Code method**

   *   On success, the one-time code is validated, the email factor is marked as verified, and a PKCE authorization ``code`` is generated using the provided ``challenge``. A 302 Found redirect occurs to ``callback_url`` with ``code`` appended.
   *   On failure, if a ``redirect_on_failure`` query parameter is present, a 302 redirect occurs to that URL with an ``error`` parameter; otherwise, a 400 Bad Request JSON response is returned with an error body.

**Common Error Scenarios (leading to failure responses):**

*   Missing required ``token`` query parameter.
*   The provided ``token`` is malformed, has an invalid signature, or is expired.
*   Internal server error during the authentication or email verification process.
*   The ``callback_url`` extracted from the token is not in the server's list of allowed redirect URIs (this should ideally be caught earlier, but could potentially manifest here).
