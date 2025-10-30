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

import collections.abc
import functools


from typing import Callable, Optional
from types import MethodType


class LRUMapping(collections.abc.MutableMapping):
    # We use an OrderedDict for LRU implementation.  Operations:
    #
    # * We use a simple `__setitem__` to push a new entry:
    #       `entries[key] = new_entry`
    #   That will push `new_entry` to the *end* of the entries dict.
    #
    # * When we have a cache hit, we call
    #       `entries.move_to_end(key, last=True)`
    #   to move the entry to the *end* of the entries dict.
    #
    # * When we need to remove entries to maintain `max_size`, we call
    #       `entries.popitem(last=False)`
    #   to remove an entry from the *beginning* of the entries dict.
    #
    # So new entries and hits are always promoted to the end of the
    # entries dict, whereas the unused one will group in the
    # beginning of it.

    def __init__(self, *, maxsize):
        if maxsize <= 0:
            raise ValueError(
                f'maxsize is expected to be greater than 0, got {maxsize}'
            )

        self._dict = collections.OrderedDict()
        self._maxsize = maxsize

    def __getitem__(self, key):
        o = self._dict[key]
        self._dict.move_to_end(key, last=True)
        return o

    def __setitem__(self, key, o):
        if key in self._dict:
            self._dict[key] = o
            self._dict.move_to_end(key, last=True)
        else:
            self._dict[key] = o
            if len(self._dict) > self._maxsize:
                self._dict.popitem(last=False)

    def __delitem__(self, key):
        del self._dict[key]

    def __contains__(self, key):
        return key in self._dict

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)


class _NoPickle:
    def __init__(self, obj):
        self.obj = obj

    def __bool__(self):
        return bool(self.obj)

    def __getstate__(self):
        return ()

    def __setstate__(self, _d):
        self.obj = None


def lru_method_cache[Tf: Callable](
    maxsize: int | None = 128,
) -> Callable[[Tf], Tf]:
    """A version of lru_cache for methods that shouldn't leak memory.

    Basically the idea is that we generate a per-object lru-cached
    partially applied method.

    Since pickling an lru_cache of a lambda or a functools.partial
    doesn't work, we wrap it in a _NoPickle object that doesn't pickle
    its contents.
    """

    def transformer(f: Tf) -> Tf:
        key = f'__{f.__name__}_cached'

        @functools.wraps(f)
        def func(self, *args, **kwargs):
            _m = getattr(self, key, None)
            if not _m:
                _m = _NoPickle(
                    functools.lru_cache(maxsize)(functools.partial(f, self))
                )
                setattr(self, key, _m)
            return _m.obj(*args, **kwargs)

        return func  # type: ignore

    return transformer


def method_cache[Tf: Callable](f: Tf) -> Tf:
    return lru_method_cache(None)(f)


def clear_method_cache[Tf](method: Tf) -> None:
    assert isinstance(method, MethodType)
    key = f'__{method.__func__.__name__}_cached'
    _m: Optional[_NoPickle] = getattr(method.__self__, key, None)
    if _m is not None:
        _m.obj.cache_clear()


_LRU_CACHES: list[functools._lru_cache_wrapper] = []


def per_job_lru_cache[Tf: Callable](
    maxsize: int | None = 128,
) -> Callable[[Tf], Tf]:
    """A version of lru_cache that can be cleared en masse.

    All the caches will be tracked and calling clear_lru_caches()
    will clear them all.
    """

    def transformer(f: Tf) -> Tf:
        wrapped = functools.lru_cache(maxsize)(f)
        _LRU_CACHES.append(wrapped)
        return wrapped  # type: ignore

    return transformer


def clear_lru_caches():
    for cache in _LRU_CACHES:
        cache.cache_clear()
