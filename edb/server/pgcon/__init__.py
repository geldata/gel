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

from .errors import (
    BackendError,
    BackendConnectionError,
    BackendPrivilegeError,
    BackendCatalogNameError,
)

from .pgcon import (
    PGConnectionRaw,
    AbstractFrontendConnection,
)
from .connect import (
    pg_connect,
    SETUP_TEMP_TABLE_SCRIPT,
    SETUP_CONFIG_CACHE_SCRIPT,
    SETUP_DML_DUMMY_TABLE_SCRIPT,
    RESET_STATIC_CFG_SCRIPT,
)

from edb.server import defines as edbdef
from typing import Protocol, Optional


class PGConnection(Protocol):
    async def sql_execute(
        self,
        sql: bytes | tuple[bytes, ...],
        *,
        tx_isolation: edbdef.TxIsolationLevel | None = None,
    ) -> None: ...

    async def sql_fetch(
        self,
        sql: bytes,
        *,
        args: tuple[bytes, ...] | list[bytes] = (),
        use_prep_stmt: bool = False,
        tx_isolation: edbdef.TxIsolationLevel | None = None,
        state: Optional[bytes] = None,
    ) -> list[tuple[bytes, ...]]: ...

    async def sql_fetch_val(
        self,
        sql: bytes,
        *,
        args: tuple[bytes, ...] | list[bytes] = (),
        use_prep_stmt: bool = False,
        tx_isolation: edbdef.TxIsolationLevel | None = None,
        state: Optional[bytes] = None,
    ) -> bytes: ...

    async def sql_fetch_col(
        self,
        sql: bytes,
        *,
        args: tuple[bytes, ...] | list[bytes] = (),
        use_prep_stmt: bool = False,
        tx_isolation: edbdef.TxIsolationLevel | None = None,
        state: Optional[bytes] = None,
    ) -> list[bytes]: ...


class PGConnectionEventListener(Protocol):
    """Protocol for PGConnection event listeners."""

    def on_pgcon_broken(self) -> None:
        """Called when a connection is broken unexpectedly."""
        pass

    def on_pgcon_lost(self) -> None:
        """Called when a connection is closed normally."""
        pass

    def on_sys_pgcon_connection_lost(self, exc: Optional[Exception]) -> None:
        """Called when a system database connection is lost."""
        pass

    def on_sys_pgcon_failover_signal(self) -> None:
        """Called when a failover signal is received from the system
        database."""
        pass

    def on_sys_pgcon_parameter_status_updated(
        self, name: str, value: str
    ) -> None:
        """Called when a parameter status is updated on a system connection."""
        pass

    def set_pg_unavailable_msg(self, msg: str) -> None:
        """Set the message to display when PostgreSQL is unavailable."""
        pass

    def on_metrics(self, metric: str, value: int) -> None:
        """Called when a metric is updated."""
        pass


__all__ = (
    'pg_connect',
    'PGConnection',
    'PGConnectionRaw',
    'PGConnectionEventListener',
    'BackendError',
    'BackendConnectionError',
    'BackendPrivilegeError',
    'BackendCatalogNameError',
    'AbstractFrontendConnection',
    'SETUP_TEMP_TABLE_SCRIPT',
    'SETUP_CONFIG_CACHE_SCRIPT',
    'SETUP_DML_DUMMY_TABLE_SCRIPT',
    'RESET_STATIC_CFG_SCRIPT'
)
