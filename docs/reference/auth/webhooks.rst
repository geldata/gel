.. _ref_auth_webhooks:

========
Webhooks
========

The auth extension supports sending webhooks for a variety of auth events. You can use these webhooks to, for instance, send a fully customized email for email verification, or password reset instead of our built-in email verification and password reset emails. You could also use them to trigger analytics events, start an email drip campaign, create an audit log, or trigger other side effects in your application.

If you are using Webhooks to send emails, be sure to not also configure an SMTP provider otherwise we will send the email via SMTP and also send the webhook which will trigger your custom email sending behavior.

.. warning::

  We send webhooks with no durability or reliability guarantees, so you should always provide a mechanism for retrying delivery of any critical events, such as email verification and password reset. We detail how to resend these events in the relevant sections on the various authentication flows.

Configuration
=============

You can configure webhooks with the UI or via query. The URLs you register as webhooks must be unique across all webhooks configured for each branch. If you want to send multiple events to the same URL, you can do so by adding multiple ``ext::auth::WebhookEvent`` values to the ``events`` set, like in this example.

.. code-block:: edgeql

    configure current branch insert
      ext::auth::WebhookConfig {
        url := 'https://example.com/auth/webhook',
        events := {
          ext::auth::WebhookEvent.EmailVerificationRequested,
          ext::auth::WebhookEvent.PasswordResetRequested,
        },
        # Optional, only needed if you want to verify the webhook request
        signing_secret_key := '1234567890',
      };

When you receive a webhook, you'll look at the ``event_type`` field to determine which event corresponds to this webhook request and handle it accordingly.

Checking webhook signatures
===========================

You can provide a signing key, which you will need to generate and save in a place that your application will have access to. The extension will then add a ``x-ext-auth-signature-sha256`` header to the request, which you can use to verify the request by comparing the signature to the SHA256 hash of the request body.

Here is an example of how you might verify the signature in a Node.js application:

.. code-block:: typescript

  /**
   * Assert that if the request contains a signature header, that the signature
   * is valid for the request body. Will return false if there is no signature
   * header.
   *
   * @param {Request} request - The request to verify.
   * @param {string} signingKey - The key to use to verify the signature.
   * @returns {boolean} - True if the signature is present and valid, false if
   *                    the signature is not present at all.
   * @throws {AssertionError} - If the signature is present but invalid.
   */
  async function assertSignature(
    request: Request,
    signingKey: string,
  ): Promise<boolean> {
      const signatureHeader = request.headers.get('x-ext-auth-signature-sha256');
      if (!signatureHeader) {
        return false;
      }

      const requestBody = await request.text();
      const encoder = new TextEncoder();
      const data = encoder.encode(requestBody);
      const key = await crypto.subtle.importKey(
        'raw',
        encoder.encode(signingKey),
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
      );
      const signature = await crypto.subtle.sign('HMAC', key, data);
      const signatureHex = Buffer.from(signature).toString('hex');

      assert.strictEqual(
        signatureHeader,
        signatureHex,
        "Signature header is set, but the signature is invalid"
      );

      return true;
  };


Troubleshooting webhooks
========================

If you are having trouble receiving webhooks, you might need to look for any responses from the requests that are being scheduled by the :ref:`std::net::http <ref_std_net>` module. You can list all of the :eql:type:`net::http::ScheduledRequest` objects, and any returned responses with the following query:

.. code-block:: edgeql

    select net::http::ScheduledRequest {
        **,
        response: { ** }
    }

Events reference
================

Common fields for all events:

* ``event_type``: (string) This will be a literal string containing the name of the event. You can use this to determine which event occurred.
* ``event_id``: (string) A unique identifier to help disambiguate events of the same type.
* ``timestamp``: (string) The ISO 8601 timestamp of when the event was triggered.


Identity created
^^^^^^^^^^^^^^^^

When a new ``ext::auth::Identity`` object is created, like when a new user signs up, or an existing user adds a new factor, this event is triggered.

**Example payload:**

.. code-block:: text

  POST http://localhost:8000/auth/webhook
  Content-type: application/json
  x-ext-auth-signature-sha256: 1234567890

  {
    "event_type": "IdentityCreated",
    "event_id": "1234567890",
    "timestamp": "2021-01-01T00:00:00Z",
    "identity_id": "identity123"
  }

Identity authenticated
^^^^^^^^^^^^^^^^^^^^^^

When an ``ext::auth::Identity`` object is authenticated, like when a user logs in, this event is triggered.

**Example payload:**

.. code-block:: text

  POST http://localhost:8000/auth/webhook
  Content-type: application/json
  x-ext-auth-signature-sha256: 1234567890

  {
    "event_type": "IdentityAuthenticated",
    "event_id": "1234567890",
    "timestamp": "2021-01-01T00:00:00Z",
    "identity_id": "identity123"
  }

Email factor created
^^^^^^^^^^^^^^^^^^^^

When a new ``ext::auth::EmailFactor`` object is created, like when a user adds a new email factor, this event is triggered.

**Example payload:**

.. code-block:: text

  POST http://localhost:8000/auth/webhook
  Content-type: application/json
  x-ext-auth-signature-sha256: 1234567890

  {
    "event_type": "EmailFactorCreated",
    "event_id": "1234567890",
    "timestamp": "2021-01-01T00:00:00Z",
    "identity_id": "identity123",
    "email_factor_id": "emailfactor123"
  }

Email verified
^^^^^^^^^^^^^^

When a user verifies their email address, this event is triggered.

**Example payload:**

.. code-block:: text

  POST http://localhost:8000/auth/webhook
  Content-type: application/json
  x-ext-auth-signature-sha256: 1234567890

  {
    "event_type": "EmailVerified",
    "event_id": "1234567890",
    "timestamp": "2021-01-01T00:00:00Z",
    "identity_id": "identity123",
    "email_factor_id": "emailfactor123"
  }

Email verification requested
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When a user requests to verify their email address, like when they first sign up, or requests to resend the verification email, this event is triggered.

**Example payload:**

.. code-block:: text

  POST http://localhost:8000/auth/webhook
  Content-type: application/json
  x-ext-auth-signature-sha256: 1234567890

  {
    "event_type": "EmailVerificationRequested",
    "event_id": "1234567890",
    "timestamp": "2021-01-01T00:00:00Z",
    "identity_id": "identity123",
    "verification_token": "verificationtoken123"
  }

Password reset requested
^^^^^^^^^^^^^^^^^^^^^^^^

When a user requests to reset their password, this event is triggered.

**Example payload:**

.. code-block:: text

  POST http://localhost:8000/auth/webhook
  Content-type: application/json
  x-ext-auth-signature-sha256: 1234567890

  {
    "event_type": "PasswordResetRequested",
    "event_id": "1234567890",
    "timestamp": "2021-01-01T00:00:00Z",
    "identity_id": "identity123",
    "reset_token": "resettoken123"
  }

Magic link requested
^^^^^^^^^^^^^^^^^^^^

When a user requests to send a magic link email, like for signing in, or signing up for the first time, this event is triggered.

**Example payload:**

.. code-block:: text

  POST http://localhost:8000/auth/webhook
  Content-type: application/json
  x-ext-auth-signature-sha256: 1234567890

  {
    "event_type": "MagicLinkRequested",
    "event_id": "1234567890",
    "timestamp": "2021-01-01T00:00:00Z",
    "identity_id": "identity123",
    "email_factor_id": "emailfactor123",
    "magic_link_token": "magiclinktoken123",
    "magic_link_url": "http://localhost:8000/auth/magic-link?token=magiclinktoken123"
  }
