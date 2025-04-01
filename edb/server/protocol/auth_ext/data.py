#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2016-present MagicStack Inc. and the EdgeDB authors.
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


import dataclasses
import datetime
import base64

from typing import Any


@dataclasses.dataclass
class UserInfo:
    """
    OpenID Connect compatible user info.
    See: https://openid.net/specs/openid-connect-core-1_0.html
    """

    sub: str
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    middle_name: str | None = None
    nickname: str | None = None
    preferred_username: str | None = None
    profile: str | None = None
    picture: str | None = None
    website: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    gender: str | None = None
    birthdate: str | None = None
    zoneinfo: str | None = None
    locale: str | None = None
    phone_number: str | None = None
    phone_number_verified: bool | None = None
    address: dict[str, str] | None = None
    updated_at: float | None = None
    source_id_token: str | None = None

    def __str__(self) -> str:
        return self.sub

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"sub={self.sub!r} "
            f"name={self.name!r} "
            f"email={self.email!r} "
            f"preferred_username={self.preferred_username!r})"
        )


@dataclasses.dataclass
class Identity:
    id: str
    subject: str
    issuer: str
    created_at: datetime.datetime
    modified_at: datetime.datetime

    def __str__(self) -> str:
        return self.id


@dataclasses.dataclass
class LocalIdentity(Identity):
    pass


@dataclasses.dataclass
class OpenIDConfig:
    """
    OpenID Connect configuration. Only includes fields actually in use.
    See:
    - https://openid.net/specs/openid-connect-discovery-1_0.html
    - https://accounts.google.com/.well-known/openid-configuration
    """

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str

    def __init__(self, **kwargs: Any):
        for field in dataclasses.fields(self):
            setattr(self, field.name, kwargs.get(field.name))

    def __str__(self) -> str:
        return self.issuer


@dataclasses.dataclass(repr=False)
class OAuthAccessTokenResponse:
    """
    Access Token Response.
    https://datatracker.ietf.org/doc/html/rfc6749#section-4.1.4
    """

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None

    def __init__(self, **kwargs: Any):
        for field in dataclasses.fields(self):
            if field.name in kwargs:
                setattr(self, field.name, kwargs.pop(field.name))
            else:
                setattr(self, field.name, None)
        self._extra_fields = kwargs


@dataclasses.dataclass(repr=False)
class OpenIDConnectAccessTokenResponse(OAuthAccessTokenResponse):
    """
    OpenID Connect Access Token Response.
    https://openid.net/specs/openid-connect-core-1_0.html#TokenResponse
    """

    id_token: str

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)


@dataclasses.dataclass
class EmailFactor:
    id: str
    created_at: datetime.datetime
    modified_at: datetime.datetime
    identity: LocalIdentity
    email: str
    verified_at: datetime.datetime | None

    def __init__(
        self,
        *,
        id: str,
        created_at: datetime.datetime,
        modified_at: datetime.datetime,
        identity: LocalIdentity,
        email: str,
        verified_at: datetime.datetime | None,
    ):
        self.id = id
        self.created_at = created_at
        self.modified_at = modified_at
        self.identity = (
            LocalIdentity(**identity)
            if isinstance(identity, dict)
            else identity
        )
        self.email = email
        self.verified_at = verified_at


@dataclasses.dataclass
class WebAuthnFactor(EmailFactor):
    user_handle: bytes
    credential_id: bytes
    public_key: bytes

    def __init__(
        self,
        *,
        id: str,
        created_at: datetime.datetime,
        modified_at: datetime.datetime,
        identity: LocalIdentity,
        email: str,
        verified_at: datetime.datetime | None,
        user_handle: bytes,
        credential_id: bytes,
        public_key: bytes,
    ):
        self.id = id
        self.created_at = created_at
        self.modified_at = modified_at
        self.identity = (
            LocalIdentity(**identity)
            if isinstance(identity, dict)
            else identity
        )
        self.email = email
        self.verified_at = verified_at
        self.user_handle = base64.b64decode(user_handle)
        self.credential_id = base64.b64decode(credential_id)
        self.public_key = base64.b64decode(public_key)


@dataclasses.dataclass
class WebAuthnAuthenticationChallenge:
    id: str
    created_at: datetime.datetime
    modified_at: datetime.datetime
    challenge: bytes
    factors: list[WebAuthnFactor]

    def __init__(
        self,
        *,
        id: str,
        created_at: datetime.datetime,
        modified_at: datetime.datetime,
        challenge: bytes,
        factors: list[WebAuthnFactor],
    ):
        self.id = id
        self.created_at = created_at
        self.modified_at = modified_at
        self.challenge = base64.b64decode(challenge)
        self.factors = [
            WebAuthnFactor(**factor) if isinstance(factor, dict) else factor
            for factor in factors
        ]
