#
# This source file is part of the Gel open source project.
#
# Copyright 2025-present MagicStack Inc. and the Gel authors.
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

import hashlib
import json
import logging
import secrets
import uuid
import datetime
from typing import Any

from edb.server.protocol import execute

from . import errors

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_code(code: str) -> bytes:
    return hashlib.sha256(code.encode('utf-8')).digest()


async def create(
    db: Any, factor_id: str, ttl: datetime.timedelta
) -> tuple[str, uuid.UUID]:
    """
    Create a new OneTimeCode object in the database.

    Args:
        db: Database connection
        factor_id: The ID of the factor to associate with this code
        ttl: Time to live for the code

    Returns:
        Tuple of (code, otc_id) where code is the plain text code and otc_id is
        the database ID
    """
    code = generate_code()
    code_hash = hash_code(code)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + ttl

    r = await execute.parse_execute_json(
        db=db,
        query="""\
with
    ONE_TIME_CODE := (insert ext::auth::OneTimeCode {
        factor := <ext::auth::Factor><uuid>$factor_id,
        code_hash := <bytes>$code_hash,
        expires_at := <datetime>$expires_at,
    })
select ONE_TIME_CODE { id };""",
        variables={
            "factor_id": factor_id,
            "code_hash": code_hash,
            "expires_at": expires_at.isoformat(),
        },
        cached_globally=True,
        query_tag='gel/auth',
    )

    result_json = json.loads(r.decode())
    if len(result_json) != 1:
        raise errors.InvalidData("Failed to create OneTimeCode")

    return code, uuid.UUID(result_json[0]["id"])


async def verify(db: Any, factor_id: str, code: str) -> str:
    """
    Verify a one-time code for a given factor.

    This function performs all verification operations in a single atomic query:
    - Cleanup expired codes
    - Check rate limits
    - Find and validate the code
    - Delete the code if valid
    - Record the authentication attempt

    Args:
        db: Database connection
        factor_id: The ID of the factor
        code: The code to verify

    Returns:
        The OneTimeCode ID if verification succeeds

    Raises:
        OTCRateLimited: If maximum verification attempts exceeded
        OTCInvalidCode: If the code is invalid or not found
        OTCExpired: If the code has expired
        OTCVerificationFailed: If verification fails for other reasons
    """
    code_hash = hash_code(code)

    r = await execute.parse_execute_json(
        db=db,
        query="""\
with
    factor_id := <uuid>$factor_id,
    FACTOR := (select ext::auth::Factor filter .id = factor_id),
    code_hash := <bytes>$code_hash,
    MAX_ATTEMPTS := <int16>$max_attempts,
    now := datetime_current(),
    window_start := now - <duration>'10 minutes',

    # Cleanup expired codes (side effect)
    cleanup_count := count(
        delete ext::auth::OneTimeCode filter .expires_at < now
    ),

    # Check rate limits
    failed_attempts := (
        select count(
            select ext::auth::AuthenticationAttempt
            filter .factor = FACTOR
               and .attempt_type =
                   ext::auth::AuthenticationAttemptType.OneTimeCode
               and .successful = false
               and .created_at > window_start
        )
    ),

    # Find the OTC
    otc := (
        select ext::auth::OneTimeCode
        filter .factor = FACTOR and .code_hash = code_hash
        limit 1
    ),

    is_rate_limited := failed_attempts >= MAX_ATTEMPTS,
    is_code_found := exists otc,
    is_code_expired := (otc.expires_at < now) ?? false,
    is_code_valid := (
        is_code_found and not is_code_expired and not is_rate_limited
    ),

    # Delete OTC if valid (side effect)
    deleted_otc := (
        delete ext::auth::OneTimeCode
        filter .id = otc.id and is_code_valid
    ),

    # Record attempt (side effect)
    recorded_attempt := (
        if (exists FACTOR)
        then (
            insert ext::auth::AuthenticationAttempt {
                factor := FACTOR,
                attempt_type :=
                    ext::auth::AuthenticationAttemptType.OneTimeCode,
                successful := is_code_valid,
            }
        )
        else {}
    ),

select {
    failed_attempts := failed_attempts,
    success := is_code_valid,
    rate_limited := is_rate_limited,
    code_found := is_code_found,
    code_expired := is_code_expired,
    otc_id := otc.id,
    cleanup_count := cleanup_count,
};""",
        variables={
            "factor_id": factor_id,
            "code_hash": code_hash,
            "max_attempts": MAX_ATTEMPTS,
        },
        cached_globally=True,
        query_tag='gel/auth',
    )

    result_json = json.loads(r.decode())
    result = result_json[0]

    if result["rate_limited"]:
        raise errors.OTCRateLimited()
    elif not result["code_found"]:
        raise errors.OTCInvalidCode()
    elif result["code_expired"]:
        raise errors.OTCExpired()
    elif not result["success"]:
        raise errors.OTCVerificationFailed()

    return str(result["otc_id"])


async def cleanup_old_attempts(db: Any, retention_hours: int = 24) -> int:
    """
    Remove authentication attempts older than the retention window.

    This is intended for scheduled maintenance jobs to prevent unbounded
    growth of the authentication attempts table.

    Args:
        db: Database connection
        retention_hours: Hours to retain attempts (defaults to 24)

    Returns:
        Number of old attempts that were deleted
    """
    r = await execute.parse_execute_json(
        db=db,
        query="""\
with
    cutoff_time := datetime_current() - <duration>$retention_duration,
    old_attempts := (
        delete ext::auth::AuthenticationAttempt
        filter .created_at < cutoff_time
    )
select count(old_attempts);""",
        variables={
            "retention_duration": f"{retention_hours} hours",
        },
        cached_globally=True,
        query_tag='gel/auth',
    )

    result_json = json.loads(r.decode())
    return result_json[0] if result_json else 0
