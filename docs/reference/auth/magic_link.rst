.. _ref_guide_auth_magic_link:

==========
Magic Link
==========

:edb-alt-title: Integrating Gel Auth's magic link provider

Magic Link is a passwordless authentication method that allows users to log in via their email. This guide will walk you through integrating Magic Link authentication with your application using Gel Auth.

Magic Link supports two verification methods:

- **Link-based verification**: Users receive an email with a clickable link that automatically authenticates them
- **Code-based verification**: Users receive an email with a one-time code that they manually enter in your application

Enable Magic Link provider
==========================

Before you can use Magic Link authentication, you need to enable the Magic Link provider in your Gel Auth configuration. This can be done through the Gel UI under the "Providers" section.

The Magic Link provider can be configured with a ``verification_method`` property that determines how users verify their identity:

- **Link** (default): Traditional magic link where users click a link in their email
- **Code**: One-time code that users manually enter in your application

Verification methods
====================

Link-based verification
-----------------------

In Link-based verification (the default method), users receive an email containing a unique, time-sensitive link. When they click this link, they are automatically authenticated and redirected to your application.

**Flow overview:**

1. Your application requests Gel Auth to send a magic link email
2. User receives the email and clicks the magic link
3. The link redirects the user to your application with an authentication code
4. Your application exchanges the code for an authentication token

**Advantages:**
- Simple user experience - just click the link
- Works well on the same device where the authentication was initiated
- Familiar pattern for most users

**Considerations:**
- Requires the user to access email on the same device or be able to navigate back to your application
- Link contains sensitive authentication data in the URL

Code-based verification
-----------------------

In Code-based verification, users receive an email containing a short one-time code (typically 6-8 digits). They manually enter this code in your application to complete authentication.

**Flow overview:**

1. Your application requests Gel Auth to send a one-time code email
2. User receives the email with the verification code
3. User enters the code in your application
4. Your application submits the code to Gel Auth along with PKCE challenge
5. On successful verification, user is authenticated and your application receives an authentication token

**Advantages:**
- Works seamlessly across devices (can receive email on phone, enter code on desktop)
- Code is short and easy to transcribe
- No sensitive data in URLs
- Better security for cross-device authentication flows

**Considerations:**
- Requires an additional step in your UI to collect the code
- Users need to manually transcribe the code

UI considerations
=================

You can query the database configuration to discover which providers are configured and their verification methods to dynamically build your UI:

.. code-block:: edgeql

  select cfg::Config.extensions[is ext::auth::AuthConfig].providers {
      name,
      [is ext::auth::OAuthProviderConfig].display_name,
      [is ext::auth::MagicLinkProviderConfig].verification_method,
  };

The ``verification_method`` property will be either ``Link`` or ``Code``, allowing you to customize your authentication flow accordingly.

For Code-based verification, you'll need to add a code input field to your UI after initiating the authentication flow.

Link-based verification implementation
======================================

This section demonstrates implementing Link-based verification (the traditional magic link flow).

Example implementation
----------------------

We will demonstrate the various steps below by building a NodeJS HTTP server in a single file that we will use to simulate a typical web application.

.. note::

    The details below show the inner workings of how data is exchanged with the
    Auth extension from a web app using HTTP. You can use this as a guide to
    integrate with your application written in any language that can send and
    receive HTTP requests.

Start the PKCE flow
-------------------

We secure authentication tokens and other sensitive data by using PKCE
(Proof Key of Code Exchange).

Your application server creates a 32-byte Base64 URL-encoded string (which will
be 43 bytes after encoding), called the ``verifier``. You need to store this
value for the duration of the flow. One way to accomplish this bit of state is
to use an HttpOnly cookie when the browser makes a request to the server for
this value, which you can then use to retrieve it from the cookie store at the
end of the flow. Take this ``verifier`` string, hash it with SHA256, and then
base64url encode the resulting string. This new string is called the
``challenge``.

.. lint-off

.. code-block:: javascript

   import http from "node:http";
   import { URL } from "node:url";
   import crypto from "node:crypto";

   /**
    * You can get this value by running `gel instance credentials`.
    * Value should be:
    * `${protocol}://${host}:${port}/branch/${branch}/ext/auth/
    */
   const GEL_AUTH_BASE_URL = process.env.GEL_AUTH_BASE_URL;
   const SERVER_PORT = 3000;

   /**
    * Generate a random Base64 url-encoded string, and derive a "challenge"
    * string from that string to use as proof that the request for a token
    * later is made from the same user agent that made the original request
    *
    * @returns {Object} The verifier and challenge strings
    */
   const generatePKCE = () => {
      const verifier = crypto.randomBytes(32).toString("base64url");

      const challenge = crypto
         .createHash("sha256")
         .update(verifier)
         .digest("base64url");

      return { verifier, challenge };
   };

.. lint-on

Routing
-------

Let's set up the routes we will use to handle the Link-based magic link authentication
flow. We will then detail each route handler in the following sections.

.. lint-off

.. code-block:: javascript

   const server = http.createServer(async (req, res) => {
     const requestUrl = getRequestUrl(req);

     switch (requestUrl.pathname) {
       case "/auth/magic-link/callback": {
         await handleCallback(req, res);
         break;
       }

       case "/auth/magic-link/signup": {
         await handleSignUp(req, res);
         break;
       }

       case "/auth/magic-link/send": {
         await handleSendMagicLink(req, res);
         break;
       }

       default: {
         res.writeHead(404);
         res.end("Not found");
         break;
       }
     }
   });

.. lint-on

Sign up
-------

.. lint-off

.. code-block:: javascript

   /**
    * Send magic link to new user's email for sign up.
    *
    * @param {Request} req
    * @param {Response} res
    */
   const handleSignUp = async (req, res) => {
     let body = "";
     req.on("data", (chunk) => {
       body += chunk.toString();
     });
     req.on("end", async () => {
       const pkce = generatePKCE();
       const { email, provider } = JSON.parse(body);
       if (!email || !provider) {
         res.status = 400;
         res.end(
           `Request body malformed. Expected JSON body with 'email' and 'provider' keys, but got: ${body}`,
         );
         return;
       }

       const registerUrl = new URL("magic-link/register", GEL_AUTH_BASE_URL);
       const callbackUrl = new URL("auth/magic-link/callback", "http://localhost:${SERVER_PORT}");
       const registerResponse = await fetch(registerUrl.href, {
         method: "post",
         headers: {
           "Content-Type": "application/json",
         },
         body: JSON.stringify({
           challenge: pkce.challenge,
           email,
           provider,
           callback_url: callbackUrl.href,
           // The following endpoint will be called if there is an error
           // processing the magic link, such as expiration or malformed token,
           // etc.
           redirect_on_failure: `http://localhost:${SERVER_PORT}/auth_error.html`,
         }),
       });

       if (!registerResponse.ok) {
         const text = await registerResponse.text();
         res.status = 400;
         res.end(`Error from the auth server: ${text}`);
         return;
       }

       res.writeHead(204, {
         "Set-Cookie": `gel-pkce-verifier=${pkce.verifier}; HttpOnly; Path=/; Secure; SameSite=Strict`,
       });
       res.end();
     });
   };

.. lint-on

Sign in
-------

Signing in with a magic link simply involves telling the Gel Auth server to
send a magic link to the user's email. The user will then click on the link to
authenticate.

.. lint-off

.. code-block:: javascript

   /**
    * Send magic link to existing user's email for sign in.
    *
    * @param {Request} req
    * @param {Response} res
    */
   const handleSendMagicLink = async (req, res) => {
     let body = "";
     req.on("data", (chunk) => {
       body += chunk.toString();
     });
     req.on("end", async () => {
       const pkce = generatePKCE();
       const { email, provider } = JSON.parse(body);
       if (!email || !provider) {
         res.status = 400;
         res.end(
           `Request body malformed. Expected JSON body with 'email' and 'provider' keys, but got: ${body}`,
         );
         return;
       }

       const emailUrl = new URL("magic-link/email", GEL_AUTH_BASE_URL);
       const callbackUrl = new URL("auth/magic-link/callback", "http://localhost:${SERVER_PORT}");
       const authenticateResponse = await fetch(emailUrl.href, {
         method: "post",
         headers: {
           "Content-Type": "application/json",
         },
         body: JSON.stringify({
           challenge: pkce.challenge,
           email,
           provider,
           callback_url: callbackUrl.href,
         }),
       });

       if (!authenticateResponse.ok) {
         const text = await authenticateResponse.text();
         res.status = 400;
         res.end(`Error from the auth server: ${text}`);
         return;
       }

       res.writeHead(204, {
         "Set-Cookie": `gel-pkce-verifier=${pkce.verifier}; HttpOnly; Path=/; Secure; SameSite=Strict`,
       });
       res.end();
     });
   };

.. lint-on

Callback
--------

Once the user clicks on the magic link, they will be redirected back to your
application with a ``code`` query parameter. Your application will then exchange
this code for an authentication token.

.. lint-off

.. code-block:: javascript

   /**
    * Handles the PKCE callback and exchanges the `code` and `verifier`
    * for an auth_token, setting the auth_token as an HttpOnly cookie.
    *
    * @param {Request} req
    * @param {Response} res
    */
   const handleCallback = async (req, res) => {
      const requestUrl = getRequestUrl(req);

      const code = requestUrl.searchParams.get("code");
      if (!code) {
         const error = requestUrl.searchParams.get("error");
         res.status = 400;
         res.end(
            `Magic link callback is missing 'code'. Provider responded with error: ${error}`,
         );
         return;
      }

      const cookies = req.headers.cookie?.split("; ");
      const verifier = cookies
         ?.find((cookie) => cookie.startsWith("gel-pkce-verifier="))
         ?.split("=")[1];
      if (!verifier) {
         res.status = 400;
         res.end(
            `Could not find 'verifier' in the cookie store. Is this the same user agent/browser that started the authorization flow?`,
         );
         return;
      }

      const codeExchangeUrl = new URL("token", GEL_AUTH_BASE_URL);
      codeExchangeUrl.searchParams.set("code", code);
      codeExchangeUrl.searchParams.set("verifier", verifier);
      const codeExchangeResponse = await fetch(codeExchangeUrl.href, {
         method: "GET",
      });

      if (!codeExchangeResponse.ok) {
         const text = await codeExchangeResponse.text();
         res.status = 400;
         res.end(`Error from the auth server: ${text}`);
         return;
      }

      const { auth_token } = await codeExchangeResponse.json();
      res.writeHead(204, {
         "Set-Cookie": `gel-auth-token=${auth_token}; HttpOnly; Path=/; Secure; SameSite=Strict`,
      });
      res.end();
   };

.. lint-on

Code-based verification implementation
======================================

This section demonstrates implementing Code-based verification where users enter a one-time code.

Example implementation
----------------------

Code-based verification modifies the authentication flow to collect a verification code from the user instead of relying on link clicks.

.. note::

    Code-based verification enables cross-device authentication flows where users can receive the email on one device (like their phone) and complete authentication on another device (like their desktop).

Start the PKCE flow
-------------------

The PKCE setup is identical to Link-based verification:

.. lint-off

.. code-block:: javascript

   import http from "node:http";
   import { URL } from "node:url";
   import crypto from "node:crypto";

   /**
    * You can get this value by running `gel instance credentials`.
    * Value should be:
    * `${protocol}://${host}:${port}/branch/${branch}/ext/auth/
    */
   const GEL_AUTH_BASE_URL = process.env.GEL_AUTH_BASE_URL;
   const SERVER_PORT = 3000;

   /**
    * Generate a random Base64 url-encoded string, and derive a "challenge"
    * string from that string to use as proof that the request for a token
    * later is made from the same user agent that made the original request
    *
    * @returns {Object} The verifier and challenge strings
    */
   const generatePKCE = () => {
      const verifier = crypto.randomBytes(32).toString("base64url");

      const challenge = crypto
         .createHash("sha256")
         .update(verifier)
         .digest("base64url");

      return { verifier, challenge };
   };

.. lint-on

Routing
-------

For Code-based verification, we need routes to handle code submission:

.. lint-off

.. code-block:: javascript

   const server = http.createServer(async (req, res) => {
     const requestUrl = getRequestUrl(req);

     switch (requestUrl.pathname) {
       case "/auth/magic-link/signup": {
         await handleSignUp(req, res);
         break;
       }

       case "/auth/magic-link/send": {
         await handleSendMagicLink(req, res);
         break;
       }

       case "/auth/magic-link/verify-code": {
         await handleVerifyCode(req, res);
         break;
       }

       default: {
         res.writeHead(404);
         res.end("Not found");
         break;
       }
     }
   });

.. lint-on

Sign up
-------

Sending the initial registration email is the same, but no callback URL is needed since users will enter the code directly:

.. lint-off

.. code-block:: javascript

   /**
    * Send verification code to new user's email for sign up.
    *
    * @param {Request} req
    * @param {Response} res
    */
   const handleSignUp = async (req, res) => {
     let body = "";
     req.on("data", (chunk) => {
       body += chunk.toString();
     });
     req.on("end", async () => {
       const { email, provider } = JSON.parse(body);
       if (!email || !provider) {
         res.status = 400;
         res.end(
           `Request body malformed. Expected JSON body with 'email' and 'provider' keys, but got: ${body}`,
         );
         return;
       }

       const registerUrl = new URL("magic-link/register", GEL_AUTH_BASE_URL);
       const registerResponse = await fetch(registerUrl.href, {
         method: "post",
         headers: {
           "Content-Type": "application/json",
         },
         body: JSON.stringify({
           email,
           provider,
           // No callback_url needed for code-based verification
         }),
       });

       if (!registerResponse.ok) {
         const text = await registerResponse.text();
         res.status = 400;
         res.end(`Error from the auth server: ${text}`);
         return;
       }

       res.writeHead(200, {
         "Content-Type": "application/json",
       });
       res.end(JSON.stringify({
         message: "Verification code sent to email",
         next_step: "verify_code"
       }));
     });
   };

.. lint-on

Sign in
-------

Similarly, sending a sign-in code doesn't require a callback URL:

.. lint-off

.. code-block:: javascript

   /**
    * Send verification code to existing user's email for sign in.
    *
    * @param {Request} req
    * @param {Response} res
    */
   const handleSendMagicLink = async (req, res) => {
     let body = "";
     req.on("data", (chunk) => {
       body += chunk.toString();
     });
     req.on("end", async () => {
       const { email, provider } = JSON.parse(body);
       if (!email || !provider) {
         res.status = 400;
         res.end(
           `Request body malformed. Expected JSON body with 'email' and 'provider' keys, but got: ${body}`,
         );
         return;
       }

       const emailUrl = new URL("magic-link/email", GEL_AUTH_BASE_URL);
       const authenticateResponse = await fetch(emailUrl.href, {
         method: "post",
         headers: {
           "Content-Type": "application/json",
         },
         body: JSON.stringify({
           email,
           provider,
           // No callback_url or challenge needed for initial code send
         }),
       });

       if (!authenticateResponse.ok) {
         const text = await authenticateResponse.text();
         res.status = 400;
         res.end(`Error from the auth server: ${text}`);
         return;
       }

       res.writeHead(200, {
         "Content-Type": "application/json",
       });
       res.end(JSON.stringify({
         message: "Verification code sent to email",
         next_step: "verify_code"
       }));
     });
   };

.. lint-on

Code verification
-----------------

The key difference in Code-based verification is this new endpoint that handles code submission:

.. lint-off

.. code-block:: javascript

   /**
    * Verify the one-time code and complete authentication.
    *
    * @param {Request} req
    * @param {Response} res
    */
   const handleVerifyCode = async (req, res) => {
     let body = "";
     req.on("data", (chunk) => {
       body += chunk.toString();
     });
     req.on("end", async () => {
       const pkce = generatePKCE();
       const { email, code, provider } = JSON.parse(body);

       if (!email || !code || !provider) {
         res.status = 400;
         res.end(
           `Request body malformed. Expected JSON body with 'email', 'code', and 'provider' keys, but got: ${body}`,
         );
         return;
       }

       const authenticateUrl = new URL("magic-link/authenticate", GEL_AUTH_BASE_URL);
       const authenticateResponse = await fetch(authenticateUrl.href, {
         method: "post",
         headers: {
           "Content-Type": "application/json",
         },
         body: JSON.stringify({
           email,
           code,
           challenge: pkce.challenge,
           // Optional: provide callback_url for redirect, or omit for JSON response
         }),
       });

       if (!authenticateResponse.ok) {
         const text = await authenticateResponse.text();
         res.status = 400;
         res.end(`Error from the auth server: ${text}`);
         return;
       }

       const { code: authCode } = await authenticateResponse.json();

       // Exchange the auth code for a token
       const codeExchangeUrl = new URL("token", GEL_AUTH_BASE_URL);
       codeExchangeUrl.searchParams.set("code", authCode);
       codeExchangeUrl.searchParams.set("verifier", pkce.verifier);
       const codeExchangeResponse = await fetch(codeExchangeUrl.href, {
         method: "GET",
       });

       if (!codeExchangeResponse.ok) {
         const text = await codeExchangeResponse.text();
         res.status = 400;
         res.end(`Error from the auth server: ${text}`);
         return;
       }

       const { auth_token } = await codeExchangeResponse.json();
       res.writeHead(204, {
         "Set-Cookie": `gel-auth-token=${auth_token}; HttpOnly; Path=/; Secure; SameSite=Strict`,
       });
       res.end();
     });
   };

.. lint-on

Create a User object
====================

For some applications, you may want to create a custom ``User`` type in the
default module to attach application-specific information. You can tie this to
an ``ext::auth::Identity`` by using the ``identity_id`` returned during the
sign-up flow.

.. note::

    For this example, we'll assume you have a one-to-one relationship between
    ``User`` objects and ``ext::auth::Identity`` objects. In your own
    application, you may instead decide to have a one-to-many relationship.

Given this ``User`` type:

.. code-block:: sdl

   type User {
       email: str;
       name: str;

       required identity: ext::auth::Identity {
           constraint exclusive;
       };
   }

For **Link-based verification**, update the callback handler to create a User object when ``isSignUp`` is true (see the original implementation above).

For **Code-based verification**, you can check for new user creation during the code verification step by modifying the ``handleVerifyCode`` function:

.. tabs::

  .. code-tab:: javascript-diff
    :caption: handleVerifyCode (Code-based)

      const handleVerifyCode = async (req, res) => {
        let body = "";
        req.on("data", (chunk) => {
          body += chunk.toString();
        });
        req.on("end", async () => {
          const pkce = generatePKCE();
    -     const { email, code, provider } = JSON.parse(body);
    +     const { email, code, provider, isSignUp } = JSON.parse(body);

          if (!email || !code || !provider) {
            res.status = 400;
            res.end(
              `Request body malformed. Expected JSON body with 'email', 'code', and 'provider' keys, but got: ${body}`,
            );
            return;
          }

          const authenticateUrl = new URL("magic-link/authenticate", GEL_AUTH_BASE_URL);
          const authenticateResponse = await fetch(authenticateUrl.href, {
            method: "post",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email,
              code,
              challenge: pkce.challenge,
            }),
          });

          if (!authenticateResponse.ok) {
            const text = await authenticateResponse.text();
            res.status = 400;
            res.end(`Error from the auth server: ${text}`);
            return;
          }

          const { code: authCode } = await authenticateResponse.json();

          // Exchange the auth code for a token
          const codeExchangeUrl = new URL("token", GEL_AUTH_BASE_URL);
          codeExchangeUrl.searchParams.set("code", authCode);
          codeExchangeUrl.searchParams.set("verifier", pkce.verifier);
          const codeExchangeResponse = await fetch(codeExchangeUrl.href, {
            method: "GET",
          });

          if (!codeExchangeResponse.ok) {
            const text = await codeExchangeResponse.text();
            res.status = 400;
            res.end(`Error from the auth server: ${text}`);
            return;
          }

    -     const { auth_token } = await codeExchangeResponse.json();
    +     const {
    +       auth_token,
    +       identity_id
    +     } = await codeExchangeResponse.json();

    +     if (isSignUp) {
    +       await client.query(`
    +         with
    +           identity := <ext::auth::Identity><uuid>$identity_id,
    +           emailFactor := (
    +             select ext::auth::EmailFactor filter .identity = identity
    +           ),
    +         insert User {
    +           email := emailFactor.email,
    +           identity := identity
    +         };
    +       `, { identity_id });
    +     }
    +
          res.writeHead(204, {
            "Set-Cookie": `gel-auth-token=${auth_token}; HttpOnly; Path=/; Secure; SameSite=Strict`,
          });
          res.end();
        });
      };

:ref:`Back to the Gel Auth guide <ref_guide_auth>`
