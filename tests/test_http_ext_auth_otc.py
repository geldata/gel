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
import hmac

from typing import Optional, cast
from email.message import EmailMessage

from edgedb import QueryAssertionError, ConstraintViolationError
from edb.testbase import http as tb
from edb.common import assert_data_shape
from edb.server.protocol.auth_ext import jwt as auth_jwt
from edb.server.auth import JWKSet

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

    async def test_http_ext_auth_otc_smoke(self):
        pass

    async def test_http_ext_auth_otc_basic_otc_objects(self):
        """Test that the schema migration additions work correctly."""

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

        # Test that OneTimeCode type exists and can be created
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
                        max_attempts := 5,
                        attempts := 0,
                    }
                ),
            select ONE_TIME_CODE { ** };
        """,
            expires_at=expires_at,
            factor_id=email_factor.id,
        )

        expected_hash = hashlib.sha256(b"test_hash_123").digest()
        self.assertEqual(otc.code_hash, expected_hash)
        self.assertEqual(otc.max_attempts, 5)
        self.assertEqual(otc.attempts, 0)

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
                            max_attempts := 5,
                            attempts := 0,
                        }
                    ),
                select ONE_TIME_CODE { ** };
                """,
                expires_at=expires_at,
                factor_id=email_factor.id,
            )
