#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2022-present MagicStack Inc. and the EdgeDB authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
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


from __future__ import annotations

import datetime
import http
import http.cookies
import json
import logging
import urllib.parse
import base64
import hashlib
import os
import mimetypes
import uuid
import dataclasses

from typing import (
    Any,
    Optional,
    cast,
    TYPE_CHECKING,
    Callable,
)

import aiosmtplib

from edb import errors as edb_errors
from edb.common import debug
from edb.common import markup
from edb.server import tenant as edbtenant, metrics
from edb.server.config.types import CompositeConfigType
from edb.ir import statypes

from . import (
    email_password,
    oauth,
    errors,
    util,
    pkce,
    ui,
    config,
    email as auth_emails,
    webauthn,
    magic_link,
    webhook,
    jwt,
    otc,
    local,
)
from .data import EmailFactor

if TYPE_CHECKING:
    from edb.server.protocol import protocol


logger = logging.getLogger('edb.server.ext.auth')


class Router:
    test_url: Optional[str]

    def __init__(
        self,
        *,
        db: edbtenant.dbview.Database,
        base_path: str,
        tenant: edbtenant.Tenant,
    ):
        self.db = db
        self.base_path = base_path
        self.tenant = tenant
        self.test_mode = tenant.server.in_test_mode()
        self.signing_key = jwt.SigningKey(
            lambda: util.get_config(
                self.db, "ext::auth::AuthConfig::auth_signing_key"
            ),
            self.base_path,
        )

    def _get_url_munger(
        self, request: protocol.HttpRequest
    ) -> Callable[[str], str] | None:
        """
        Returns a callable that can be used to modify the base URL
        when making requests to the OAuth provider.

        This is used to redirect requests to the test OAuth provider
        when running in test mode.
        """
        if not self.test_mode:
            return None
        test_url = (
            request.params[b'oauth-test-server'].decode()
            if (request.params and b'oauth-test-server' in request.params)
            else None
        )
        if test_url:
            return lambda path: f"{test_url}{urllib.parse.quote(path)}"
        return None

    async def handle_request(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
        args: list[str],
    ) -> None:
        if self.db.db_config is None:
            await self.db.introspection()

        self.test_url = (
            request.params[b'oauth-test-server'].decode()
            if (
                self.test_mode
                and request.params
                and b'oauth-test-server' in request.params
            )
            else None
        )

        logger.info(
            f"Handling incoming HTTP request: /ext/auth/{'/'.join(args)}"
        )

        try:
            match args:
                # PKCE token exchange route
                case ("token",):
                    await self.handle_token(request, response)

                # OAuth routes
                case ("authorize",):
                    await self.handle_authorize(request, response)
                case ("callback",):
                    await self.handle_callback(request, response)

                # Email/password routes
                case ("register",):
                    await self.handle_register(request, response)
                case ("authenticate",):
                    await self.handle_authenticate(request, response)
                case ('send-reset-email',):
                    await self.handle_send_reset_email(request, response)
                case ('reset-password',):
                    await self.handle_reset_password(request, response)

                # Magic link routes
                case ('magic-link', 'register'):
                    await self.handle_magic_link_register(request, response)
                case ('magic-link', 'email'):
                    await self.handle_magic_link_email(request, response)
                case ('magic-link', 'authenticate'):
                    await self.handle_magic_link_authenticate(request, response)

                # WebAuthn routes
                case ('webauthn', 'register'):
                    await self.handle_webauthn_register(request, response)
                case ('webauthn', 'register', 'options'):
                    await self.handle_webauthn_register_options(
                        request, response
                    )
                case ('webauthn', 'authenticate'):
                    await self.handle_webauthn_authenticate(request, response)
                case ('webauthn', 'authenticate', 'options'):
                    await self.handle_webauthn_authenticate_options(
                        request, response
                    )

                # Email verification routes
                case ("verify",):
                    await self.handle_verify(request, response)
                case ("resend-verification-email",):
                    await self.handle_resend_verification_email(
                        request, response
                    )

                # UI routes
                case ('ui', 'signin'):
                    await self.handle_ui_signin(request, response)
                case ('ui', 'signup'):
                    await self.handle_ui_signup(request, response)
                case ('ui', 'forgot-password'):
                    await self.handle_ui_forgot_password(request, response)
                case ('ui', 'reset-password'):
                    await self.handle_ui_reset_password(request, response)
                case ("ui", "verify"):
                    await self.handle_ui_verify(request, response)
                case ("ui", "resend-verification"):
                    await self.handle_ui_resend_verification(request, response)
                case ("ui", "magic-link-sent"):
                    await self.handle_ui_magic_link_sent(request, response)
                case ('ui', '_static', filename):
                    filepath = os.path.join(
                        os.path.dirname(__file__), '_static', filename
                    )
                    try:
                        with open(filepath, 'rb') as f:
                            response.status = http.HTTPStatus.OK
                            response.content_type = (
                                mimetypes.guess_type(filename)[0]
                                or 'application/octet-stream'
                            ).encode()
                            response.body = f.read()
                    except FileNotFoundError:
                        response.status = http.HTTPStatus.NOT_FOUND

                case _:
                    raise errors.NotFound("Unknown auth endpoint")

        # User-facing errors
        except errors.NotFound as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.NOT_FOUND,
                ex=ex,
            )

        except errors.InvalidData as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.BAD_REQUEST,
                ex=ex,
            )

        except errors.PKCEVerificationFailed as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.FORBIDDEN,
                ex=ex,
            )

        except errors.NoIdentityFound as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.FORBIDDEN,
                ex=ex,
            )

        except errors.UserAlreadyRegistered as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.CONFLICT,
                ex=ex,
            )

        except errors.VerificationRequired as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.UNAUTHORIZED,
                ex=ex,
            )

        # Server errors
        except errors.MissingConfiguration as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                ex=ex,
            )

        except errors.WebAuthnRegistrationFailed as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.BAD_REQUEST,
                ex=ex,
                exc_info=True,
            )

        except errors.WebAuthnAuthenticationFailed as ex:
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.UNAUTHORIZED,
                ex=ex,
                exc_info=True,
            )

        except Exception as ex:
            if debug.flags.server:
                markup.dump(ex)
            _fail_with_error(
                response=response,
                status=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                ex=edb_errors.InternalServerError(str(ex)),
                exc_info=True,
            )

    async def handle_authorize(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )
        provider_name = _get_search_param(query, "provider")
        allowed_redirect_to = self._make_allowed_url(
            _get_search_param(query, "redirect_to")
        )
        allowed_redirect_to_on_signup = self._maybe_make_allowed_url(
            _maybe_get_search_param(query, "redirect_to_on_signup")
        )
        allowed_callback_url = self._maybe_make_allowed_url(
            _maybe_get_search_param(query, "callback_url")
        )
        challenge = _get_search_param(
            query, "challenge", fallback_keys=["code_challenge"]
        )
        oauth_client = oauth.Client(
            db=self.db,
            provider_name=provider_name,
            url_munger=self._get_url_munger(request),
            http_client=self.tenant.get_http_client(originator="auth"),
        )
        await pkce.create(self.db, challenge)
        redirect_uri = (
            allowed_callback_url.url
            if allowed_callback_url
            else self._get_callback_url()
        )
        authorize_url = await oauth_client.get_authorize_url(
            redirect_uri=redirect_uri,
            state=jwt.OAuthStateToken(
                provider=provider_name,
                redirect_to=allowed_redirect_to.url,
                redirect_to_on_signup=(
                    allowed_redirect_to_on_signup.url
                    if allowed_redirect_to_on_signup
                    else None
                ),
                challenge=challenge,
                redirect_uri=redirect_uri,
            ).sign(self.signing_key),
        )
        # n.b. Explicitly allow authorization URL to be outside of allowed
        # URLs because it is a trusted URL from the identity provider.
        self._do_redirect(response, AllowedUrl(authorize_url))

    async def handle_callback(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        if request.method == b"POST" and (
            request.content_type == b"application/x-www-form-urlencoded"
        ):
            form_data = urllib.parse.parse_qs(request.body.decode())
            state = _maybe_get_form_field(form_data, "state")
            code = _maybe_get_form_field(form_data, "code")

            error = _maybe_get_form_field(form_data, "error")
            error_description = _maybe_get_form_field(
                form_data, "error_description"
            )
        elif request.url.query is not None:
            query = urllib.parse.parse_qs(
                request.url.query.decode("ascii") if request.url.query else ""
            )
            state = _maybe_get_search_param(query, "state")
            code = _maybe_get_search_param(query, "code")
            error = _maybe_get_search_param(query, "error")
            error_description = _maybe_get_search_param(
                query, "error_description"
            )
        else:
            raise errors.OAuthProviderFailure(
                "Provider did not respond with expected data"
            )

        if state is None:
            raise errors.InvalidData(
                "Provider did not include the 'state' parameter in callback"
            )

        if error is not None:
            try:
                claims = jwt.OAuthStateToken.verify(state, self.signing_key)
                redirect_to = claims.redirect_to
            except Exception:
                raise errors.InvalidData("Invalid state token")

            params = {
                "error": error,
            }
            error_str = error
            if error_description is not None:
                params["error_description"] = error_description
                error_str += f": {error_description}"

            logger.debug(f"OAuth provider returned an error: {error_str}")
            return self._try_redirect(
                response,
                util.join_url_params(redirect_to, params),
            )

        if code is None:
            raise errors.InvalidData(
                "Provider did not include the 'code' parameter in callback"
            )

        try:
            claims = jwt.OAuthStateToken.verify(state, self.signing_key)
            provider_name = claims.provider
            allowed_redirect_to = self._make_allowed_url(claims.redirect_to)
            allowed_redirect_to_on_signup = self._maybe_make_allowed_url(
                claims.redirect_to_on_signup
            )
            challenge = claims.challenge
            redirect_uri = claims.redirect_uri
        except Exception:
            raise errors.InvalidData("Invalid state token")
        oauth_client = oauth.Client(
            db=self.db,
            provider_name=provider_name,
            url_munger=self._get_url_munger(request),
            http_client=self.tenant.get_http_client(originator="auth"),
        )
        (
            identity,
            new_identity,
            auth_token,
            refresh_token,
            id_token,
        ) = await oauth_client.handle_callback(code, redirect_uri)
        if new_identity:
            await self._maybe_send_webhook(
                webhook.IdentityCreated(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    identity_id=identity.id,
                )
            )
        pkce_code = await pkce.link_identity_challenge(
            self.db, identity.id, challenge
        )
        if auth_token or refresh_token:
            await pkce.add_provider_tokens(
                self.db,
                id=pkce_code,
                auth_token=auth_token,
                refresh_token=refresh_token,
                id_token=id_token,
            )
        new_url = (
            (allowed_redirect_to_on_signup or allowed_redirect_to)
            if new_identity
            else allowed_redirect_to
        ).map(
            lambda u: util.join_url_params(
                u, {"code": pkce_code, "provider": provider_name}
            )
        )
        logger.info(
            "OAuth callback successful: "
            f"identity_id={identity.id}, new_identity={new_identity}"
        )
        self._do_redirect(response, new_url)

    async def handle_token(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )
        code = _get_search_param(query, "code")
        verifier = _get_search_param(
            query, "verifier", fallback_keys=["code_verifier"]
        )

        verifier_size = len(verifier)

        if verifier_size < 43:
            raise errors.InvalidData(
                "Verifier must be at least 43 characters long"
            )
        if verifier_size > 128:
            raise errors.InvalidData(
                "Verifier must be shorter than 128 characters long"
            )
        try:
            pkce_object = await pkce.get_by_id(self.db, code)
        except Exception:
            raise errors.NoIdentityFound("Could not find a matching PKCE code")

        if pkce_object.identity_id is None:
            raise errors.InvalidData("Code is not associated with an Identity")

        hashed_verifier = hashlib.sha256(verifier.encode()).digest()
        base64_url_encoded_verifier = base64.urlsafe_b64encode(
            hashed_verifier
        ).rstrip(b'=')

        if base64_url_encoded_verifier.decode() == pkce_object.challenge:
            await pkce.delete(self.db, code)

            identity_id = pkce_object.identity_id
            await self._maybe_send_webhook(
                webhook.IdentityAuthenticated(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    identity_id=identity_id,
                )
            )
            auth_expiration_time = util.get_config(
                self.db,
                "ext::auth::AuthConfig::token_time_to_live",
                statypes.Duration,
            )
            session_token = jwt.SessionToken(
                subject=identity_id,
            ).sign(
                self.signing_key,
                expires_in=auth_expiration_time.to_timedelta(),
            )
            metrics.auth_successful_logins.inc(
                1.0, self.tenant.get_instance_name()
            )
            logger.info(f"Token exchange successful: identity_id={identity_id}")
            response.status = http.HTTPStatus.OK
            response.content_type = b"application/json"
            response.body = json.dumps(
                {
                    "auth_token": session_token,
                    "identity_id": identity_id,
                    "provider_token": pkce_object.auth_token,
                    "provider_refresh_token": pkce_object.refresh_token,
                    "provider_id_token": pkce_object.id_token,
                }
            ).encode()
        else:
            raise errors.PKCEVerificationFailed

    async def handle_register(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        allowed_redirect_to = self._maybe_make_allowed_url(
            cast(Optional[str], data.get("redirect_to"))
        )

        maybe_challenge = cast(Optional[str], data.get("challenge"))
        register_provider_name = cast(Optional[str], data.get("provider"))
        if register_provider_name is None:
            raise errors.InvalidData('Missing "provider" in register request')

        email_password_client = email_password.Client(db=self.db)
        require_verification = email_password_client.config.require_verification
        if not require_verification and maybe_challenge is None:
            raise errors.InvalidData('Missing "challenge" in register request')
        pkce_code: Optional[str] = None

        try:
            email_factor = await email_password_client.register(data)
            identity = email_factor.identity

            verify_url = data.get("verify_url", f"{self.base_path}/ui/verify")
            verification_token = self._make_verification_token(
                identity_id=identity.id,
                verify_url=verify_url,
                maybe_challenge=maybe_challenge,
                maybe_redirect_to=(
                    allowed_redirect_to.url if allowed_redirect_to else None
                ),
            )

            await self._maybe_send_webhook(
                webhook.IdentityCreated(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    identity_id=identity.id,
                )
            )
            await self._maybe_send_webhook(
                webhook.EmailFactorCreated(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    identity_id=identity.id,
                    email_factor_id=email_factor.id,
                )
            )
            await self._maybe_send_webhook(
                webhook.EmailVerificationRequested(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    identity_id=identity.id,
                    email_factor_id=email_factor.id,
                    verification_token=verification_token,
                )
            )

            if require_verification:
                response_dict = {
                    "identity_id": identity.id,
                    "email": email_factor.email,
                    "verification_email_sent_at": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                }
            else:
                # Checked at the beginning of the route handler
                assert maybe_challenge is not None
                await pkce.create(self.db, maybe_challenge)
                pkce_code = await pkce.link_identity_challenge(
                    self.db, identity.id, maybe_challenge
                )
                response_dict = {
                    "code": pkce_code,
                    "email": email_factor.email,
                    "provider": register_provider_name,
                }

            await self._send_verification_email(
                provider=register_provider_name,
                verification_token=verification_token,
                to_addr=data["email"],
                verify_url=verify_url,
            )

            logger.info(
                f"Identity created: identity_id={identity.id}, "
                f"pkce_id={pkce_code!r}"
            )

            if allowed_redirect_to is not None:
                self._do_redirect(
                    response,
                    allowed_redirect_to.map(
                        lambda u: util.join_url_params(u, response_dict)
                    ),
                )
            else:
                response.status = http.HTTPStatus.CREATED
                response.content_type = b"application/json"
                response.body = json.dumps(response_dict).encode()
        except Exception as ex:
            redirect_on_failure = data.get(
                "redirect_on_failure", data.get("redirect_to")
            )
            if redirect_on_failure is not None:
                error_message = str(ex)
                email = data.get("email", "")
                logger.error(
                    f"Error creating identity: error={error_message}, "
                    f"email={email}"
                )
                error_redirect_url = util.join_url_params(
                    redirect_on_failure,
                    {
                        "error": error_message,
                        "email": email,
                    },
                )
                return self._try_redirect(response, error_redirect_url)
            else:
                raise ex

    async def handle_authenticate(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        _check_keyset(data, {"provider", "challenge", "email", "password"})
        challenge = data["challenge"]
        email = data["email"]
        password = data["password"]

        await pkce.create(self.db, challenge)

        allowed_redirect_to = self._maybe_make_allowed_url(
            cast(Optional[str], data.get("redirect_to"))
        )

        email_password_client = email_password.Client(db=self.db)
        try:
            local_identity = await email_password_client.authenticate(
                email, password
            )
            verified_at = (
                await email_password_client.get_verified_by_identity_id(
                    identity_id=local_identity.id
                )
            )
            if (
                email_password_client.config.require_verification
                and verified_at is None
            ):
                raise errors.VerificationRequired()

            pkce_code = await pkce.link_identity_challenge(
                self.db, local_identity.id, challenge
            )
            response_dict = {"code": pkce_code}
            logger.info(
                f"Authentication successful: identity_id={local_identity.id}, "
                f"pkce_id={pkce_code}"
            )
            if allowed_redirect_to:
                self._do_redirect(
                    response,
                    allowed_redirect_to.map(
                        lambda u: util.join_url_params(u, response_dict)
                    ),
                )
            else:
                response.status = http.HTTPStatus.OK
                response.content_type = b"application/json"
                response.body = json.dumps(response_dict).encode()
        except Exception as ex:
            redirect_on_failure = data.get(
                "redirect_on_failure", data.get("redirect_to")
            )
            if redirect_on_failure is not None:
                error_message = str(ex)
                email = data.get("email", "")
                logger.error(
                    f"Error authenticating: error={error_message}, "
                    f"email={email}"
                )
                error_redirect_url = util.join_url_params(
                    redirect_on_failure,
                    {
                        "error": error_message,
                        "email": email,
                    },
                )
                return self._try_redirect(response, error_redirect_url)
            else:
                raise ex

    async def handle_verify(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        verification_token = data.get("verification_token")
        email = data.get("email")
        code = data.get("code")
        provider = data.get("provider")

        if not provider:
            raise errors.InvalidData('Missing "provider" in verify request')

        if verification_token:
            try:
                token = jwt.VerificationToken.verify(
                    verification_token,
                    self.signing_key,
                )

                email_factor = await self._try_verify_email(
                    provider=provider,
                    identity_id=token.subject,
                )
                await self._maybe_send_webhook(
                    webhook.EmailVerified(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.datetime.now(datetime.timezone.utc),
                        identity_id=token.subject,
                        email_factor_id=email_factor.id,
                    )
                )
            except errors.VerificationTokenExpired:
                response.status = http.HTTPStatus.FORBIDDEN
                response.content_type = b"application/json"
                error_message = "The verification token is older than 24 hours"
                logger.error(f"Verification token expired: {error_message}")
                response.body = json.dumps({"message": error_message}).encode()
                return

            logger.info(
                f"Email verified via token: identity_id={token.subject}, "
                f"email_factor_id={email_factor.id}, "
                f"email={email_factor.email}"
            )
            identity_id = token.subject
            challenge = token.maybe_challenge
            redirect_to = token.maybe_redirect_to

        elif email and code:
            _check_keyset(
                data,
                {
                    "email",
                    "code",
                    "provider",
                },
            )
            email_client: local.Client
            if provider == "builtin::local_emailpassword":
                email_client = email_password.Client(db=self.db)
            elif provider == "builtin::local_webauthn":
                email_client = webauthn.Client(db=self.db)
            else:
                raise errors.InvalidData(f"Unsupported provider: {provider}")

            try:
                maybe_email_factor = (
                    await email_client.get_email_factor_by_email(email)
                )
                if maybe_email_factor is None:
                    raise errors.NoIdentityFound("Invalid email")

                email_factor = maybe_email_factor

                otc_id = await otc.verify(self.db, str(email_factor.id), code)

                await self._handle_otc_verified(
                    identity_id=str(email_factor.identity.id),
                    email_factor_id=str(email_factor.id),
                    otc_id=str(otc_id),
                )

                await self._try_verify_email(
                    provider=provider,
                    identity_id=email_factor.identity.id,
                )

                await self._maybe_send_webhook(
                    webhook.EmailVerified(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.datetime.now(datetime.timezone.utc),
                        identity_id=email_factor.identity.id,
                        email_factor_id=email_factor.id,
                    )
                )

                logger.info(
                    f"Email verified via OTC: "
                    f"identity_id={email_factor.identity.id}, "
                    f"email_factor_id={email_factor.id}, "
                    f"email={email}"
                )

                identity_id = email_factor.identity.id
                challenge = data.get("challenge")
                redirect_to = data.get("redirect_to")

            except Exception as ex:
                self._handle_otc_failed(ex)
                response.status = http.HTTPStatus.BAD_REQUEST
                response.content_type = b"application/json"
                response.body = json.dumps(
                    {"error": str(ex), "error_code": "verification_failed"}
                ).encode()
                return

        else:
            raise errors.InvalidData(
                'Must provide either "verification_token" (Link mode) '
                'or "email" + "code" (OTC mode)'
            )

        logger.info(f"Challenge: {challenge}, Redirect to: {redirect_to}")
        match (challenge, redirect_to):
            case (str(), str()):
                await pkce.create(self.db, challenge)
                code = await pkce.link_identity_challenge(
                    self.db, identity_id, challenge
                )
                return self._try_redirect(
                    response,
                    util.join_url_params(redirect_to, {"code": code}),
                )
            case (str(), None):
                await pkce.create(self.db, challenge)
                code = await pkce.link_identity_challenge(
                    self.db, identity_id, challenge
                )
                response.status = http.HTTPStatus.OK
                response.content_type = b"application/json"
                response.body = json.dumps({"code": code}).encode()
                return
            case (None, str()):
                return self._try_redirect(response, redirect_to)
            case (None, None):
                response.status = http.HTTPStatus.NO_CONTENT
                return

    async def handle_resend_verification_email(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        request_data = self._get_data_from_request(request)

        _check_keyset(request_data, {"provider"})
        provider_name = request_data["provider"]
        local_client: email_password.Client | webauthn.Client
        match provider_name:
            case "builtin::local_emailpassword":
                local_client = email_password.Client(db=self.db)
            case "builtin::local_webauthn":
                local_client = webauthn.Client(db=self.db)
            case _:
                raise errors.InvalidData(
                    f"Unsupported provider: {request_data['provider']}"
                )

        verify_url = request_data.get(
            "verify_url", f"{self.base_path}/ui/verify"
        )
        email_factor: Optional[EmailFactor] = None
        if "verification_token" in request_data:
            token = jwt.VerificationToken.verify(
                request_data["verification_token"],
                self.signing_key,
                skip_expiration_check=True,
            )
            identity_id = token.subject
            verify_url = token.verify_url
            maybe_challenge = token.maybe_challenge
            maybe_redirect_to = token.maybe_redirect_to
            email_factor = await local_client.get_email_factor_by_identity_id(
                identity_id
            )
        else:
            maybe_challenge = request_data.get(
                "challenge", request_data.get("code_challenge")
            )
            maybe_redirect_to = request_data.get("redirect_to")
            if maybe_redirect_to and not self._is_url_allowed(
                maybe_redirect_to
            ):
                raise errors.InvalidData(
                    "Redirect URL does not match any allowed URLs.",
                )
            match local_client:
                case webauthn.Client():
                    _check_keyset(request_data, {"credential_id"})
                    credential_id = base64.b64decode(
                        request_data["credential_id"]
                    )
                    email_factor = (
                        await local_client.get_email_factor_by_credential_id(
                            credential_id
                        )
                    )
                case email_password.Client():
                    _check_keyset(request_data, {"email"})
                    email_factor = await local_client.get_email_factor_by_email(
                        request_data["email"]
                    )

        if email_factor is None:
            match local_client:
                case webauthn.Client():
                    logger.debug(
                        f"Failed to find email factor for resend verification "
                        f"email: provider={provider_name}, "
                        f"webauthn_credential_id={request_data.get('credential_id')}"
                    )
                case email_password.Client():
                    logger.debug(
                        f"Failed to find email factor for resend verification "
                        f"email: provider={provider_name}, "
                        f"email={request_data.get('email')}"
                    )
            await auth_emails.send_fake_email(self.tenant)
        else:
            logger.info(
                f"Resending verification email: provider={provider_name}, "
                f"identity_id={email_factor.identity.id}, "
                f"email_factor_id={email_factor.id}, "
                f"email={email_factor.email}"
            )
            verification_token = self._make_verification_token(
                identity_id=email_factor.identity.id,
                verify_url=verify_url,
                maybe_challenge=maybe_challenge,
                maybe_redirect_to=maybe_redirect_to,
            )
            await self._maybe_send_webhook(
                webhook.EmailVerificationRequested(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    identity_id=email_factor.identity.id,
                    email_factor_id=email_factor.id,
                    verification_token=verification_token,
                )
            )
            await self._send_verification_email(
                provider=request_data["provider"],
                verification_token=verification_token,
                to_addr=email_factor.email,
                verify_url=verify_url,
            )

        response.status = http.HTTPStatus.OK

    async def handle_send_reset_email(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        _check_keyset(data, {"provider", "email", "reset_url", "challenge"})
        email = data["email"]
        email_password_client = email_password.Client(db=self.db)
        if not self._is_url_allowed(data["reset_url"]):
            raise errors.InvalidData(
                "Redirect URL does not match any allowed URLs.",
            )
        allowed_redirect_to = self._maybe_make_allowed_url(
            data.get("redirect_to")
        )

        try:
            try:
                (
                    email_factor,
                    secret,
                ) = await email_password_client.get_email_factor_and_secret(
                    email
                )
                identity_id = email_factor.identity.id

                if email_password_client.config.verification_method == "Code":
                    code, otc_id = await otc.create(
                        self.db,
                        str(email_factor.id),
                        datetime.timedelta(minutes=10),
                    )
                    await auth_emails.send_password_reset_code_email(
                        db=self.db,
                        tenant=self.tenant,
                        to_addr=email,
                        code=code,
                        test_mode=self.test_mode,
                    )

                    await self._handle_otc_initiated(
                        identity_id=identity_id,
                        email_factor_id=str(email_factor.id),
                        otc_id=str(otc_id),
                        one_time_code=code,
                    )

                    logger.info(
                        "Sent OTC password reset email: "
                        f"email={email}, otc_id={otc_id}"
                    )
                else:
                    new_reset_token = jwt.ResetToken(
                        subject=identity_id,
                        secret=secret,
                        challenge=data["challenge"],
                    ).sign(self.signing_key)

                    reset_token_params = {"reset_token": new_reset_token}
                    reset_url = util.join_url_params(
                        data['reset_url'], reset_token_params
                    )
                    await self._maybe_send_webhook(
                        webhook.PasswordResetRequested(
                            event_id=str(uuid.uuid4()),
                            timestamp=datetime.datetime.now(
                                datetime.timezone.utc
                            ),
                            identity_id=identity_id,
                            reset_token=new_reset_token,
                            email_factor_id=email_factor.id,
                        )
                    )

                    await auth_emails.send_password_reset_email(
                        db=self.db,
                        tenant=self.tenant,
                        to_addr=email,
                        reset_url=reset_url,
                        test_mode=self.test_mode,
                    )

            except errors.NoIdentityFound:
                logger.debug(
                    f"Failed to find identity for send reset email: "
                    f"email={email}"
                )
                await auth_emails.send_fake_email(self.tenant)

            return_data = {
                "email_sent": email,
            }

            if allowed_redirect_to:
                return self._do_redirect(
                    response,
                    allowed_redirect_to.map(
                        lambda u: util.join_url_params(u, return_data)
                    ),
                )
            else:
                response.status = http.HTTPStatus.OK
                response.content_type = b"application/json"
                response.body = json.dumps(return_data).encode()
        except aiosmtplib.SMTPException as ex:
            if not debug.flags.server:
                logger.warning("Failed to send emails via SMTP", exc_info=True)
            raise edb_errors.InternalServerError(
                "Failed to send the email, please try again later."
            ) from ex

        except Exception as ex:
            redirect_on_failure = data.get(
                "redirect_on_failure", data.get("redirect_to")
            )
            if redirect_on_failure is not None:
                error_message = str(ex)
                logger.error(
                    f"Error sending reset email: error={error_message}, "
                    f"email={email}"
                )
                redirect_url = util.join_url_params(
                    redirect_on_failure,
                    {
                        "error": error_message,
                        "email": email,
                    },
                )
                return self._try_redirect(
                    response,
                    redirect_url,
                )
            else:
                raise ex

    async def handle_reset_password(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        try:
            _check_keyset(data, {"password", "provider"})
            password = data['password']

            reset_token = data.get('reset_token')
            email = data.get('email')
            code = data.get('code')

            allowed_redirect_to = self._maybe_make_allowed_url(
                data.get("redirect_to")
            )

            email_password_client = email_password.Client(db=self.db)

            if reset_token:
                token = jwt.ResetToken.verify(
                    reset_token,
                    self.signing_key,
                )

                await email_password_client.update_password(
                    token.subject, token.secret, password
                )
                await pkce.create(self.db, token.challenge)
                code = await pkce.link_identity_challenge(
                    self.db, token.subject, token.challenge
                )
                response_dict = {"code": code}
                logger.info(
                    "Reset password via token: "
                    f"identity_id={token.subject}, pkce_id={code}"
                )

            elif email and code:
                try:
                    (
                        email_factor,
                        secret,
                    ) = await email_password_client.get_email_factor_and_secret(
                        email
                    )

                    otc_id = await otc.verify(
                        self.db, str(email_factor.id), code
                    )
                    logger.info(
                        "OTC verified for password reset: "
                        f"otc_id={otc_id}, email={email}"
                    )

                    await self._handle_otc_verified(
                        identity_id=email_factor.identity.id,
                        email_factor_id=str(email_factor.id),
                        otc_id=str(otc_id),
                    )
                except Exception as ex:
                    self._handle_otc_failed(ex)
                    raise

                try:
                    await email_password_client.update_password(
                        email_factor.identity.id, secret, password
                    )
                except Exception as ex:
                    raise errors.InvalidData(
                        f"Failed to reset password: {str(ex)}"
                    )

                challenge = data.get('challenge')
                if challenge:
                    await pkce.create(self.db, challenge)
                    auth_code = await pkce.link_identity_challenge(
                        self.db, email_factor.identity.id, challenge
                    )
                    response_dict = {"code": auth_code}
                    logger.info(
                        "Reset password via OTC: "
                        f"identity_id={email_factor.identity.id}, email={email}"
                    )
                else:
                    response_dict = {"status": "password_reset"}

            else:
                raise errors.InvalidData(
                    'Must provide either "reset_token" (Token mode) '
                    'or "email" + "code" (OTC mode)'
                )

            if allowed_redirect_to:
                return self._do_redirect(
                    response,
                    allowed_redirect_to.map(
                        lambda u: util.join_url_params(u, response_dict)
                    ),
                )
            else:
                response.status = http.HTTPStatus.OK
                response.content_type = b"application/json"
                response.body = json.dumps(response_dict).encode()

        except Exception as ex:
            redirect_on_failure = data.get(
                "redirect_on_failure", data.get("redirect_to")
            )
            if redirect_on_failure is not None:
                error_message = str(ex)
                logger.error(
                    f"Error resetting password: error={error_message}, "
                    f"reset_token={reset_token}, email={email}"
                )
                error_params = {
                    "error": error_message,
                }
                if reset_token:
                    error_params["reset_token"] = reset_token
                if email:
                    error_params["email"] = email
                redirect_url = util.join_url_params(
                    redirect_on_failure,
                    error_params,
                )
                return self._try_redirect(response, redirect_url)
            else:
                raise ex

    async def handle_magic_link_register(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        _check_keyset(data, {"redirect_on_failure"})
        allowed_redirect_on_failure = self._make_allowed_url(
            data["redirect_on_failure"]
        )

        try:
            _check_keyset(
                data,
                {
                    "provider",
                    "email",
                },
            )

            email = data["email"]
            allowed_redirect_to = self._maybe_make_allowed_url(
                data.get("redirect_to")
            )

            magic_link_client = magic_link.Client(
                db=self.db,
                issuer=self.base_path,
                tenant=self.tenant,
                test_mode=self.test_mode,
                signing_key=self.signing_key,
            )

            request_accepts_json: bool = request.accept == b"application/json"

            if not request_accepts_json and not allowed_redirect_to:
                raise errors.InvalidData(
                    "Request must accept JSON or provide a redirect URL."
                )
            email_factor = await magic_link_client.register(
                email=email,
            )
            await self._maybe_send_webhook(
                webhook.IdentityCreated(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    identity_id=email_factor.identity.id,
                )
            )
            await self._maybe_send_webhook(
                webhook.EmailFactorCreated(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    identity_id=email_factor.identity.id,
                    email_factor_id=email_factor.id,
                )
            )
            if magic_link_client.provider.verification_method == "Code":
                code, otc_id = await otc.create(
                    self.db,
                    str(email_factor.id),
                    datetime.timedelta(minutes=10),
                )
                await auth_emails.send_one_time_code_email(
                    db=self.db,
                    tenant=self.tenant,
                    to_addr=email,
                    code=code,
                    test_mode=self.test_mode,
                )

                await self._handle_otc_initiated(
                    identity_id=str(email_factor.identity.id),
                    email_factor_id=str(email_factor.id),
                    otc_id=str(otc_id),
                    one_time_code=code,
                )

                logger.info(
                    "Sent OTC email: "
                    f"identity_id={email_factor.identity.id}, "
                    f"email={email}, otc_id={otc_id}"
                )

                return_data = {
                    "code": "true",
                    "signup": "true",
                    "email": email,
                }

            else:
                _check_keyset(data, {"challenge", "callback_url"})
                challenge = data["challenge"]
                callback_url = data["callback_url"]
                if not self._is_url_allowed(callback_url):
                    raise errors.InvalidData(
                        "Callback URL does not match any allowed URLs.",
                    )

                allowed_link_url = self._maybe_make_allowed_url(
                    data.get("link_url")
                )
                link_url = (
                    allowed_link_url.url
                    if allowed_link_url
                    else f"{self.base_path}/magic-link/authenticate"
                )

                magic_link_token = magic_link_client.make_magic_link_token(
                    identity_id=email_factor.identity.id,
                    callback_url=callback_url,
                    challenge=challenge,
                )
                await self._maybe_send_webhook(
                    webhook.MagicLinkRequested(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.datetime.now(datetime.timezone.utc),
                        identity_id=email_factor.identity.id,
                        email_factor_id=email_factor.id,
                        magic_link_token=magic_link_token,
                        magic_link_url=link_url,
                    )
                )
                logger.info(
                    "Sending magic link: "
                    f"identity_id={email_factor.identity.id}, email={email}"
                )

                await magic_link_client.send_magic_link(
                    email=email,
                    link_url=link_url,
                    redirect_on_failure=allowed_redirect_on_failure.url,
                    token=magic_link_token,
                )

                return_data = {
                    "email_sent": email,
                }

            if request_accepts_json:
                response.status = http.HTTPStatus.OK
                response.content_type = b"application/json"
                response.body = json.dumps(return_data).encode()
            elif allowed_redirect_to:
                return self._do_redirect(
                    response,
                    allowed_redirect_to.map(
                        lambda u: util.join_url_params(u, return_data)
                    ),
                )
            else:
                # This should not happen since we check earlier for this case
                # but this seems safer than a cast
                raise errors.InvalidData(
                    "Request must accept JSON or provide a redirect URL."
                )
        except Exception as ex:
            if request_accepts_json:
                raise ex

            error_message = str(ex)
            logger.error(
                f"Error sending magic link: error={error_message}, "
                f"email={email}"
            )
            redirect_url = allowed_redirect_on_failure.map(
                lambda u: util.join_url_params(
                    u,
                    {
                        "error": error_message,
                        "email": email,
                    },
                )
            )
            return self._do_redirect(response, redirect_url)

    async def handle_magic_link_email(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        try:
            _check_keyset(
                data,
                {
                    "provider",
                    "email",
                    "challenge",
                    "redirect_on_failure",
                },
            )

            email = data["email"]
            challenge = data["challenge"]
            redirect_on_failure = data["redirect_on_failure"]
            if not self._is_url_allowed(redirect_on_failure):
                raise errors.InvalidData(
                    "Error redirect URL does not match any allowed URLs.",
                )

            allowed_redirect_to = self._maybe_make_allowed_url(
                data.get("redirect_to")
            )

            allowed_link_url = self._maybe_make_allowed_url(
                data.get("link_url")
            )
            link_url = (
                allowed_link_url.url
                if allowed_link_url
                else f"{self.base_path}/magic-link/authenticate"
            )

            magic_link_client = magic_link.Client(
                db=self.db,
                issuer=self.base_path,
                tenant=self.tenant,
                test_mode=self.test_mode,
                signing_key=self.signing_key,
            )
            email_factor = await magic_link_client.get_email_factor_by_email(
                email
            )
            if email_factor is None:
                logger.error(
                    f"Cannot send magic link email: no email factor found for "
                    f"email={email}"
                )
                await auth_emails.send_fake_email(self.tenant)
            else:
                identity_id = email_factor.identity.id
                if magic_link_client.provider.verification_method == "Code":
                    code, otc_id = await otc.create(
                        self.db,
                        str(email_factor.id),
                        datetime.timedelta(minutes=10),
                    )
                    await auth_emails.send_one_time_code_email(
                        db=self.db,
                        tenant=self.tenant,
                        to_addr=email,
                        code=code,
                        test_mode=self.test_mode,
                    )

                    await self._handle_otc_initiated(
                        identity_id=str(identity_id),
                        email_factor_id=str(email_factor.id),
                        otc_id=str(otc_id),
                        one_time_code=code,
                    )

                    logger.info(
                        f"Sent OTC email: identity_id={identity_id}, "
                        f"email={email}, otc_id={otc_id}"
                    )

                    return_data = {
                        "code": "true",
                        "email": email,
                    }
                else:
                    _check_keyset(data, {"callback_url"})
                    callback_url = data["callback_url"]
                    if not self._is_url_allowed(callback_url):
                        raise errors.InvalidData(
                            "Callback URL does not match any allowed URLs.",
                        )
                    magic_link_token = magic_link_client.make_magic_link_token(
                        identity_id=identity_id,
                        callback_url=callback_url,
                        challenge=challenge,
                    )
                    await self._maybe_send_webhook(
                        webhook.MagicLinkRequested(
                            event_id=str(uuid.uuid4()),
                            timestamp=datetime.datetime.now(
                                datetime.timezone.utc
                            ),
                            identity_id=identity_id,
                            email_factor_id=email_factor.id,
                            magic_link_token=magic_link_token,
                            magic_link_url=link_url,
                        )
                    )
                    await magic_link_client.send_magic_link(
                        email=email,
                        token=magic_link_token,
                        link_url=link_url,
                        redirect_on_failure=redirect_on_failure,
                    )
                    logger.info(
                        "Sent magic link email: "
                        f"identity_id={identity_id}, email={email}"
                    )

                    return_data = {
                        "email_sent": email,
                    }

            if allowed_redirect_to:
                return self._do_redirect(
                    response,
                    allowed_redirect_to.map(
                        lambda u: util.join_url_params(u, return_data)
                    ),
                )
            else:
                response.status = http.HTTPStatus.OK
                response.content_type = b"application/json"
                response.body = json.dumps(return_data).encode()
        except Exception as ex:
            request_accepts_json: bool = request.accept == b"application/json"
            if request_accepts_json:
                raise ex

            redirect_on_failure = data.get(
                "redirect_on_failure", data.get("redirect_to")
            )
            if redirect_on_failure is None:
                raise ex
            else:
                error_message = str(ex)
                logger.error(
                    f"Error sending magic link email: error={error_message}, "
                    f"email={email}"
                )
                error_redirect_url = util.join_url_params(
                    redirect_on_failure,
                    {
                        "error": error_message,
                        "email": email,
                    },
                )
                self._try_redirect(response, error_redirect_url)

    async def handle_magic_link_authenticate(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )

        token_str = _maybe_get_search_param(query, "token")

        if token_str:
            try:
                token = jwt.MagicLinkToken.verify(token_str, self.signing_key)
                await pkce.create(self.db, token.challenge)
                code = await pkce.link_identity_challenge(
                    self.db, token.subject, token.challenge
                )
                local_client = magic_link.Client(
                    db=self.db,
                    tenant=self.tenant,
                    test_mode=self.test_mode,
                    issuer=self.base_path,
                    signing_key=self.signing_key,
                )
                await local_client.verify_email(
                    token.subject, datetime.datetime.now(datetime.timezone.utc)
                )

                return self._try_redirect(
                    response,
                    util.join_url_params(token.callback_url, {"code": code}),
                )

            except Exception as ex:
                redirect_on_failure = _maybe_get_search_param(
                    query, "redirect_on_failure"
                )
                if redirect_on_failure is None:
                    raise ex
                else:
                    error_message = str(ex)
                    logger.error(
                        "Error authenticating magic link: "
                        f"error={error_message}, token={token_str}"
                    )
                    redirect_url = util.join_url_params(
                        redirect_on_failure,
                        {
                            "error": error_message,
                        },
                    )
                    return self._try_redirect(response, redirect_url)
        else:
            try:
                data = self._get_data_from_request(request)

                _check_keyset(
                    data, {"email", "code", "callback_url", "challenge"}
                )

                email = data["email"]
                code_str = data["code"]
                callback_url = data["callback_url"]
                challenge = data["challenge"]

                if not self._is_url_allowed(callback_url):
                    raise errors.InvalidData(
                        "Callback URL does not match any allowed URLs.",
                    )

                magic_link_client = magic_link.Client(
                    db=self.db,
                    tenant=self.tenant,
                    test_mode=self.test_mode,
                    issuer=self.base_path,
                    signing_key=self.signing_key,
                )

                email_factor = (
                    await magic_link_client.get_email_factor_by_email(email)
                )
                if email_factor is None:
                    raise errors.NoIdentityFound("Invalid email")

                try:
                    otc_id = await otc.verify(
                        self.db, str(email_factor.id), code_str
                    )

                    await self._handle_otc_verified(
                        identity_id=str(email_factor.identity.id),
                        email_factor_id=str(email_factor.id),
                        otc_id=str(otc_id),
                    )
                except Exception as ex:
                    self._handle_otc_failed(ex)
                    raise

                await pkce.create(self.db, challenge)
                auth_code = await pkce.link_identity_challenge(
                    self.db, email_factor.identity.id, challenge
                )

                await magic_link_client.verify_email(
                    email_factor.identity.id,
                    datetime.datetime.now(datetime.timezone.utc),
                )

                return self._try_redirect(
                    response,
                    util.join_url_params(callback_url, {"code": auth_code}),
                )

            except Exception as ex:
                redirect_on_failure = _maybe_get_search_param(
                    query, "redirect_on_failure"
                )
                if redirect_on_failure is None:
                    response.status = http.HTTPStatus.BAD_REQUEST
                    response.content_type = b"application/json"
                    response.body = json.dumps(
                        {"error": str(ex), "error_code": "verification_failed"}
                    ).encode()
                    return
                else:
                    error_message = str(ex)
                    logger.error(
                        f"Error authenticating OTC: error={error_message}, "
                        f"email={_maybe_get_search_param(query, 'email')}"
                    )
                    redirect_url = util.join_url_params(
                        redirect_on_failure,
                        {
                            "error": error_message,
                        },
                    )
                    return self._try_redirect(response, redirect_url)

    async def handle_webauthn_register_options(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )
        email = _get_search_param(query, "email")
        webauthn_client = webauthn.Client(self.db)

        try:
            (
                user_handle,
                registration_options,
            ) = await webauthn_client.create_registration_options_for_email(
                email=email,
            )
        except Exception as e:
            raise errors.WebAuthnRegistrationFailed(
                "Failed to create registration options"
            ) from e

        response.status = http.HTTPStatus.OK
        response.content_type = b"application/json"
        _set_cookie(
            response,
            "edgedb-webauthn-registration-user-handle",
            user_handle,
            path="/",
        )
        response.body = registration_options

    async def handle_webauthn_register(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        _check_keyset(
            data,
            {"provider", "challenge", "email", "credentials", "verify_url"},
        )
        webauthn_client = webauthn.Client(self.db)

        provider_name: str = data["provider"]
        email: str = data["email"]
        verify_url: str = data["verify_url"]
        credentials: str = data["credentials"]
        pkce_challenge: str = data["challenge"]

        user_handle_cookie = request.cookies.get(
            "edgedb-webauthn-registration-user-handle"
        )
        user_handle_base64url: Optional[str] = (
            user_handle_cookie.value
            if user_handle_cookie
            else data.get("user_handle")
        )
        if user_handle_base64url is None:
            raise errors.InvalidData(
                "Missing user_handle from cookie or request body"
            )
        try:
            user_handle = base64.urlsafe_b64decode(
                f"{user_handle_base64url}==="
            )
        except Exception as e:
            raise errors.InvalidData("Failed to decode user_handle") from e

        require_verification = webauthn_client.provider.require_verification
        pkce_code: Optional[str] = None

        try:
            email_factor = await webauthn_client.register(
                credentials=credentials,
                email=email,
                user_handle=user_handle,
            )
        except Exception as e:
            raise errors.WebAuthnRegistrationFailed(
                "Failed to register WebAuthn"
            ) from e

        identity_id = email_factor.identity.id

        await self._maybe_send_webhook(
            webhook.IdentityCreated(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                identity_id=identity_id,
            )
        )
        await self._maybe_send_webhook(
            webhook.EmailFactorCreated(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                identity_id=identity_id,
                email_factor_id=email_factor.id,
            )
        )

        verification_token = self._make_verification_token(
            identity_id=identity_id,
            verify_url=verify_url,
            maybe_challenge=pkce_challenge,
            maybe_redirect_to=None,
        )

        await self._maybe_send_webhook(
            webhook.EmailVerificationRequested(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                identity_id=identity_id,
                email_factor_id=email_factor.id,
                verification_token=verification_token,
            )
        )
        await self._send_verification_email(
            provider=provider_name,
            verification_token=verification_token,
            to_addr=email_factor.email,
            verify_url=verify_url,
        )

        if not require_verification:
            await pkce.create(self.db, pkce_challenge)
            pkce_code = await pkce.link_identity_challenge(
                self.db, identity_id, pkce_challenge
            )

        _set_cookie(
            response,
            "edgedb-webauthn-registration-user-handle",
            "",
            path="/",
        )
        response.status = http.HTTPStatus.CREATED
        response.content_type = b"application/json"
        if require_verification:
            now_iso8601 = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            response.body = json.dumps(
                {
                    "identity_id": identity_id,
                    "email": email_factor.email,
                    "verification_email_sent_at": now_iso8601,
                }
            ).encode()
            logger.info(
                f"Sent verification email: identity_id={identity_id}, "
                f"email={email}"
            )
        else:
            if pkce_code is None:
                raise errors.PKCECreationFailed
            response.body = json.dumps(
                {
                    "code": pkce_code,
                    "provider": provider_name,
                    "email": email_factor.email,
                }
            ).encode()
            logger.info(
                f"WebAuthn registration successful: identity_id={identity_id}, "
                f"email={email}, "
                f"pkce_id={pkce_code}"
            )

    async def handle_webauthn_authenticate_options(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )
        email = _get_search_param(query, "email")
        webauthn_provider = self._get_webauthn_provider()
        if webauthn_provider is None:
            raise errors.MissingConfiguration(
                "ext::auth::AuthConfig::providers",
                "WebAuthn provider is not configured",
            )
        webauthn_client = webauthn.Client(self.db)

        try:
            (
                _,
                registration_options,
            ) = await webauthn_client.create_authentication_options_for_email(
                email=email, webauthn_provider=webauthn_provider
            )
        except Exception as e:
            raise errors.WebAuthnAuthenticationFailed(
                "Failed to create authentication options"
            ) from e

        response.status = http.HTTPStatus.OK
        response.content_type = b"application/json"
        response.body = registration_options

    async def handle_webauthn_authenticate(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        data = self._get_data_from_request(request)

        _check_keyset(
            data,
            {"challenge", "email", "assertion"},
        )
        webauthn_client = webauthn.Client(self.db)

        email: str = data["email"]
        assertion: str = data["assertion"]
        pkce_challenge: str = data["challenge"]

        try:
            identity = await webauthn_client.authenticate(
                assertion=assertion,
                email=email,
            )
        except Exception as e:
            raise errors.WebAuthnAuthenticationFailed(
                "Failed to authenticate WebAuthn"
            ) from e

        require_verification = webauthn_client.provider.require_verification
        if require_verification:
            email_is_verified = await webauthn_client.is_email_verified(
                email, assertion
            )
            if not email_is_verified:
                raise errors.VerificationRequired()

        await pkce.create(self.db, pkce_challenge)
        code = await pkce.link_identity_challenge(
            self.db, identity.id, pkce_challenge
        )

        logger.info(
            f"WebAuthn authentication successful: identity_id={identity.id}, "
            f"email={email}, "
            f"pkce_id={code}"
        )

        response.status = http.HTTPStatus.OK
        response.content_type = b"application/json"
        response.body = json.dumps(
            {
                "code": code,
            }
        ).encode()

    async def handle_ui_signin(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        ui_config = self._get_ui_config()

        if ui_config is None:
            response.status = http.HTTPStatus.NOT_FOUND
            response.body = b'Auth UI not enabled'
        else:
            providers = util.maybe_get_config(
                self.db,
                "ext::auth::AuthConfig::providers",
                frozenset,
            )
            if providers is None or len(providers) == 0:
                raise errors.MissingConfiguration(
                    'ext::auth::AuthConfig::providers',
                    'No providers are configured',
                )

            app_details_config = self._get_app_details_config()
            query = urllib.parse.parse_qs(
                request.url.query.decode("ascii") if request.url.query else ""
            )

            maybe_challenge = _get_pkce_challenge(
                response=response,
                cookies=request.cookies,
                query_dict=query,
            )
            if maybe_challenge is None:
                raise errors.InvalidData(
                    'Missing "challenge" in register request'
                )

            response.status = http.HTTPStatus.OK
            response.content_type = b'text/html'
            response.body = ui.render_signin_page(
                base_path=self.base_path,
                providers=providers,
                redirect_to=ui_config.redirect_to,
                redirect_to_on_signup=ui_config.redirect_to_on_signup,
                error_message=_maybe_get_search_param(query, 'error'),
                email=_maybe_get_search_param(query, 'email'),
                challenge=maybe_challenge,
                selected_tab=_maybe_get_search_param(query, 'selected_tab'),
                app_name=app_details_config.app_name,
                logo_url=app_details_config.logo_url,
                dark_logo_url=app_details_config.dark_logo_url,
                brand_color=app_details_config.brand_color,
            )

    async def handle_ui_signup(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        ui_config = self._get_ui_config()
        if ui_config is None:
            response.status = http.HTTPStatus.NOT_FOUND
            response.body = b'Auth UI not enabled'
        else:
            providers = util.maybe_get_config(
                self.db,
                "ext::auth::AuthConfig::providers",
                frozenset,
            )
            if providers is None or len(providers) == 0:
                raise errors.MissingConfiguration(
                    'ext::auth::AuthConfig::providers',
                    'No providers are configured',
                )

            query = urllib.parse.parse_qs(
                request.url.query.decode("ascii") if request.url.query else ""
            )

            maybe_challenge = _get_pkce_challenge(
                response=response,
                cookies=request.cookies,
                query_dict=query,
            )
            if maybe_challenge is None:
                raise errors.InvalidData(
                    'Missing "challenge" in register request'
                )
            app_details_config = self._get_app_details_config()

            response.status = http.HTTPStatus.OK
            response.content_type = b'text/html'
            response.body = ui.render_signup_page(
                base_path=self.base_path,
                providers=providers,
                redirect_to=ui_config.redirect_to,
                redirect_to_on_signup=ui_config.redirect_to_on_signup,
                error_message=_maybe_get_search_param(query, 'error'),
                email=_maybe_get_search_param(query, 'email'),
                challenge=maybe_challenge,
                selected_tab=_maybe_get_search_param(query, 'selected_tab'),
                app_name=app_details_config.app_name,
                logo_url=app_details_config.logo_url,
                dark_logo_url=app_details_config.dark_logo_url,
                brand_color=app_details_config.brand_color,
            )

    async def handle_ui_forgot_password(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        ui_config = self._get_ui_config()
        password_provider = (
            self._get_password_provider() if ui_config is not None else None
        )

        if ui_config is None or password_provider is None:
            response.status = http.HTTPStatus.NOT_FOUND
            response.body = (
                b'Password provider not configured'
                if ui_config
                else b'Auth UI not enabled'
            )
            return

        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )
        challenge = _get_search_param(
            query, "challenge", fallback_keys=["code_challenge"]
        )
        app_details_config = self._get_app_details_config()

        redirect_on_failure = (
            f"{self.base_path}/ui/forgot-password?challenge={challenge}"
        )
        reset_url = f"{self.base_path}/ui/reset-password"
        if password_provider.verification_method == "Code":
            redirect_to = (
                f"{self.base_path}/ui/reset-password?"
                f"code=true&challenge={challenge}"
            )
        else:
            redirect_to = (
                f"{self.base_path}/ui/forgot-password?challenge={challenge}"
            )

        response.status = http.HTTPStatus.OK
        response.content_type = b'text/html'
        response.body = ui.render_forgot_password_page(
            redirect_to=redirect_to,
            redirect_on_failure=redirect_on_failure,
            reset_url=reset_url,
            provider_name=password_provider.name,
            error_message=_maybe_get_search_param(query, 'error'),
            email=_maybe_get_search_param(query, 'email'),
            email_sent=_maybe_get_search_param(query, 'email_sent'),
            challenge=challenge,
            app_name=app_details_config.app_name,
            logo_url=app_details_config.logo_url,
            dark_logo_url=app_details_config.dark_logo_url,
            brand_color=app_details_config.brand_color,
        )

    async def handle_ui_reset_password(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        ui_config = self._get_ui_config()
        password_provider = (
            self._get_password_provider() if ui_config is not None else None
        )

        if ui_config is None or password_provider is None:
            raise errors.NotFound(
                'Password provider not configured'
                if ui_config
                else 'Auth UI not enabled'
            )

        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )

        challenge = _get_pkce_challenge(
            response=response,
            cookies=request.cookies,
            query_dict=query,
        )

        if challenge is None:
            raise errors.InvalidData(
                'Missing "challenge" in reset password request'
            )

        error_message = _maybe_get_search_param(query, "error")

        if password_provider.verification_method == "Code":
            maybe_email = _maybe_get_search_param(
                query, "email", fallback_keys=["email_sent"]
            )
            if maybe_email is None:
                raise errors.InvalidData('Missing "email" for reset code flow')
            app_details_config = self._get_app_details_config()
            response.status = http.HTTPStatus.OK
            response.content_type = b'text/html'
            response.body = ui.render_reset_password_page(
                base_path=self.base_path,
                provider_name=password_provider.name,
                is_valid=True,  # Code flow is always valid to show the form
                redirect_to=ui_config.redirect_to,
                challenge=challenge,
                reset_token=None,
                error_message=error_message,
                is_code_flow=True,
                email=maybe_email,
                app_name=app_details_config.app_name,
                logo_url=app_details_config.logo_url,
                dark_logo_url=app_details_config.dark_logo_url,
                brand_color=app_details_config.brand_color,
            )
            return

        try:
            reset_token = _get_search_param(query, 'reset_token')
            token = jwt.ResetToken.verify(reset_token, self.signing_key)

            email_password_client = email_password.Client(
                db=self.db,
            )

            is_valid = (
                await email_password_client.validate_reset_secret(
                    token.subject, token.secret
                )
                is not None
            )
        except Exception:
            is_valid = False

        app_details_config = self._get_app_details_config()
        response.status = http.HTTPStatus.OK
        response.content_type = b'text/html'
        response.body = ui.render_reset_password_page(
            base_path=self.base_path,
            provider_name=password_provider.name,
            is_valid=is_valid,
            redirect_to=ui_config.redirect_to,
            reset_token=reset_token,
            challenge=challenge,
            error_message=error_message,
            is_code_flow=False,
            email=None,
            app_name=app_details_config.app_name,
            logo_url=app_details_config.logo_url,
            dark_logo_url=app_details_config.dark_logo_url,
            brand_color=app_details_config.brand_color,
        )

    async def handle_ui_verify(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        error_messages: list[str] = []
        is_valid = True
        is_code_method: bool = False

        ui_config = self._get_ui_config()
        if ui_config is None:
            response.status = http.HTTPStatus.NOT_FOUND
            response.body = b'Auth UI not enabled'
            return

        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )

        maybe_provider_name = _maybe_get_search_param(query, "provider")
        provider: (
            config.WebAuthnProvider | config.EmailPasswordProviderConfig | None
        ) = None

        # Decide flow by provider config
        match maybe_provider_name:
            case "builtin::local_emailpassword":
                provider = self._get_password_provider()
                if provider is None:
                    raise errors.MissingConfiguration(
                        "ext::auth::AuthConfig::providers",
                        "EmailPassword provider is not configured",
                    )
                is_code_method = provider.verification_method == "Code"
            case "builtin::local_webauthn":
                provider = self._get_webauthn_provider()
                if provider is None:
                    raise errors.MissingConfiguration(
                        "ext::auth::AuthConfig::providers",
                        "WebAuthn provider is not configured",
                    )
                is_code_method = provider.verification_method == "Code"
            case _:
                raise errors.InvalidData(
                    f"Unknown provider: {maybe_provider_name}"
                )

        if is_code_method:
            email = _get_search_param(query, "email")
            error_message = _maybe_get_search_param(query, "error")
            challenge = _get_pkce_challenge(
                cookies=request.cookies,
                response=response,
                query_dict=query,
            )
            if challenge is None:
                raise errors.InvalidData(
                    'Missing "challenge" in email verification request'
                )

            app_details_config = self._get_app_details_config()
            response.status = http.HTTPStatus.OK
            response.content_type = b'text/html'
            response.body = ui.render_email_verification_page_code_flow(
                challenge=challenge,
                email=email,
                provider=maybe_provider_name,
                base_path=self.base_path,
                callback_url=(
                    ui_config.redirect_to_on_signup or ui_config.redirect_to
                ),
                error_message=error_message,
                app_name=app_details_config.app_name,
                logo_url=app_details_config.logo_url,
                dark_logo_url=app_details_config.dark_logo_url,
                brand_color=app_details_config.brand_color,
            )
            return

        maybe_pkce_code: str | None = None
        redirect_to = ui_config.redirect_to_on_signup or ui_config.redirect_to

        maybe_verification_token = _maybe_get_search_param(
            query, "verification_token"
        )

        match (maybe_provider_name, maybe_verification_token):
            case (None, None):
                error_messages.append(
                    "Missing provider and email verification token."
                )
                is_valid = False
            case (None, _):
                error_messages.append("Missing provider.")
                is_valid = False
            case (_, None):
                error_messages.append("Missing email verification token.")
                is_valid = False
            case (str(provider_name), str(verification_token)):
                try:
                    token = jwt.VerificationToken.verify(
                        verification_token,
                        self.signing_key,
                    )
                    await self._try_verify_email(
                        provider=provider_name,
                        identity_id=token.subject,
                    )

                    match token.maybe_challenge:
                        case str(ch):
                            await pkce.create(self.db, ch)
                            maybe_pkce_code = (
                                await pkce.link_identity_challenge(
                                    self.db,
                                    token.subject,
                                    ch,
                                )
                            )
                        case _:
                            maybe_pkce_code = None

                    redirect_to = token.maybe_redirect_to or redirect_to
                    redirect_to = (
                        util.join_url_params(
                            redirect_to,
                            {
                                "code": maybe_pkce_code,
                            },
                        )
                        if maybe_pkce_code
                        else redirect_to
                    )

                except errors.VerificationTokenExpired:
                    app_details_config = self._get_app_details_config()
                    response.status = http.HTTPStatus.OK
                    response.content_type = b"text/html"
                    response.body = ui.render_email_verification_expired_page(
                        verification_token=verification_token,
                        app_name=app_details_config.app_name,
                        logo_url=app_details_config.logo_url,
                        dark_logo_url=app_details_config.dark_logo_url,
                        brand_color=app_details_config.brand_color,
                    )
                    return

                except Exception as ex:
                    error_messages.append(repr(ex))
                    is_valid = False

        # Only redirect back if verification succeeds
        if is_valid:
            return self._try_redirect(response, redirect_to)

        app_details_config = self._get_app_details_config()
        response.status = http.HTTPStatus.OK
        response.content_type = b'text/html'
        response.body = ui.render_email_verification_page_link_flow(
            verification_token=maybe_verification_token,
            is_valid=is_valid,
            error_messages=error_messages,
            app_name=app_details_config.app_name,
            logo_url=app_details_config.logo_url,
            dark_logo_url=app_details_config.dark_logo_url,
            brand_color=app_details_config.brand_color,
        )

    async def handle_ui_resend_verification(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )
        ui_config = self._get_ui_config()
        password_provider = (
            self._get_password_provider() if ui_config is not None else None
        )
        is_valid = True

        if password_provider is None:
            response.status = http.HTTPStatus.NOT_FOUND
            response.body = b'Password provider not configured'
            return
        try:
            _check_keyset(query, {"verification_token"})
            verification_token = query["verification_token"][0]
            token = jwt.VerificationToken.verify(
                verification_token,
                self.signing_key,
                skip_expiration_check=True,
            )
            email_password_client = email_password.Client(self.db)
            email_factor = (
                await email_password_client.get_email_factor_by_identity_id(
                    token.subject
                )
            )
            if email_factor is None:
                raise errors.NoIdentityFound(
                    "Could not find email for provided identity"
                )

            verify_url = f"{self.base_path}/ui/verify"
            verification_token = self._make_verification_token(
                identity_id=token.subject,
                verify_url=verify_url,
                maybe_challenge=token.maybe_challenge,
                maybe_redirect_to=token.maybe_redirect_to,
            )

            await self._send_verification_email(
                provider=password_provider.name,
                verification_token=verification_token,
                to_addr=email_factor.email,
                verify_url=verify_url,
            )
        except Exception:
            is_valid = False

        app_details_config = self._get_app_details_config()
        response.status = http.HTTPStatus.OK
        response.content_type = b"text/html"
        response.body = ui.render_resend_verification_done_page(
            is_valid=is_valid,
            verification_token=_maybe_get_search_param(
                query, "verification_token"
            ),
            app_name=app_details_config.app_name,
            logo_url=app_details_config.logo_url,
            dark_logo_url=app_details_config.dark_logo_url,
            brand_color=app_details_config.brand_color,
        )

    async def handle_ui_magic_link_sent(
        self,
        request: protocol.HttpRequest,
        response: protocol.HttpResponse,
    ) -> None:
        ui_config = self._get_ui_config()
        if ui_config is None:
            response.status = http.HTTPStatus.NOT_FOUND
            response.body = b'Auth UI not enabled'
            return
        app_details = self._get_app_details_config()

        query = urllib.parse.parse_qs(
            request.url.query.decode("ascii") if request.url.query else ""
        )

        # Use magic link provider to decide display mode
        magic_link_provider = None
        providers = util.maybe_get_config(
            self.db,
            "ext::auth::AuthConfig::providers",
            frozenset,
        )
        if providers is not None:
            for p in providers:
                if getattr(p, 'name', None) == 'builtin::local_magic_link':
                    magic_link_provider = p
                    break

        is_code_method = (
            getattr(magic_link_provider, 'verification_method', 'Link')
            == 'Code'
        )

        if is_code_method:
            is_signup = _maybe_get_search_param(query, "signup") == "true"
            email = _get_search_param(query, "email")
            challenge = _get_pkce_challenge(
                cookies=request.cookies, response=response, query_dict=query
            )
            if challenge is None:
                response.status = http.HTTPStatus.BAD_REQUEST
                response.body = b'Missing challenge from cookie or query params'
                return

            error_message = _maybe_get_search_param(query, "error")
            callback_url = ui_config.redirect_to
            if is_signup and ui_config.redirect_to_on_signup:
                callback_url = ui_config.redirect_to_on_signup

            content = ui.render_magic_link_sent_page_code_flow(
                app_name=app_details.app_name,
                logo_url=app_details.logo_url,
                dark_logo_url=app_details.dark_logo_url,
                brand_color=app_details.brand_color,
                email=email,
                challenge=challenge,
                callback_url=callback_url,
                error_message=error_message,
            )
        else:
            content = ui.render_magic_link_sent_page_link_flow(
                app_name=app_details.app_name,
                logo_url=app_details.logo_url,
                dark_logo_url=app_details.dark_logo_url,
                brand_color=app_details.brand_color,
            )

        response.status = http.HTTPStatus.OK
        response.content_type = b"text/html"
        response.body = content

    def _get_webhook_config(self) -> list[config.WebhookConfig]:
        raw_webhook_configs = util.get_config(
            self.db,
            "ext::auth::AuthConfig::webhooks",
            frozenset,
        )
        return [
            config.WebhookConfig(
                events=raw_config.events,
                url=raw_config.url,
                signing_secret_key=raw_config.signing_secret_key,
            )
            for raw_config in raw_webhook_configs
        ]

    async def _maybe_send_webhook(self, event: webhook.Event) -> None:
        webhook_configs = self._get_webhook_config()
        for webhook_config in webhook_configs:
            if event.event_type in webhook_config.events:
                request_id = await webhook.send(
                    db=self.db,
                    url=webhook_config.url,
                    secret=webhook_config.signing_secret_key,
                    event=event,
                )
                logger.info(
                    f"Sent webhook request {request_id} "
                    f"to {webhook_config.url} for event {event!r}"
                )

    async def _handle_otc_initiated(
        self,
        identity_id: str,
        email_factor_id: str,
        otc_id: str,
        one_time_code: str,
    ) -> None:
        metrics.otc_initiated_total.inc(1.0, self.tenant.get_instance_name())

        await self._maybe_send_webhook(
            webhook.OneTimeCodeRequested(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                identity_id=identity_id,
                email_factor_id=email_factor_id,
                otc_id=str(otc_id),
                one_time_code=one_time_code,
            )
        )

        logger.info(
            f"OTC initiated: identity_id={identity_id}, otc_id={otc_id}"
        )

    async def _handle_otc_verified(
        self, identity_id: str, email_factor_id: str, otc_id: str
    ) -> None:
        metrics.otc_verified_total.inc(1.0, self.tenant.get_instance_name())

        await self._maybe_send_webhook(
            webhook.OneTimeCodeVerified(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                identity_id=identity_id,
                email_factor_id=email_factor_id,
                otc_id=str(otc_id),
            )
        )

        logger.info(f"OTC verified: identity_id={identity_id}, otc_id={otc_id}")

    def _handle_otc_failed(self, ex: Exception) -> None:
        match ex:
            case errors.OTCRateLimited():
                failure_reason = "rate_limited"
            case errors.OTCInvalidCode():
                failure_reason = "invalid_code"
            case errors.OTCExpired():
                failure_reason = "expired"
            case errors.OTCVerificationFailed():
                failure_reason = "verification_failed"
            case _:
                failure_reason = "unknown"

        metrics.otc_failed_total.inc(
            1.0, self.tenant.get_instance_name(), failure_reason
        )

        logger.info(f"OTC verification failed: reason={failure_reason}")

    def _get_callback_url(self) -> str:
        return f"{self.base_path}/callback"

    def _get_data_from_request(
        self,
        request: protocol.HttpRequest,
    ) -> dict[Any, Any]:
        content_type = request.content_type
        match content_type:
            case b"application/x-www-form-urlencoded":
                return {
                    k: v[0]
                    for k, v in urllib.parse.parse_qs(
                        request.body.decode('ascii')
                    ).items()
                }
            case b"application/json":
                data = json.loads(request.body)
                if not isinstance(data, dict):
                    raise errors.InvalidData(
                        f"Invalid json data, expected an object"
                    )
                return data
            case _:
                raise errors.InvalidData(
                    f"Unsupported Content-Type: {content_type!r}"
                )

    def _get_ui_config(self) -> config.UIConfig:
        return cast(
            config.UIConfig,
            util.maybe_get_config(
                self.db, "ext::auth::AuthConfig::ui", CompositeConfigType
            ),
        )

    def _get_app_details_config(self) -> config.AppDetailsConfig:
        return util.get_app_details_config(self.db)

    def _get_password_provider(
        self,
    ) -> Optional[config.EmailPasswordProviderConfig]:
        providers = cast(
            list[config.ProviderConfig],
            util.get_config(
                self.db,
                "ext::auth::AuthConfig::providers",
                frozenset,
            ),
        )
        password_providers = [
            cast(config.EmailPasswordProviderConfig, p)
            for p in providers
            if (p.name == 'builtin::local_emailpassword')
        ]

        return password_providers[0] if len(password_providers) == 1 else None

    def _get_webauthn_provider(self) -> config.WebAuthnProvider | None:
        providers = cast(
            list[config.ProviderConfig],
            util.get_config(
                self.db,
                "ext::auth::AuthConfig::providers",
                frozenset,
            ),
        )
        webauthn_providers = cast(
            list[config.WebAuthnProviderConfig],
            [p for p in providers if (p.name == 'builtin::local_webauthn')],
        )

        if len(webauthn_providers) == 1:
            provider = webauthn_providers[0]
            return config.WebAuthnProvider(
                name=provider.name,
                relying_party_origin=provider.relying_party_origin,
                require_verification=provider.require_verification,
                verification_method=provider.verification_method,
            )
        else:
            return None

    def _make_verification_token(
        self,
        identity_id: str,
        verify_url: str,
        maybe_challenge: str | None,
        maybe_redirect_to: str | None,
        *,
        maybe_provider: str | None = None,
    ) -> str:
        if not self._is_url_allowed(verify_url):
            raise errors.InvalidData(
                "Verify URL does not match any allowed URLs.",
            )

        return jwt.VerificationToken(
            subject=identity_id,
            verify_url=verify_url,
            maybe_challenge=maybe_challenge,
            maybe_redirect_to=maybe_redirect_to,
        ).sign(self.signing_key)

    async def _send_verification_email(
        self,
        *,
        verification_token: str,
        verify_url: str,
        provider: str,
        to_addr: str,
    ) -> None:
        client: email_password.Client | webauthn.Client | None = None
        match provider:
            case "builtin::local_emailpassword":
                client = email_password.Client(db=self.db)
            case "builtin::local_webauthn":
                client = webauthn.Client(self.db)
        if client is not None:
            if client.config.verification_method == "Code":
                email_factor = await client.get_email_factor_by_email(to_addr)
                if email_factor is not None:
                    code, otc_id = await otc.create(
                        self.db,
                        str(email_factor.id),
                        datetime.timedelta(minutes=10),
                    )
                    await auth_emails.send_one_time_code_email(
                        db=self.db,
                        tenant=self.tenant,
                        to_addr=to_addr,
                        code=code,
                        test_mode=self.test_mode,
                    )

                    await self._handle_otc_initiated(
                        identity_id=email_factor.identity.id,
                        email_factor_id=str(email_factor.id),
                        otc_id=str(otc_id),
                        one_time_code=code,
                    )

                    logger.info(
                        "Sent OTC verification email: "
                        f"email={to_addr}, otc_id={otc_id}"
                    )
                    return

        await auth_emails.send_verification_email(
            db=self.db,
            tenant=self.tenant,
            to_addr=to_addr,
            verification_token=verification_token,
            provider=provider,
            verify_url=verify_url,
            test_mode=self.test_mode,
        )

    async def _try_verify_email(
        self, provider: str, identity_id: str
    ) -> EmailFactor:
        current_time = datetime.datetime.now(datetime.timezone.utc)

        client: email_password.Client | webauthn.Client
        match provider:
            case "builtin::local_emailpassword":
                client = email_password.Client(db=self.db)
            case "builtin::local_webauthn":
                client = webauthn.Client(self.db)
            case _:
                raise errors.InvalidData(
                    f"Unknown provider: {provider}",
                )

        updated = await client.verify_email(identity_id, current_time)
        if updated is None:
            raise errors.NoIdentityFound(
                "Could not verify email for identity"
                f" {identity_id}. This email address may not exist"
                " in our system, or it might already be verified."
            )
        return updated

    def _is_url_allowed(self, url: str) -> bool:
        allowed_urls = util.get_config(
            self.db,
            "ext::auth::AuthConfig::allowed_redirect_urls",
            frozenset,
        )
        allowed_urls = cast(frozenset[str], allowed_urls).union(
            {self.base_path}
        )

        ui_config = self._get_ui_config()
        if ui_config:
            allowed_urls = allowed_urls.union({ui_config.redirect_to})
            if ui_config.redirect_to_on_signup:
                allowed_urls = allowed_urls.union(
                    {ui_config.redirect_to_on_signup}
                )

        lower_url = url.lower()

        for allowed_url in allowed_urls:
            lower_allowed_url = allowed_url.lower()
            if lower_url.startswith(lower_allowed_url):
                return True

            parsed_allowed_url = urllib.parse.urlparse(lower_allowed_url)
            allowed_domain = parsed_allowed_url.netloc
            allowed_path = parsed_allowed_url.path

            parsed_lower_url = urllib.parse.urlparse(lower_url)
            lower_domain = parsed_lower_url.netloc
            lower_path = parsed_lower_url.path

            if (
                lower_domain == allowed_domain
                or lower_domain.endswith('.' + allowed_domain)
            ) and lower_path.startswith(allowed_path):
                return True

        return False

    def _do_redirect(
        self, response: protocol.HttpResponse, allowed_url: AllowedUrl
    ) -> None:
        response.status = http.HTTPStatus.FOUND
        response.custom_headers["Location"] = allowed_url.url

    def _try_redirect(self, response: protocol.HttpResponse, url: str) -> None:
        allowed_url = self._make_allowed_url(url)
        self._do_redirect(response, allowed_url)

    def _make_allowed_url(self, url: str) -> AllowedUrl:
        if not self._is_url_allowed(url):
            raise errors.InvalidData(
                "Redirect URL does not match any allowed URLs.",
            )
        return AllowedUrl(url)

    def _maybe_make_allowed_url(
        self, url: Optional[str]
    ) -> Optional[AllowedUrl]:
        return self._make_allowed_url(url) if url else None


@dataclasses.dataclass
class AllowedUrl:
    url: str

    def map(self, f: Callable[[str], str]) -> "AllowedUrl":
        return AllowedUrl(f(self.url))


def _fail_with_error(
    *,
    response: protocol.HttpResponse,
    status: http.HTTPStatus,
    ex: Exception,
    exc_info: bool = False,
) -> None:
    err_dct = {
        "message": str(ex),
        "type": str(ex.__class__.__name__),
    }

    logger.error(
        f"Failed to handle HTTP request: {err_dct!r}", exc_info=exc_info
    )
    response.body = json.dumps({"error": err_dct}).encode()
    response.status = status


def _maybe_get_search_param(
    query_dict: dict[str, list[str]],
    key: str,
    *,
    fallback_keys: Optional[list[str]] = None,
) -> str | None:
    params = query_dict.get(key)
    if params is None and fallback_keys is not None:
        for fallback_key in fallback_keys:
            params = query_dict.get(fallback_key)
            if params is not None:
                break
    return params[0] if params else None


def _get_search_param(
    query_dict: dict[str, list[str]],
    key: str,
    *,
    fallback_keys: Optional[list[str]] = None,
) -> str:
    val = _maybe_get_search_param(query_dict, key, fallback_keys=fallback_keys)
    if val is None:
        raise errors.InvalidData(f"Missing query parameter: {key}")
    return val


def _maybe_get_form_field(
    form_dict: dict[str, list[str]], key: str
) -> str | None:
    maybe_val = form_dict.get(key)
    if maybe_val is None:
        return None
    return maybe_val[0]


def _get_pkce_challenge(
    *,
    response: protocol.HttpResponse,
    cookies: http.cookies.SimpleCookie,
    query_dict: dict[str, list[str]],
) -> str | None:
    cookie_name = 'edgedb-pkce-challenge'
    challenge: str | None = _maybe_get_search_param(query_dict, 'challenge')
    if challenge is not None:
        logger.info(
            f"PKCE challenge found in query param 'challenge': {challenge!r}"
        )
    else:
        challenge = _maybe_get_search_param(query_dict, "code_challenge")
        if challenge is not None:
            logger.info(
                "PKCE challenge found in query param 'code_challenge':"
                f" {challenge!r}"
            )
    if challenge is not None:
        _set_cookie(response, cookie_name, challenge)
    else:
        if 'edgedb-pkce-challenge' in cookies:
            challenge = cookies['edgedb-pkce-challenge'].value
            logger.info(f"PKCE challenge found in cookie: {challenge!r}")
        else:
            logger.info("No PKCE challenge found in query params or cookies.")
            logger.info(f"Query params: {query_dict}")
            logger.info(f"Cookies: {cookies}")
    return challenge


def _set_cookie(
    response: protocol.HttpResponse,
    name: str,
    value: str,
    *,
    http_only: bool = True,
    secure: bool = True,
    same_site: str = "Strict",
    path: Optional[str] = None,
) -> None:
    val: http.cookies.Morsel[str] = http.cookies.SimpleCookie({name: value})[
        name
    ]
    val["httponly"] = http_only
    val["secure"] = secure
    val["samesite"] = same_site
    if path is not None:
        val["path"] = path
    response.custom_headers["Set-Cookie"] = val.OutputString()


def _check_keyset(candidate: dict[str, Any], keyset: set[str]) -> None:
    missing_fields = [field for field in keyset if field not in candidate]
    if missing_fields:
        raise errors.InvalidData(
            f"Missing required fields: {', '.join(missing_fields)}"
        )
