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


from __future__ import annotations
from typing import TYPE_CHECKING, ParamSpec, TypeVar

import asyncio
import functools
import unittest
import logging

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


logger = logging.getLogger("edb.test")
skip = unittest.skip

_P = ParamSpec("_P")
_R = TypeVar("_R", covariant=True)


def _xfail(
    reason: str,
    *,
    unless: bool = False,
    allow_failure: bool,
    allow_error: bool,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    def decorator(test_item: Callable[_P, _R]) -> Callable[_P, _R]:
        if unless:
            return test_item
        else:
            test_item.__et_xfail_reason__ = reason  # type: ignore [attr-defined]
            test_item.__et_xfail_allow_failure__ = allow_failure  # type: ignore [attr-defined]
            test_item.__et_xfail_allow_error__ = allow_error  # type: ignore [attr-defined]
            return unittest.expectedFailure(test_item)

    return decorator


def xfail(
    reason: str,
    *,
    unless: bool = False,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    return _xfail(reason, unless=unless, allow_failure=True, allow_error=False)


def xerror(
    reason: str,
    *,
    unless: bool = False,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    return _xfail(reason, unless=unless, allow_failure=False, allow_error=True)


def not_implemented(
    reason: str,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    def decorator(test_item: Callable[_P, _R]) -> Callable[_P, _R]:
        test_item.__et_xfail_reason__ = reason  # type: ignore [attr-defined]
        test_item.__et_xfail_not_implemented__ = True  # type: ignore [attr-defined]
        test_item.__et_xfail_allow_failure__ = True  # type: ignore [attr-defined]
        test_item.__et_xfail_allow_error__ = True  # type: ignore [attr-defined]
        return unittest.expectedFailure(test_item)

    return decorator


def async_timeout(
    timeout: int,
) -> Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]:
    def decorator(
        test_func: Callable[_P, Awaitable[_R]],
    ) -> Callable[_P, Awaitable[_R]]:
        @functools.wraps(test_func)
        async def wrapper(
            *args: _P.args,
            **kwargs: _P.kwargs,
        ) -> _R:
            try:
                return await asyncio.wait_for(
                    test_func(*args, **kwargs), timeout
                )
            except TimeoutError:
                logger.error(
                    "Test %s failed due to timeout after %s seconds",
                    test_func,
                    timeout,
                )
                raise AssertionError(
                    f"Test failed due to timeout after {timeout} seconds"
                ) from None
            except asyncio.CancelledError as e:
                logger.error(
                    "Test %s failed due to timeout after %s seconds",
                    test_func,
                    timeout,
                    exc_info=e,
                )
                raise AssertionError(
                    f"Test failed due to timeout after {timeout} seconds"
                ) from e

        return wrapper

    return decorator
