#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2011-present MagicStack Inc. and the EdgeDB authors.
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

import abc
import builtins
import collections
import collections.abc

__all__ = ['TypedList']


class TypedCollectionMeta(abc.ABCMeta):
    def __new__(mcls, name, bases, dct, *, accept_none=False, **kwargs):
        dct['__typed_accept_none__'] = bool(accept_none)
        cls = super().__new__(mcls, name, bases, dct)

        for arg in cls._TYPE_ARGS:
            try:
                arg_value = kwargs[arg]
            except KeyError:
                raise TypeError(
                    '{!r} class argument is required for {!r}'.format(
                        arg, cls))

            if arg_value is not None and not isinstance(
                    arg_value, builtins.type):
                raise ValueError('type expected for {!r} class, '
                                 'got object {!r}'.format(cls, arg_value))

            setattr(cls, arg, arg_value)

        return cls

    def __init__(cls, name, bases, dct, **kwargs):
        return super().__init__(name, bases, dct)


class AbstractTypedCollection(metaclass=TypedCollectionMeta):
    _TYPE_ARGS = ()

    def __init__(self):
        for arg in self._TYPE_ARGS:
            _type = getattr(self, arg, None)
            if _type is None:
                raise ValueError(
                    'cannot instantiate typed collection {!r} '
                    'without "type"'.format(self))

            setattr(self, arg, _type)

    def _check_type(self, value, _type, name):
        if value is None and self.__typed_accept_none__:
            return
        if not isinstance(value, _type):
            raise ValueError(
                '{!r} accepts only {} of type {!r}, got {!r}'.format(
                    type(self), name, _type, type(value)))


class AbstractTypedSequence(AbstractTypedCollection, type=None):
    _TYPE_ARGS = ('type', )

    def _check_item(self, value):
        return AbstractTypedCollection._check_type(
            self, value, self.type, 'items')

    def _check_items(self, lst):
        if isinstance(lst, TypedList) and issubclass(lst.type, self.type):
            return

        for item in lst:
            self._check_item(item)


class FrozenTypedList(AbstractTypedSequence, collections.UserList, type=None):

    def __init__(self, initlist=None):
        """
        :param iterable initlist: Values to initialize typed list with.
        """

        AbstractTypedCollection.__init__(self)
        collections.UserList.__init__(self, initlist)

        if initlist is not None:
            self._check_items(self.data)

        self._hash = -1

    def __hash__(self):
        if self._hash == -1:
            self._hash = hash(tuple(self))
        return self._hash

    __eq__ = collections.UserList.__eq__

    def __iter__(self):
        return iter(self.data)

    def __setitem__(self, i, item):
        raise NotImplementedError

    def __delitem__(self, i):
        raise NotImplementedError

    def __add__(self, other):
        raise NotImplementedError

    def __radd__(self, other):
        raise NotImplementedError

    def __iadd__(self, other):
        raise NotImplementedError

    def append(self, item):
        raise NotImplementedError

    def pop(self, i=-1):
        raise NotImplementedError

    def insert(self, i, item):
        raise NotImplementedError

    def extend(self, other):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def sort(self, *args, **kwds):
        raise NotImplementedError

    def remove(self, item):
        raise NotImplementedError

    def reverse(self):
        raise NotImplementedError


class TypedList(AbstractTypedSequence, collections.UserList, type=None):
    """List of one-type only elements.  All other properties and interface is
    the same as for the :py:class:`builtins.list`.

    .. code-block:: pycon

        >>> class IntList(TypedList, type=int):
        ...     pass

        >>> tl = IntList()

        >>> tl.append(1)

        >>> tl.append('2')
        ValueError
    """

    def __init__(self, initlist=None):
        """
        :param iterable initlist: Values to initialize typed list with.
        """

        AbstractTypedCollection.__init__(self)
        collections.UserList.__init__(self, initlist)

        if initlist is not None:
            self._check_items(self.data)

    def __iter__(self):
        return iter(self.data)

    def __setitem__(self, i, item):
        if isinstance(i, slice):
            self._check_items(item)
        else:
            self._check_item(item)
        self.data[i] = item

    def __add__(self, other):
        self._check_items(other)

        if isinstance(other, collections.UserList):
            return self.__class__(self.data + other.data)
        elif isinstance(other, type(self.data)):
            return self.__class__(self.data + other)
        return self.__class__(self.data + list(other))

    def __radd__(self, other):
        self._check_items(other)

        if isinstance(other, collections.UserList):
            return self.__class__(other.data + self.data)
        elif isinstance(other, type(self.data)):
            return self.__class__(other + self.data)
        return self.__class__(list(other) + self.data)

    def __iadd__(self, other):
        self._check_items(other)
        return super().__iadd__(other)

    def append(self, item):
        self._check_item(item)
        return self.data.append(item)

    def insert(self, i, item):
        self._check_item(item)
        return self.data.insert(i, item)

    def extend(self, other):
        self._check_items(other)
        return super().extend(other)


class IntList(TypedList, type=int):
    """List that contains only ``int`` values"""


class StrList(TypedList, type=str):
    """List that contains only ``str`` values"""
