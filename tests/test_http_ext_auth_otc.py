#
# This source file is part of the Gel open source project.
#
# Copyright 2025-present MagicStack Inc. and the Gel authors.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import contextvars
import urllib.parse
import uuid
import json
import base64
import datetime
import argon2
import os
import pickle
import re
import hashlib

from typing import Optional, cast
from email.message import EmailMessage

from edgedb import ConstraintViolationError
from edb.testbase import http as tb
from edb.server.protocol.auth_ext import jwt as auth_jwt, otc, errors

ph = argon2.PasswordHasher()

HTTP_TEST_PORT: contextvars.ContextVar[str] = contextvars.ContextVar(
    'HTTP_TEST_PORT'
)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


SIGNING_KEY = 'a' * 32
APP_NAME = "Test App" * 13
LOGO_URL = "http://example.com/logo.png"
DARK_LOGO_URL = "http://example.com/darklogo.png"
BRAND_COLOR = "f0f8ff"
SENDER = f"sender@example.com"


class TestHttpExtAuthOtc(tb.ExtAuthTestCase):
    TRANSACTION_ISOLATION = False
    PARALLELISM_GRANULARITY = 'suite'

    SETUP = [
        f"""
        CONFIGURE CURRENT DATABASE INSERT cfg::SMTPProviderConfig {{
            name := "email_hosting_is_easy",
            sender := "{SENDER}",
        }};

        CONFIGURE CURRENT DATABASE SET
        current_email_provider_name := "email_hosting_is_easy";

        CONFIGURE CURRENT DATABASE SET
        ext::auth::AuthConfig::auth_signing_key := '{SIGNING_KEY}';

        CONFIGURE CURRENT DATABASE SET
        ext::auth::AuthConfig::token_time_to_live := <duration>'24 hours';

        CONFIGURE CURRENT DATABASE SET
        ext::auth::AuthConfig::app_name := '{APP_NAME}';

        CONFIGURE CURRENT DATABASE SET
        ext::auth::AuthConfig::logo_url := '{LOGO_URL}';

        CONFIGURE CURRENT DATABASE SET
        ext::auth::AuthConfig::dark_logo_url := '{DARK_LOGO_URL}';

        CONFIGURE CURRENT DATABASE SET
        ext::auth::AuthConfig::brand_color := '{BRAND_COLOR}';

        CONFIGURE CURRENT DATABASE
        INSERT ext::auth::UIConfig {{
          redirect_to := 'https://example.com/app',
          redirect_to_on_signup := 'https://example.com/signup/app',
        }};

        CONFIGURE CURRENT DATABASE SET
        ext::auth::AuthConfig::allowed_redirect_urls := {{
            'https://example.com/app'
        }};

        CONFIGURE CURRENT DATABASE
        INSERT ext::auth::EmailPasswordProviderConfig {{
            require_verification := false,
        }};

        CONFIGURE CURRENT DATABASE
        INSERT ext::auth::WebAuthnProviderConfig {{
            relying_party_origin := 'https://example.com:8080',
            require_verification := false,
        }};

        CONFIGURE CURRENT DATABASE
        INSERT ext::auth::MagicLinkProviderConfig {{}};

        # Pure testing code:
        CREATE TYPE TestUser;
        ALTER TYPE TestUser {{
            CREATE REQUIRED LINK identity: ext::auth::Identity {{
                SET default := (GLOBAL ext::auth::ClientTokenIdentity)
            }};
        }};

        """,
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loop.run_until_complete(
            cls._wait_for_db_config('ext::auth::AuthConfig::providers')
        )

    mock_net_server: tb.MockHttpServer

    def setUp(self):
        self.mock_net_server = tb.MockHttpServer()
        self.mock_net_server.start()
        super().setUp()

    def tearDown(self):
        if self.mock_net_server is not None:
            self.mock_net_server.stop()
        super().tearDown()

    def signing_key(self):
        return auth_jwt.SigningKey(
            lambda: SIGNING_KEY,
            self.http_addr,
            is_key_for_testing=True,
        )

    @classmethod
    def get_setup_script(cls):
        res = super().get_setup_script()

        import os.path

        # HACK: As a debugging cycle hack, when RELOAD is true, we reload the
        # extension package from the file, so we can test without a bootstrap.
        RELOAD = False

        if RELOAD:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            with open(os.path.join(root, 'edb/lib/ext/auth.edgeql')) as f:
                contents = f.read()
            to_add = (
                '''
                drop extension package auth version '1.0';
                create extension auth;
            '''
                + contents
            )
            splice = '__internal_testmode := true;'
            res = res.replace(splice, splice + to_add)

        return res

    async def get_provider_config_by_name(self, fqn: str):
        return await self.con.query_required_single(
            """
            SELECT assert_exists(
                cfg::Config.extensions[is ext::auth::AuthConfig].providers {
                    *,
                    verification_method := (
                      [is ext::auth::EmailPasswordProviderConfig].verification_method
                      ?? [is ext::auth::MagicLinkProviderConfig].verification_method
                      ?? [is ext::auth::WebAuthnProviderConfig].verification_method
                    ),
                    [is ext::auth::OAuthProviderConfig].client_id,
                    [is ext::auth::OAuthProviderConfig].additional_scope,
                } filter .name = <str>$0
            )
            """,
            fqn,
        )

    async def get_builtin_provider_config_by_name(self, provider_name: str):
        return await self.get_provider_config_by_name(
            f"builtin::{provider_name}"
        )

    async def get_auth_config_value(self, key: str):
        return await self.con.query_single(
            f"""
            SELECT assert_single(
                cfg::Config.extensions[is ext::auth::AuthConfig]
                    .{key}
            )
            """
        )

    def maybe_get_cookie_value(
        self, headers: dict[str, str], name: str
    ) -> Optional[str]:
        set_cookie = headers.get("set-cookie")
        if set_cookie is not None:
            (k, v) = set_cookie.split(";", 1)[0].split("=", 1)
            if k == name:
                return v

        return None

    def maybe_get_auth_token(self, headers: dict[str, str]) -> Optional[str]:
        return self.maybe_get_cookie_value(headers, "edgedb-session")

    async def test_http_ext_auth_otc_00(self):
        """Test that the schema migration additions work correctly.

        This test verifies that the new OneTimeCode and AuthenticationAttempt types
        can be created and function properly. It tests the verification_method property
        on provider configs, ensures OneTimeCode constraints work (code_hash exclusivity),
        and validates that AuthenticationAttempts track events correctly in an event-based
        design that allows multiple attempts per factor.
        """

        # Test that EmailPasswordProviderConfig has verification_method property with Link default
        email_config = await self.get_builtin_provider_config_by_name(
            "local_emailpassword"
        )
        self.assertEqual(str(email_config.verification_method), 'Link')

        # Test that MagicLinkProviderConfig has verification_method property with Link default
        magic_link_config = await self.get_builtin_provider_config_by_name(
            "local_magic_link"
        )
        self.assertEqual(str(magic_link_config.verification_method), 'Link')

        # Test that OneTimeCode and AuthenticationAttempt types exist and can be created
        # First create a test factor to link to
        result = await self.con.query_single("""
            INSERT ext::auth::LocalIdentity {
                issuer := "test",
                subject := "test_user_123",
            };
        """)

        identity_id = result.id

        email_factor = await self.con.query_single(
            """
            INSERT ext::auth::EmailFactor {
                identity := <ext::auth::LocalIdentity><uuid>$identity_id,
                email := "test@example.com",
            };
        """,
            identity_id=identity_id,
        )

        # Now create a OneTimeCode
        expires_at = utcnow() + datetime.timedelta(minutes=10)
        otc = await self.con.query_single(
            """
            with
                plaintext_code := b"test_hash_123",
                code_hash := ext::pgcrypto::digest(plaintext_code, 'sha256'),
                ONE_TIME_CODE := (
                    INSERT ext::auth::OneTimeCode {
                        code_hash := code_hash,
                        expires_at := <datetime>$expires_at,
                        factor := <ext::auth::Factor><uuid>$factor_id,
                    }
                ),
            select ONE_TIME_CODE { ** };
        """,
            expires_at=expires_at,
            factor_id=email_factor.id,
        )

        expected_hash = hashlib.sha256(b"test_hash_123").digest()
        self.assertEqual(otc.code_hash, expected_hash)

        # Test that AuthenticationAttempt can be created and tracks attempt events properly
        auth_attempt = await self.con.query_single(
            """
            with
                ATTEMPT := (
                    INSERT ext::auth::AuthenticationAttempt {
                        factor := <ext::auth::Factor><uuid>$factor_id,
                        attempt_type := ext::auth::AuthenticationAttemptType.OneTimeCode,
                        successful := false,
                    }
                ),
            select ATTEMPT { * };
        """,
            factor_id=email_factor.id,
        )

        self.assertEqual(str(auth_attempt.attempt_type), "OneTimeCode")
        self.assertFalse(auth_attempt.successful)
        self.assertIsNotNone(auth_attempt.created_at)
        self.assertIsNotNone(auth_attempt.modified_at)

        # Test that the OneTimeCode constraint works (code_hash should be exclusive)
        with self.assertRaises(ConstraintViolationError):
            await self.con.query(
                """
                with
                    plaintext_code := b"test_hash_123",
                    code_hash := ext::pgcrypto::digest(plaintext_code, 'sha256'),
                    ONE_TIME_CODE := (
                        INSERT ext::auth::OneTimeCode {
                            code_hash := code_hash,
                            expires_at := <datetime>$expires_at,
                            factor := <ext::auth::Factor><uuid>$factor_id,
                        }
                    ),
                select ONE_TIME_CODE { ** };
                """,
                expires_at=expires_at,
                factor_id=email_factor.id,
            )

        # Test that multiple AuthenticationAttempts can be created (event-based design)
        auth_attempt2 = await self.con.query_single(
            """
            with
                ATTEMPT := (
                    INSERT ext::auth::AuthenticationAttempt {
                        factor := <ext::auth::Factor><uuid>$factor_id,
                        attempt_type := ext::auth::AuthenticationAttemptType.OneTimeCode,
                        successful := true,
                    }
                ),
            select ATTEMPT { * };
        """,
            factor_id=email_factor.id,
        )

        # Both attempts should exist (event-based allows multiple)
        all_attempts = await self.con.query(
            """
            SELECT ext::auth::AuthenticationAttempt { * }
            FILTER .factor.id = <uuid>$factor_id
            ORDER BY .created_at;
        """,
            factor_id=email_factor.id,
        )

        self.assertEqual(len(all_attempts), 2)
        self.assertFalse(all_attempts[0].successful)  # First attempt was failed
        self.assertTrue(
            all_attempts[1].successful
        )  # Second attempt was successful

    async def test_http_ext_auth_otc_06(self):
        """Test verification with expired code.

        Validates that expired OTCs are properly rejected and cleaned up during
        verification attempts. This tests the TTL enforcement and ensures expired
        codes cannot be used for authentication, maintaining security.
        """
        # Create test factor
        identity = await self.con.query_single("""
            INSERT ext::auth::LocalIdentity {
                issuer := "test",
                subject := "test_user_otc_expired",
            };
        """)

        email_factor = await self.con.query_single(
            """
            INSERT ext::auth::EmailFactor {
                identity := <ext::auth::LocalIdentity><uuid>$identity_id,
                email := "test_otc_expired@example.com",
            };
        """,
            identity_id=identity.id,
        )

        # Create an OTC that's already expired
        expired_time = utcnow() - datetime.timedelta(minutes=5)
        code_hash = otc.hash_code("123456")

        expired_otc = await self.con.query_single(
            """
            INSERT ext::auth::OneTimeCode {
                factor := <ext::auth::Factor><uuid>$factor_id,
                code_hash := <bytes>$code_hash,
                expires_at := <datetime>$expires_at,
            };
        """,
            factor_id=email_factor.id,
            code_hash=code_hash,
            expires_at=expired_time,
        )

        # Try to verify the expired code via HTTP (should return 400 with error)
        with self.http_con() as http_con:
            auth_body, auth_headers, auth_status = self.http_con_request(
                http_con,
                params={
                    "email": "test_otc_expired@example.com",
                    "code": "123456",
                    "challenge": "test_challenge_expired",
                    "callback_url": "https://example.com/app/auth/callback",
                },
                method="GET",
                path="magic-link/authenticate",
            )
        self.assertEqual(
            auth_status, 400, f"Expected 400, got {auth_status}: {auth_body}"
        )
        error_data = json.loads(auth_body)
        self.assertEqual(error_data.get("error"), "Code has expired")

        # Code should be deleted by the mega query
        deleted_otc = await self.con.query_single(
            "SELECT ext::auth::OneTimeCode { ** } FILTER .id = <uuid>$otc_id",
            otc_id=expired_otc.id,
        )
        self.assertIsNone(deleted_otc)

    async def test_http_ext_auth_otc_magic_link_00(self):
        """Test complete Magic Link OTC flow: register -> email with code -> authenticate.

        Tests the full Magic Link authentication flow when configured for OTC mode.
        Validates that registration sends an email with a 6-digit code instead of
        a magic link, the code can be extracted and used for authentication, and
        the complete PKCE flow works with the OTC verification method.
        """

        # Configure Magic Link provider to use Code verification
        await self.con.query("""
            CONFIGURE CURRENT DATABASE
            RESET ext::auth::MagicLinkProviderConfig;

            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::MagicLinkProviderConfig {
                verification_method := ext::auth::VerificationMethod.Code,
            };
        """)

        # Set up webhook configuration to test OTC webhook events
        base_url = self.mock_net_server.get_base_url().rstrip("/")
        webhook_url = f"{base_url}/otc-webhook"
        await self.con.query(
            """
            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::WebhookConfig {
                url := <str>$url,
                events := {
                    ext::auth::WebhookEvent.OneTimeCodeRequested,
                    ext::auth::WebhookEvent.OneTimeCodeVerified,
                    ext::auth::WebhookEvent.IdentityCreated,
                    ext::auth::WebhookEvent.EmailFactorCreated,
                },
            };
            """,
            url=webhook_url,
        )

        webhook_request = (
            "POST",
            base_url,
            "/otc-webhook",
        )
        self.mock_net_server.register_route_handler(*webhook_request)(
            ("", 204)
        )

        await self._wait_for_db_config("ext::auth::AuthConfig::webhooks")

        try:
            email = f"{uuid.uuid4()}@example.com"
            verifier, challenge = self.generate_pkce_pair()
            callback_url = "https://example.com/app/auth/callback"
            error_url = "https://example.com/app/auth/error"

            with self.http_con() as http_con:
                # Step 1: Register (should send OTC email, not magic link)
                body, headers, status = self.http_con_request(
                    http_con,
                    method="POST",
                    path="magic-link/register",
                    body=json.dumps(
                        {
                            "provider": "builtin::local_magic_link",
                            "email": email,
                            "challenge": challenge,
                            "callback_url": callback_url,
                            "redirect_on_failure": error_url,
                        }
                    ).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                self.assertEqual(
                    status, 200, f"POST /magic-link/register: {status} {body}"
                )

                # Should redirect to code-sent page, not magic-link-sent
                response_data = json.loads(body)
                self.assertIn(
                    "code-sent", response_data.get("redirect_url", "")
                )

                # Step 2: Get the OTC from email
                file_name_hash = hashlib.sha256(
                    f"{SENDER}{email}".encode()
                ).hexdigest()
                test_file = os.environ.get(
                    "EDGEDB_TEST_EMAIL_FILE",
                    f"/tmp/edb-test-email-{file_name_hash}.pickle",
                )
                with open(test_file, "rb") as f:
                    email_args = pickle.load(f)

                msg = cast(EmailMessage, email_args["message"])
                html_body = msg.get_body(('html',))
                html_content = html_body.get_payload(decode=True).decode(
                    'utf-8'
                )

                # Extract the 6-digit code from email
                code_match = re.search(r'(?:^|\s)(\d{6})(?:\s|$)', html_content)
                self.assertIsNotNone(
                    code_match, "No 6-digit code found in email"
                )
                otc_code = code_match.group(1)
                self.assertEqual(len(otc_code), 6)

                # Step 3: Authenticate with the code (includes PKCE challenge)
                auth_body, auth_headers, auth_status = self.http_con_request(
                    http_con,
                    params={
                        "email": email,
                        "code": otc_code,
                        "challenge": challenge,
                        "callback_url": callback_url,
                    },
                    method="GET",
                    path="magic-link/authenticate",
                )

                self.assertEqual(
                    auth_status, 302, auth_body
                )  # Should redirect with auth code

                # Should redirect to callback_url with auth code
                location = auth_headers.get("location", "")
                self.assertTrue(location.startswith(callback_url))

                # Parse auth code from redirect
                parsed_url = urllib.parse.urlparse(location)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                auth_code = query_params.get("code", [None])[0]
                self.assertIsNotNone(auth_code)

                # Step 4: Exchange auth code for token
                token_body, token_headers, token_status = self.http_con_request(
                    http_con,
                    params={
                        "code": auth_code,
                        "verifier": verifier,
                    },
                    method="GET",
                    path="token",
                    headers={"Content-Type": "application/json"},
                )

                self.assertEqual(
                    token_status,
                    200,
                    f"POST /token: {token_status} {token_body}",
                )
                token_data = json.loads(token_body)
                self.assertIn("auth_token", token_data)

                # Step 5: Test OTC webhook events were sent
                async for tr in self.try_until_succeeds(
                    delay=2, timeout=120, ignore=(KeyError, AssertionError)
                ):
                    async with tr:
                        requests_for_webhook = self.mock_net_server.requests[
                            webhook_request
                        ]
                        # Should have 4 webhook events: IdentityCreated, EmailFactorCreated,
                        # OneTimeCodeRequested, OneTimeCodeVerified
                        self.assertEqual(len(requests_for_webhook), 4)

                # Parse and validate webhook events
                event_types: dict[str, dict | None] = {
                    "IdentityCreated": None,
                    "EmailFactorCreated": None,
                    "OneTimeCodeRequested": None,
                    "OneTimeCodeVerified": None,
                }

                for request in requests_for_webhook:
                    assert request.body is not None
                    event_data = json.loads(request.body)
                    event_type = event_data["event_type"]
                    self.assertIn(event_type, event_types)
                    event_types[event_type] = event_data

                # Verify all expected events were received
                self.assertTrue(
                    all(value is not None for value in event_types.values())
                )

                                # Validate OneTimeCodeRequested event
                otc_requested = cast(dict, event_types["OneTimeCodeRequested"])
                self.assertIn("identity_id", otc_requested)
                self.assertIn("email_factor_id", otc_requested)
                self.assertIn("otc_id", otc_requested)
                self.assertIn("one_time_code", otc_requested)
                self.assertIn("event_id", otc_requested)
                self.assertIn("timestamp", otc_requested)
                # Verify the code is a 6-digit string
                self.assertEqual(len(otc_requested["one_time_code"]), 6)
                self.assertTrue(otc_requested["one_time_code"].isdigit())

                # Validate OneTimeCodeVerified event
                otc_verified = cast(dict, event_types["OneTimeCodeVerified"])
                self.assertIn("identity_id", otc_verified)
                self.assertIn("email_factor_id", otc_verified)
                self.assertIn("otc_id", otc_verified)
                self.assertIn("event_id", otc_verified)
                self.assertIn("timestamp", otc_verified)

                # Verify the OTC events have the same identity and factor IDs
                self.assertEqual(
                    otc_requested["identity_id"],
                    otc_verified["identity_id"]
                )
                self.assertEqual(
                    otc_requested["email_factor_id"],
                    otc_verified["email_factor_id"]
                )

        finally:
            # Clean up webhook config
            await self.con.query(
                "CONFIGURE CURRENT DATABASE RESET ext::auth::WebhookConfig"
            )
            # Restore original Magic Link provider config
            await self.con.query("""
                CONFIGURE CURRENT DATABASE
                RESET ext::auth::MagicLinkProviderConfig;
                CONFIGURE CURRENT DATABASE
                INSERT ext::auth::MagicLinkProviderConfig {};
            """)

    async def test_http_ext_auth_otc_magic_link_01(self):
        """Test Magic Link OTC cross-device: initiate on device A, verify on device B.

        Tests the cross-device authentication scenario where a user initiates
        authentication on one device but completes verification on another. This
        validates that OTC codes can be shared between devices and that PKCE
        challenges work correctly across different sessions.
        """

        # Configure for OTC
        await self.con.query("""
            CONFIGURE CURRENT DATABASE
            RESET ext::auth::MagicLinkProviderConfig;

            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::MagicLinkProviderConfig {
                verification_method := ext::auth::VerificationMethod.Code,
            };
        """)

        email = f"{uuid.uuid4()}@example.com"
        callback_url = "https://example.com/app/auth/callback"
        error_url = "https://example.com/app/auth/error"
        pkce_device_a = self.generate_pkce_pair()
        pkce_device_b = self.generate_pkce_pair()

        # Device A: Initiate flow
        with self.http_con() as http_con_device_a:
            body, headers, status = self.http_con_request(
                http_con_device_a,
                method="POST",
                path="magic-link/register",
                body=json.dumps(
                    {
                        "provider": "builtin::local_magic_link",
                        "email": email,
                        "callback_url": callback_url,
                        "redirect_on_failure": error_url,
                        "challenge": pkce_device_a[1],
                    }
                ).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            self.assertEqual(status, 200, body)

        # Get OTC from email
        file_name_hash = hashlib.sha256(f"{SENDER}{email}".encode()).hexdigest()
        test_file = os.environ.get(
            "EDGEDB_TEST_EMAIL_FILE",
            f"/tmp/edb-test-email-{file_name_hash}.pickle",
        )
        with open(test_file, "rb") as f:
            email_args = pickle.load(f)

        msg = cast(EmailMessage, email_args["message"])
        html_content = (
            msg.get_body(('html',)).get_payload(decode=True).decode('utf-8')
        )
        code_match = re.search(r'(?:^|\s)(\d{6})(?:\s|$)', html_content)
        otc_code = code_match.group(1)

        # Device B: Verify with new PKCE challenge
        with self.http_con() as http_con_device_b:
            auth_body, auth_headers, auth_status = self.http_con_request(
                http_con_device_b,
                params={
                    "email": email,
                    "code": otc_code,
                    "callback_url": callback_url,
                    "redirect_on_failure": error_url,
                    "challenge": pkce_device_b[1],
                },
                method="GET",
                path="magic-link/authenticate",
            )

            self.assertEqual(auth_status, 302, auth_body)

            # Should successfully redirect with auth code
            location = auth_headers.get("location", "")
            self.assertTrue(
                location.startswith(callback_url),
                f"Expected callback_url: {callback_url}, got: {location}",
            )

            # Verify can exchange for token using Device B's verifier
            parsed_url = urllib.parse.urlparse(location)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            auth_code = query_params.get("code", [None])[0]

            token_body, _, token_status = self.http_con_request(
                http_con_device_b,
                params={
                    "code": auth_code,
                    "verifier": pkce_device_b[0],
                },
                method="GET",
                path="token",
            )

            self.assertEqual(token_status, 200, token_body)
            token_data = json.loads(token_body)
            self.assertIn("auth_token", token_data)

    async def test_http_ext_auth_otc_email_password_00(self):
        """Test Email+Password OTC flow: register -> email with code -> verify.

        Tests the complete Email+Password registration and verification flow when
        configured for OTC mode. Validates that registration sends verification
        codes instead of links, codes can be extracted and used for verification,
        and successful verification allows subsequent authentication.
        """

        # Configure Email+Password provider to use Code verification
        await self.con.query("""
            CONFIGURE CURRENT DATABASE
            RESET ext::auth::EmailPasswordProviderConfig;

            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::EmailPasswordProviderConfig {
                require_verification := true,
                verification_method := ext::auth::VerificationMethod.Code,
            };
        """)

        # Set up webhook configuration to test OTC webhook events
        base_url = self.mock_net_server.get_base_url().rstrip("/")
        webhook_url = f"{base_url}/email-otc-webhook"
        await self.con.query(
            """
            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::WebhookConfig {
                url := <str>$url,
                events := {
                    ext::auth::WebhookEvent.OneTimeCodeRequested,
                    ext::auth::WebhookEvent.OneTimeCodeVerified,
                    ext::auth::WebhookEvent.IdentityCreated,
                    ext::auth::WebhookEvent.EmailFactorCreated,
                    ext::auth::WebhookEvent.EmailVerified,
                },
            };
            """,
            url=webhook_url,
        )

        webhook_request = (
            "POST",
            base_url,
            "/email-otc-webhook",
        )
        self.mock_net_server.register_route_handler(*webhook_request)(
            ("", 204)
        )

        await self._wait_for_db_config("ext::auth::AuthConfig::webhooks")

        email = f"{uuid.uuid4()}@example.com"
        password = "test_password_otc_123"
        verifier, challenge = self.generate_pkce_pair()

        try:
            with self.http_con() as http_con:
                # Step 1: Register (should send OTC email, not verification link)
                form_data = {
                    "provider": "builtin::local_emailpassword",
                    "email": email,
                    "password": password,
                    "challenge": challenge,
                }
                form_data_encoded = urllib.parse.urlencode(form_data).encode()

                body, headers, status = self.http_con_request(
                    http_con,
                    method="POST",
                    path="register",
                    body=form_data_encoded,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                self.assertEqual(status, 201, body)

                # Step 2: Get the OTC from verification email
                file_name_hash = hashlib.sha256(
                    f"{SENDER}{email}".encode()
                ).hexdigest()
                test_file = os.environ.get(
                    "EDGEDB_TEST_EMAIL_FILE",
                    f"/tmp/edb-test-email-{file_name_hash}.pickle",
                )
                with open(test_file, "rb") as f:
                    email_args = pickle.load(f)

                msg = cast(EmailMessage, email_args["message"])
                html_content = (
                    msg.get_body(('html',)).get_payload(decode=True).decode('utf-8')
                )

                # Extract the 6-digit code from email
                code_match = re.search(r'(?:^|\s)(\d{6})(?:\s|$)', html_content)
                self.assertIsNotNone(
                    code_match, "No 6-digit code found in verification email"
                )
                otc_code = code_match.group(1)

                # Step 3: Verify email with the code
                verify_body, verify_headers, verify_status = self.http_con_request(
                    http_con,
                    method="POST",
                    path="verify",
                    body=json.dumps(
                        {
                            "provider": "builtin::local_emailpassword",
                            "email": email,
                            "code": otc_code,
                            "challenge": challenge,
                        }
                    ).encode(),
                    headers={"Content-Type": "application/json"},
                )

                self.assertEqual(verify_status, 200, verify_body)

                # Should return successful verification response
                verify_data = json.loads(verify_body)
                self.assertEqual(verify_data.get("status"), "verified")

                # Step 4: Now should be able to authenticate with email+password
                auth_body, auth_headers, auth_status = self.http_con_request(
                    http_con,
                    method="POST",
                    path="authenticate",
                    body=json.dumps(
                        {
                            "provider": "builtin::local_emailpassword",
                            "email": email,
                            "password": password,
                            "challenge": challenge,
                        }
                    ).encode(),
                    headers={"Content-Type": "application/json"},
                )

                self.assertEqual(auth_status, 200, auth_body)
                auth_data = json.loads(auth_body)
                code = auth_data.get("code")

                # Step 5: Exchange auth code for token
                token_body, token_headers, token_status = self.http_con_request(
                    http_con,
                    params={
                        "code": code,
                        "verifier": verifier,
                    },
                    method="GET",
                    path="token",
                )
                self.assertEqual(token_status, 200, token_body)
                token_data = json.loads(token_body)
                self.assertIn("auth_token", token_data)

                # Step 6: Test webhook events were sent
                async for tr in self.try_until_succeeds(
                    delay=2, timeout=120, ignore=(KeyError, AssertionError)
                ):
                    async with tr:
                        requests_for_webhook = self.mock_net_server.requests[
                            webhook_request
                        ]
                        # Should have 5 webhook events: IdentityCreated, EmailFactorCreated,
                        # OneTimeCodeRequested, OneTimeCodeVerified, EmailVerified
                        self.assertEqual(len(requests_for_webhook), 5)

                # Parse and validate webhook events
                event_types: dict[str, dict | None] = {
                    "IdentityCreated": None,
                    "EmailFactorCreated": None,
                    "OneTimeCodeRequested": None,
                    "OneTimeCodeVerified": None,
                    "EmailVerified": None,
                }

                for request in requests_for_webhook:
                    assert request.body is not None
                    event_data = json.loads(request.body)
                    event_type = event_data["event_type"]
                    self.assertIn(event_type, event_types)
                    event_types[event_type] = event_data

                # Verify all expected events were received
                self.assertTrue(
                    all(value is not None for value in event_types.values())
                )

                # Validate OneTimeCodeRequested event structure
                otc_requested = cast(dict, event_types["OneTimeCodeRequested"])
                self.assertIn("identity_id", otc_requested)
                self.assertIn("email_factor_id", otc_requested)
                self.assertIn("otc_id", otc_requested)
                self.assertIn("one_time_code", otc_requested)
                # Verify the code is a 6-digit string
                self.assertEqual(len(otc_requested["one_time_code"]), 6)
                self.assertTrue(otc_requested["one_time_code"].isdigit())

                # Validate OneTimeCodeVerified event structure
                otc_verified = cast(dict, event_types["OneTimeCodeVerified"])
                self.assertIn("identity_id", otc_verified)
                self.assertIn("email_factor_id", otc_verified)
                self.assertIn("otc_id", otc_verified)

                # Validate EmailVerified event (should be sent after OTC verification)
                email_verified = cast(dict, event_types["EmailVerified"])
                self.assertIn("identity_id", email_verified)
                self.assertIn("email_factor_id", email_verified)

                # Verify the events reference the same identity
                self.assertEqual(
                    otc_requested["identity_id"],
                    otc_verified["identity_id"]
                )
                self.assertEqual(
                    otc_verified["identity_id"],
                    email_verified["identity_id"]
                )

        finally:
            # Clean up webhook config
            await self.con.query(
                "CONFIGURE CURRENT DATABASE RESET ext::auth::WebhookConfig"
            )

    async def test_http_ext_auth_otc_email_password_01(self):
        """Test Email+Password OTC verification with invalid code.

        Ensures that Email+Password verification properly rejects invalid codes
        and returns appropriate error responses. This tests the security aspect
        of preventing unauthorized account verification through invalid codes.
        """

        # Configure for OTC
        await self.con.query("""
            CONFIGURE CURRENT DATABASE
            RESET ext::auth::EmailPasswordProviderConfig;

            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::EmailPasswordProviderConfig {
                require_verification := true,
                verification_method := ext::auth::VerificationMethod.Code,
            };
        """)

        email = f"{uuid.uuid4()}@example.com"
        password = "test_password_invalid"

        with self.http_con() as http_con:
            # Register to create factor
            form_data = {
                "provider": "builtin::local_emailpassword",
                "email": email,
                "password": password,
                "challenge": str(uuid.uuid4()),
            }
            form_data_encoded = urllib.parse.urlencode(form_data).encode()

            self.http_con_request(
                http_con,
                method="POST",
                path="register",
                body=form_data_encoded,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Try to verify with invalid code
            verify_body, verify_headers, verify_status = self.http_con_request(
                http_con,
                method="POST",
                path="verify",
                body=json.dumps(
                    {
                        "provider": "builtin::local_emailpassword",
                        "email": email,
                        "code": "000000",  # Invalid code
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
            )

            self.assertEqual(verify_status, 400, verify_body)
            verify_data = json.loads(verify_body)
            self.assertIn("error", verify_data)

    async def test_http_ext_auth_otc_webhook_failure_events(self):
        """Test that webhook events are properly sent/not sent during OTC failures.

        Verifies that OneTimeCodeRequested is sent during registration, but
        OneTimeCodeVerified is NOT sent when verification fails with invalid codes.
        This ensures webhook consistency and proper failure handling.
        """

        # Configure for OTC
        await self.con.query("""
            CONFIGURE CURRENT DATABASE
            RESET ext::auth::EmailPasswordProviderConfig;

            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::EmailPasswordProviderConfig {
                require_verification := true,
                verification_method := ext::auth::VerificationMethod.Code,
            };
        """)

        # Set up webhook configuration
        base_url = self.mock_net_server.get_base_url().rstrip("/")
        webhook_url = f"{base_url}/failure-webhook"
        await self.con.query(
            """
            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::WebhookConfig {
                url := <str>$url,
                events := {
                    ext::auth::WebhookEvent.OneTimeCodeRequested,
                    ext::auth::WebhookEvent.OneTimeCodeVerified,
                    ext::auth::WebhookEvent.IdentityCreated,
                    ext::auth::WebhookEvent.EmailFactorCreated,
                },
            };
            """,
            url=webhook_url,
        )

        webhook_request = (
            "POST",
            base_url,
            "/failure-webhook",
        )
        self.mock_net_server.register_route_handler(*webhook_request)(
            ("", 204)
        )

        await self._wait_for_db_config("ext::auth::AuthConfig::webhooks")

        email = f"{uuid.uuid4()}@example.com"
        password = "test_password_failure"

        try:
            with self.http_con() as http_con:
                # Step 1: Register (should send OneTimeCodeRequested)
                form_data = {
                    "provider": "builtin::local_emailpassword",
                    "email": email,
                    "password": password,
                    "challenge": str(uuid.uuid4()),
                }
                form_data_encoded = urllib.parse.urlencode(form_data).encode()

                body, headers, status = self.http_con_request(
                    http_con,
                    method="POST",
                    path="register",
                    body=form_data_encoded,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                self.assertEqual(status, 201, body)

                # Step 2: Try to verify with invalid code (should NOT send OneTimeCodeVerified)
                verify_body, verify_headers, verify_status = self.http_con_request(
                    http_con,
                    method="POST",
                    path="verify",
                    body=json.dumps(
                        {
                            "provider": "builtin::local_emailpassword",
                            "email": email,
                            "code": "000000",  # Invalid code
                        }
                    ).encode(),
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(verify_status, 400, verify_body)

                # Step 3: Verify webhook events
                async for tr in self.try_until_succeeds(
                    delay=2, timeout=120, ignore=(KeyError, AssertionError)
                ):
                    async with tr:
                        requests_for_webhook = self.mock_net_server.requests[
                            webhook_request
                        ]
                        # Should have 3 webhook events: IdentityCreated, EmailFactorCreated,
                        # OneTimeCodeRequested (but NOT OneTimeCodeVerified)
                        self.assertEqual(len(requests_for_webhook), 3)

                # Parse and validate webhook events
                received_event_types = set()
                for request in requests_for_webhook:
                    assert request.body is not None
                    event_data = json.loads(request.body)
                    event_type = event_data["event_type"]
                    received_event_types.add(event_type)

                # Verify expected events were received
                expected_events = {
                    "IdentityCreated",
                    "EmailFactorCreated",
                    "OneTimeCodeRequested"
                }
                self.assertEqual(received_event_types, expected_events)

                # Verify OneTimeCodeVerified was NOT sent
                self.assertNotIn("OneTimeCodeVerified", received_event_types)

        finally:
            # Clean up webhook config
            await self.con.query(
                "CONFIGURE CURRENT DATABASE RESET ext::auth::WebhookConfig"
            )

    async def test_http_ext_auth_otc_email_password_02(self):
        """Test that Email+Password still works with verification_method=Link (default).

        Validates backward compatibility by ensuring Email+Password authentication
        continues to work with traditional link-based verification. This ensures
        that existing implementations using verification links continue to function
        without modification when the OTC feature is added.
        """

        # Ensure Email+Password provider uses Link mode (default)
        await self.con.query("""
            CONFIGURE CURRENT DATABASE
            RESET ext::auth::EmailPasswordProviderConfig;

            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::EmailPasswordProviderConfig {
                require_verification := true,
                verification_method := ext::auth::VerificationMethod.Link,
            };
        """)

        email = f"{uuid.uuid4()}@example.com"
        password = "test_password_link_mode"

        with self.http_con() as http_con:
            # Register (should send traditional verification link)
            form_data = {
                "provider": "builtin::local_emailpassword",
                "email": email,
                "password": password,
                "challenge": str(uuid.uuid4()),
            }
            form_data_encoded = urllib.parse.urlencode(form_data).encode()

            body, headers, status = self.http_con_request(
                http_con,
                method="POST",
                path="register",
                body=form_data_encoded,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            self.assertEqual(status, 201, body)

            # Get traditional verification link from email
            file_name_hash = hashlib.sha256(
                f"{SENDER}{email}".encode()
            ).hexdigest()
            test_file = os.environ.get(
                "EDGEDB_TEST_EMAIL_FILE",
                f"/tmp/edb-test-email-{file_name_hash}.pickle",
            )
            with open(test_file, "rb") as f:
                email_args = pickle.load(f)

            msg = cast(EmailMessage, email_args["message"])
            html_content = (
                msg.get_body(('html',)).get_payload(decode=True).decode('utf-8')
            )

            # Should contain verification link with token, not OTC
            link_match = re.search(
                r'<p style="word-break: break-all">([^<]+)', html_content
            )
            self.assertIsNotNone(
                link_match, "No verification link found in email"
            )
            verify_url = urllib.parse.urlparse(link_match.group(1))
            search_params = urllib.parse.parse_qs(verify_url.query)
            verification_token = search_params.get(
                "verification_token", [None]
            )[0]
            self.assertIsNotNone(verification_token)

            # Should NOT contain 6-digit code
            code_match = re.search(r'(?:^|\s)(\d{6})(?:\s|$)', html_content)
            self.assertIsNone(
                code_match, "Unexpected OTC found in Link mode email"
            )

    async def test_http_ext_auth_otc_12(self):
        """Test that expired OTCs are cleaned up during any verification attempt.

        Validates that the verification process automatically removes expired OTCs
        from the database during any verification attempt, not just successful ones.
        This prevents database bloat and maintains clean state even when users
        attempt to verify with invalid or expired codes.
        """

        # Configure for OTC
        await self.con.query("""
            CONFIGURE CURRENT DATABASE
            RESET ext::auth::MagicLinkProviderConfig;

            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::MagicLinkProviderConfig {
                verification_method := ext::auth::VerificationMethod.Code,
            };
        """)

        email = f"{uuid.uuid4()}@example.com"
        callback_url = "https://example.com/app/auth/callback"
        error_url = "https://example.com/app/auth/error"
        verifier, challenge = self.generate_pkce_pair()

        with self.http_con() as http_con:
            # Create factor by registering
            register_body, register_headers, register_status = (
                self.http_con_request(
                    http_con,
                    method="POST",
                    path="magic-link/register",
                    body=json.dumps(
                        {
                            "provider": "builtin::local_magic_link",
                            "email": email,
                            "challenge": challenge,
                            "callback_url": callback_url,
                            "redirect_on_failure": error_url,
                        }
                    ).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
            )
            self.assertEqual(register_status, 200, register_body)

            factor = await self.con.query_required_single(
                """
                select assert_exists((
                    SELECT ext::auth::EmailFactor { id }
                    FILTER .email = <str>$email
                    limit 1
                ))
                """,
                email=email,
            )

            # Manually create several expired OTCs in the database
            expired_time = utcnow() - datetime.timedelta(minutes=5)
            for i in range(3):
                await self.con.query(
                    """
                    INSERT ext::auth::OneTimeCode {
                        factor := <ext::auth::Factor><uuid>$factor_id,
                        code_hash := <bytes>$code_hash,
                        expires_at := <datetime>$expires_at,
                    };
                """,
                    factor_id=factor.id,
                    code_hash=otc.hash_code(f"12345{i}"),
                    expires_at=expired_time,
                )

            # Verify there are 4 expired codes: 3 from the loop above, plus the
            # one that was created by the register request.
            expired_codes_query = """
                SELECT count(
                    SELECT ext::auth::OneTimeCode
                    FILTER .factor.id = <uuid>$factor_id
                )
            """
            expired_count = await self.con.query_single(
                expired_codes_query,
                factor_id=factor.id,
            )
            self.assertEqual(expired_count, 4)

            # Try to verify with invalid code - should trigger cleanup
            self.http_con_request(
                http_con,
                params={
                    "email": email,
                    "code": "999999",
                    "challenge": challenge,
                    "callback_url": callback_url,
                },
                method="GET",
                path="magic-link/authenticate",
            )

            # All the manually created expired codes should be cleaned up
            remaining_count = await self.con.query_single(
                expired_codes_query,
                factor_id=factor.id,
            )
            self.assertEqual(remaining_count, 1)

    async def test_http_ext_auth_otc_13(self):
        """Test that rate limiting works across different OTC verification attempts.

        Ensures that rate limiting is properly enforced across multiple failed
        verification attempts and that the system blocks further attempts after
        reaching the limit. This tests the security mechanism that prevents
        brute force attacks on OTC verification endpoints.
        """

        # Configure for OTC
        await self.con.query("""
            CONFIGURE CURRENT DATABASE
            RESET ext::auth::MagicLinkProviderConfig;

            CONFIGURE CURRENT DATABASE
            INSERT ext::auth::MagicLinkProviderConfig {
                verification_method := ext::auth::VerificationMethod.Code,
            };
        """)

        email = f"{uuid.uuid4()}@example.com"
        callback_url = "https://example.com/app/auth/callback"
        error_url = "https://example.com/app/auth/error"
        verifier, challenge = self.generate_pkce_pair()

        with self.http_con() as http_con:
            # Register to create factor
            register_body, register_headers, register_status = (
                self.http_con_request(
                    http_con,
                    method="POST",
                    path="magic-link/register",
                    body=json.dumps(
                        {
                            "provider": "builtin::local_magic_link",
                            "email": email,
                            "callback_url": callback_url,
                            "redirect_on_failure": error_url,
                            "challenge": challenge,
                        }
                    ).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
            )
            self.assertEqual(register_status, 200, register_body)

            # Make 5 failed attempts to trigger rate limiting
            for i in range(5):
                body, headers, status = self.http_con_request(
                    http_con,
                    params={
                        "email": email,
                        "code": f"00000{i}",
                        "challenge": challenge,
                        "callback_url": callback_url,
                    },
                    method="GET",
                    path="magic-link/authenticate",
                    headers={
                        "Accept": "application/json",
                    },
                )
                self.assertEqual(status, 400, body)
                self.assertIn("invalid code", body.decode().lower())

            # 6th attempt should be rate limited
            body, headers, status = self.http_con_request(
                http_con,
                params={
                    "email": email,
                    "code": "000006",
                    "challenge": challenge,
                    "callback_url": callback_url,
                },
                method="GET",
                path="magic-link/authenticate",
                headers={
                    "Accept": "application/json",
                },
            )
            self.assertEqual(status, 400, body)
            # Should contain rate limiting message
            self.assertIn("attempts exceeded", body.decode().lower())
