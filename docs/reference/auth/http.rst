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
*   ``reset_url`` (string, required): The base URL for the password reset link that will be emailed to the user. The ``reset_token`` will be appended as a query parameter. This URL must be an allowed redirect URI in the server configuration.
*   ``challenge`` (string, required): A PKCE code challenge. This challenge is embedded in the reset token and will be used when the user resets their password to issue a new authorization code.
*   ``redirect_to`` (string, optional): A URL to redirect to after the reset email has been successfully queued for sending.
*   ``redirect_on_failure`` (string, optional): A URL to redirect to if there's an error during the process. If not provided, but ``redirect_to`` is, ``redirect_to`` will be used as the fallback for failure redirection.

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
*   ``reset_token`` (string, required): The token that was emailed to the user.
*   ``password`` (string, required): The new password for the user's account.
*   ``redirect_to`` (string, optional): A URL to redirect to after the password has been successfully reset. If provided, a PKCE ``code`` will be appended to this URL.
*   ``redirect_on_failure`` (string, optional): A URL to redirect to if the password reset process fails. If not provided, but ``redirect_to`` is, ``redirect_to`` will be used as the fallback.

**Response:**

1.  **Successful Password Reset:**

    *   The ``reset_token`` is validated, and the user's password is updated.
    *   A new PKCE authorization ``code`` is generated using the challenge embedded in the ``reset_token``.
    *   If ``redirect_to`` is provided in the request:

        *   A 302 redirect to the ``redirect_to`` URL occurs.
        *   The redirect URL will have the new PKCE ``code`` appended as a query parameter. This ``code`` can then be exchanged for a session token at the ``POST /token`` endpoint.
            Example: ``https://app.example.com/password-reset-success?code=new_pkce_code``

    *   If ``redirect_to`` is NOT provided:

        *   A 200 OK response is returned with a JSON body containing the new PKCE ``code``:

            .. code-block:: json

                {
                  "code": "new_pkce_code"
                }

            This ``code`` can then be exchanged for a session token at the ``POST /token`` endpoint.

2.  **Password Reset Failure (e.g., invalid/expired token, server error):**

    *   This can occur if the ``reset_token`` is invalid, expired, or if there's an issue updating the password on the server.
    *   If ``redirect_on_failure`` (or ``redirect_to`` as a fallback) is provided and is an allowed URL:

        *   A 302 redirect to this URL occurs.
        *   The redirect URL will include ``error`` (a description of the error) and the submitted ``reset_token`` as query parameters.

    *   Otherwise (no applicable redirect URL or it's not allowed):

        *   An HTTP error response (e.g., 400 Bad Request, 403 Forbidden for token issues) is returned with a JSON body describing the error.

**Common Error Scenarios:**

*   Missing required fields in the request: ``provider``, ``reset_token``, or ``password``.
*   The ``reset_token`` is malformed, has an invalid signature, or is expired.
*   Internal server error during the password update process.

Email verification
==================

These endpoints apply to the Email and password provider, as well as the WebAuthn provider. Verification emails are sent even if you do not *require* verification. The difference between requiring verification and not is that if you require verification, the user must verify their email before they can authenticate. If you do not require verification, the user can authenticate without verifying their email.

POST /verify
------------

Verify a user's email address using a verification token.

**Request Body (JSON):**

*   ``provider`` (string, required): The name of the provider associated with the email, e.g., ``builtin::local_emailpassword``.
*   ``verification_token`` (string, required): The JWT sent to the user (typically via an email link) to verify their email.

**Response:**

The primary action is to validate the ``verification_token`` and mark the associated email as verified. The exact response depends on the contents of the ``verification_token`` itself, which may include a PKCE challenge and/or a redirect URL specified during its creation (e.g., at registration).

1.  **Token Valid & Email Verified - With Challenge & Redirect URL in Token:**

    *   A PKCE authorization code is generated using the challenge from the token.
    *   A 302 redirect to the URL specified in the token (``maybe_redirect_to``) occurs.
    *   The redirect URL will have the generated ``code`` appended as a query parameter.
        Example: ``https://app.example.com/redirect-after-verify?code=generated_pkce_code``

2.  **Token Valid & Email Verified - With Challenge Only in Token:**

    *   A PKCE authorization code is generated using the challenge from the token.
    *   A 200 OK response is returned with a JSON body:

        .. code-block:: json

            {
              "code": "generated_pkce_code"
            }

3.  **Token Valid & Email Verified - With Redirect URL Only in Token:**

    *   A 302 redirect to the URL specified in the token (``maybe_redirect_to``) occurs (no ``code`` is added in this case).

4.  **Token Valid & Email Verified - No Challenge or Redirect URL in Token:**

    *   A 204 No Content response is returned. The email is verified, but no further redirect or code generation was requested by the token's context.

5.  **Token Invalid or Expired:**

    *   A 403 Forbidden response is returned with a JSON body. Example for an expired token:

        .. code-block:: json

            {
              "message": "The 'iat' claim in verification token is older than 24 hours"
            }

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
