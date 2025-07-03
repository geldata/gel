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
from typing import (
    Any,
    Callable,
    cast,
    Hashable,
    Mapping,
    NamedTuple,
    Optional,
    TYPE_CHECKING,
)

import asyncio
import collections
import dataclasses
import functools
import hmac
import logging
import os
import os.path
import pickle
import random
import signal
import subprocess
import sys
import time

import immutables
import psutil

from edb.common import debug
from edb.common import lru

from edb.pgsql import params as pgparams

from edb.schema import reflection as s_refl
from edb.schema import schema as s_schema
from edb.server import args as srvargs
from edb.server import config
from edb.server import dbview
from edb.server import defines
from edb.server import metrics

from . import amsg
from . import queue
from . import state

if TYPE_CHECKING:
    from edb import errors
    from edb import graphql
    from edb.server.compiler import compiler
    from edb.server.compiler import config as config_compiler
    from edb.server.compiler import dbstate
    from edb.server.compiler import sertypes

SyncStateCallback = Callable[[], None]
SyncFinalizer = Callable[[], None]
Config = immutables.Map[str, config.SettingValue]
InitArgs = tuple[
    pgparams.BackendRuntimeParams,
    s_schema.FlatSchema,
    s_schema.FlatSchema,
    s_refl.SchemaClassLayout,
    bytes,
    Config,
]
MultiTenantInitArgs = tuple[
    pgparams.BackendRuntimeParams,
    s_schema.FlatSchema,
    s_schema.FlatSchema,
    s_refl.SchemaClassLayout,
]
RemoteInitArgsPickle = tuple[bytes, bytes, bytes, bytes]
PreArgs = tuple[Any, ...]


PROCESS_INITIAL_RESPONSE_TIMEOUT: float = 60.0
KILL_TIMEOUT: float = 10.0
HEALTH_CHECK_MIN_INTERVAL: float = float(
    os.getenv("GEL_COMPILER_HEALTH_CHECK_MIN_INTERVAL", 10)
)
HEALTH_CHECK_TIMEOUT: float = float(
    os.getenv("GEL_COMPILER_HEALTH_CHECK_TIMEOUT", 10)
)
ADAPTIVE_SCALE_UP_WAIT_TIME: float = 3.0
ADAPTIVE_SCALE_DOWN_WAIT_TIME: float = 60.0
WORKER_PKG: str = __name__.rpartition('.')[0] + '.'
DEFAULT_CLIENT: str = 'default'
HIGH_RSS_GRACE_PERIOD: tuple[int, int] = (20 * 3600, 30 * 3600)
CURRENT_COMPILER_PROTOCOL = 2


logger = logging.getLogger("edb.server")
log_metrics = logging.getLogger("edb.server.metrics")


# Inherit sys.path so that import system can find worker class
# in unittests.
_ENV = os.environ.copy()
_ENV['PYTHONPATH'] = ':'.join(sys.path)


@functools.lru_cache(maxsize=4)
def _pickle_memoized(obj: Any) -> bytes:
    return pickle.dumps(obj, -1)


class BaseWorker:

    _dbs: collections.OrderedDict[str, state.PickledDatabaseState]
    _backend_runtime_params: pgparams.BackendRuntimeParams
    _std_schema: s_schema.FlatSchema
    _refl_schema: s_schema.FlatSchema
    _schema_class_layout: s_refl.SchemaClassLayout
    _global_schema_pickle: bytes
    _system_config: Config
    _last_pickled_state: Optional[bytes]

    _con: Optional[amsg.HubConnection]
    _last_used: float
    _closed: bool

    def __init__(
        self,
        backend_runtime_params: pgparams.BackendRuntimeParams,
        std_schema: s_schema.FlatSchema,
        refl_schema: s_schema.FlatSchema,
        schema_class_layout: s_refl.SchemaClassLayout,
        global_schema_pickle: bytes,
        system_config: Config,
    ) -> None:
        self._dbs = collections.OrderedDict()
        self._backend_runtime_params = backend_runtime_params
        self._std_schema = std_schema
        self._refl_schema = refl_schema
        self._schema_class_layout = schema_class_layout
        self._global_schema_pickle = global_schema_pickle
        self._system_config = system_config
        self._last_pickled_state = None

        self._con = None
        self._last_used = time.monotonic()
        self._closed = False

    def get_db(self, name: str) -> Optional[state.PickledDatabaseState]:
        rv = self._dbs.get(name)
        if rv is not None:
            self._dbs.move_to_end(name, last=False)
        return rv

    def set_db(self, name: str, db: state.PickledDatabaseState) -> None:
        self._dbs[name] = db
        self._dbs.move_to_end(name, last=False)

    def prepare_evict_db(self, keep: int) -> list[str]:
        return list(self._dbs.keys())[keep:]

    def evict_db(self, name: str) -> Optional[state.PickledDatabaseState]:
        return self._dbs.pop(name, None)

    async def call(
        self,
        method_name: str,
        *args: Any,
        sync_state: Optional[SyncStateCallback] = None,
    ) -> Any:
        assert not self._closed
        assert self._con is not None

        if self._con.is_closed():
            raise RuntimeError(
                'the connection to the compiler worker process is '
                'unexpectedly closed')

        data = await self._request(method_name, args)

        status, *result = pickle.loads(data)

        self._last_used = time.monotonic()

        if status == 0:
            if sync_state is not None:
                sync_state()
            return result[0]
        elif status == 1:
            exc, tb = result
            if (sync_state is not None and
                    not isinstance(exc, state.FailedStateSync)):
                sync_state()
            exc.__formatted_error__ = tb
            raise exc
        else:
            exc = RuntimeError(
                'could not serialize result in worker subprocess')
            exc.__formatted_error__ = result[0]
            raise exc

    async def _request(
        self,
        method_name: str,
        args: tuple[Any, ...],
    ) -> memoryview:
        assert self._con is not None
        msg = pickle.dumps((method_name, args))
        return await self._con.request(msg)


class Worker(BaseWorker):

    _pid: int
    _proc: psutil.Process
    _manager: BaseLocalPool
    _server: amsg.Server
    _allow_high_rss_until: float

    def __init__(
        self,
        manager: BaseLocalPool,
        server: amsg.Server,
        pid: int,
        *args: Any,
    ) -> None:
        super().__init__(*args)

        self._pid = pid
        self._proc = psutil.Process(pid)
        self._manager = manager
        self._server = server
        grace_period = random.SystemRandom().randint(*HIGH_RSS_GRACE_PERIOD)
        self._allow_high_rss_until = time.monotonic() + grace_period

    async def _attach(self, init_args_pickled: bytes) -> None:
        self._manager._stats_spawned += 1

        self._con = self._server.get_by_pid(self._pid)

        await self.call(
            '__init_worker__',
            init_args_pickled,
        )

    def set_db(self, name: str, db: state.PickledDatabaseState) -> None:
        pid = str(self._pid)
        old_size: Optional[int] = None
        if (old_db := self._dbs.get(name)) is not None:
            old_size = old_db.get_estimated_size()
        super().set_db(name, db)
        metrics.compiler_process_schema_size.inc(
            db.get_estimated_size() - (old_size or 0), pid, DEFAULT_CLIENT
        )
        if old_size is None:
            action = 'cache-add'
            metrics.compiler_process_branches.set(
                len(self._dbs), pid, DEFAULT_CLIENT
            )
        else:
            action = 'cache-update'
        metrics.compiler_process_branch_actions.inc(
            1, pid, DEFAULT_CLIENT, action
        )

    def evict_db(self, name: str) -> Optional[state.PickledDatabaseState]:
        pid = str(self._pid)
        db = self._dbs.get(name)
        super().evict_db(name)
        if db is not None:
            metrics.compiler_process_schema_size.dec(
                db.get_estimated_size(), pid, DEFAULT_CLIENT
            )
            metrics.compiler_process_branch_actions.inc(
                1, pid, DEFAULT_CLIENT, 'cache-evict'
            )
        return db

    def get_pid(self) -> int:
        return self._pid

    def get_rss(self) -> int:
        return self._proc.memory_info().rss

    def maybe_close_for_high_rss(self, max_rss: int) -> bool:
        if time.monotonic() > self._allow_high_rss_until:
            rss = self.get_rss()
            if rss > max_rss:
                logger.info(
                    'worker process with PID %d exceeds high RSS limit '
                    '(%d > %d), killing now',
                    self._pid, rss, max_rss,
                )
                self.close()
                return True

        return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        metrics.compiler_process_kills.inc()
        self._manager._stats_killed += 1
        self._manager._workers.pop(self._pid, None)
        self._manager._report_worker(self, action="kill")
        try:
            os.kill(self._pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


class AbstractPool[
    BaseWorker_T: BaseWorker, InitArgs_T, InitArgsPickle_T,
]:

    _loop: asyncio.AbstractEventLoop
    _worker_branch_limit: int
    _backend_runtime_params: pgparams.BackendRuntimeParams
    _std_schema: s_schema.FlatSchema
    _refl_schema: s_schema.FlatSchema
    _schema_class_layout: s_refl.SchemaClassLayout
    _dbindex: Optional[dbview.DatabaseIndex] = None
    _last_active_time: float

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        worker_branch_limit: int,
        **kwargs: Any,
    ) -> None:
        self._loop = loop
        self._worker_branch_limit = worker_branch_limit
        self._init(kwargs)

    def _init(self, kwargs: dict[str, Any]) -> None:
        self._backend_runtime_params = kwargs["backend_runtime_params"]
        self._std_schema = kwargs["std_schema"]
        self._refl_schema = kwargs["refl_schema"]
        self._schema_class_layout = kwargs["schema_class_layout"]
        self._dbindex = kwargs.get("dbindex")
        self._last_active_time = 0

    def _get_init_args(self) -> tuple[InitArgs_T, InitArgsPickle_T]:
        assert self._dbindex is not None
        return self._make_cached_init_args(
            *self._dbindex.get_cached_compiler_args()
        )

    def _make_cached_init_args(
        self,
        global_schema_pickle: bytes,
        system_config: Config,
    ) -> tuple[InitArgs_T, InitArgsPickle_T]:
        raise NotImplementedError

    def _make_init_args(
        self,
        global_schema_pickle: bytes,
        system_config: Config,
    ) -> InitArgs:
        return (
            self._backend_runtime_params,
            self._std_schema,
            self._refl_schema,
            self._schema_class_layout,
            global_schema_pickle,
            system_config,
        )

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    def get_template_pid(self) -> Optional[int]:
        return None

    async def _compute_compile_preargs(
        self,
        method_name: str,
        worker: BaseWorker_T,
        dbname: str,
        user_schema_pickle: bytes,
        global_schema_pickle: bytes,
        reflection_cache: state.ReflectionCache,
        database_config: Config,
        system_config: Config,
    ) -> tuple[PreArgs, Optional[SyncStateCallback], SyncFinalizer]:

        def sync_worker_state_cb(
            *,
            worker: BaseWorker_T,
            dbname: str,
            user_schema_pickle: Optional[bytes] = None,
            global_schema_pickle: Optional[bytes] = None,
            reflection_cache: Optional[state.ReflectionCache] = None,
            database_config: Optional[Config] = None,
            system_config: Optional[Config] = None,
            evicted_dbs: Optional[list[str]] = None,
        ):
            if evicted_dbs is not None:
                for name in evicted_dbs:
                    worker.evict_db(name)

            worker_db = worker.get_db(dbname)
            if worker_db is None:
                assert user_schema_pickle is not None
                assert reflection_cache is not None
                assert global_schema_pickle is not None
                assert database_config is not None
                assert system_config is not None

                worker.set_db(
                    dbname,
                    state.PickledDatabaseState(
                        user_schema_pickle=user_schema_pickle,
                        reflection_cache=reflection_cache,
                        database_config=database_config,
                    ),
                )
                worker._global_schema_pickle = global_schema_pickle
                worker._system_config = system_config
            else:
                if (
                    user_schema_pickle is not None
                    or reflection_cache is not None
                    or database_config is not None
                ):
                    worker.set_db(
                        dbname,
                        state.PickledDatabaseState(
                            user_schema_pickle=(
                                user_schema_pickle
                                or worker_db.user_schema_pickle
                            ),
                            reflection_cache=(
                                worker_db.reflection_cache
                                if reflection_cache is None
                                else reflection_cache
                            ),
                            database_config=(
                                worker_db.database_config
                                if database_config is None
                                else database_config
                            ),
                        ),
                    )

                if global_schema_pickle is not None:
                    worker._global_schema_pickle = global_schema_pickle
                if system_config is not None:
                    worker._system_config = system_config

        worker_db = worker.get_db(dbname)
        preargs: list[Any] = [method_name, dbname]
        to_update: dict[str, Any] = {}
        branch_cache_hit = True

        if worker_db is None:
            branch_cache_hit = False
            evicted_dbs = worker.prepare_evict_db(
                self._worker_branch_limit - 1
            )
            preargs.extend([
                evicted_dbs,
                user_schema_pickle,
                _pickle_memoized(reflection_cache),
                global_schema_pickle,
                _pickle_memoized(database_config),
                _pickle_memoized(system_config),
            ])
            to_update = {
                'evicted_dbs': evicted_dbs,
                'user_schema_pickle': user_schema_pickle,
                'reflection_cache': reflection_cache,
                'global_schema_pickle': global_schema_pickle,
                'database_config': database_config,
                'system_config': system_config,
            }
        else:
            preargs.append([])  # evicted_dbs

            if worker_db.user_schema_pickle is not user_schema_pickle:
                branch_cache_hit = False
                preargs.append(user_schema_pickle)
                to_update['user_schema_pickle'] = user_schema_pickle
            else:
                preargs.append(None)

            if worker_db.reflection_cache is not reflection_cache:
                branch_cache_hit = False
                preargs.append(_pickle_memoized(reflection_cache))
                to_update['reflection_cache'] = reflection_cache
            else:
                preargs.append(None)

            if worker._global_schema_pickle is not global_schema_pickle:
                preargs.append(global_schema_pickle)
                to_update['global_schema_pickle'] = global_schema_pickle
            else:
                preargs.append(None)

            if worker_db.database_config is not database_config:
                branch_cache_hit = False
                preargs.append(_pickle_memoized(database_config))
                to_update['database_config'] = database_config
            else:
                preargs.append(None)

            if worker._system_config is not system_config:
                preargs.append(_pickle_memoized(system_config))
                to_update['system_config'] = system_config
            else:
                preargs.append(None)

        self._report_branch_request(worker, branch_cache_hit)

        if to_update:
            callback = functools.partial(
                sync_worker_state_cb,
                worker=worker,
                dbname=dbname,
                **to_update
            )
        else:
            callback = None

        return tuple(preargs), callback, lambda: None

    def _report_branch_request(
        self,
        worker: BaseWorker_T,
        cache_hit: bool,
        client: str = DEFAULT_CLIENT,
    ) -> None:
        pass

    async def _acquire_worker(
        self,
        *,
        condition: Optional[queue.AcquireCondition[BaseWorker_T]] = None,
        weighter: Optional[queue.Weighter[BaseWorker_T]] = None,
        **compiler_args: Any,
    ) -> BaseWorker_T:
        raise NotImplementedError

    def _release_worker(
        self,
        worker: BaseWorker_T,
        *,
        put_in_front: bool = True,
    ) -> None:
        raise NotImplementedError

    async def compile(
        self,
        dbname: str,
        user_schema_pickle: bytes,
        global_schema_pickle: bytes,
        reflection_cache: state.ReflectionCache,
        database_config: Config,
        system_config: Config,
        *compile_args: Any,
        **compiler_args: Any,
    ) -> tuple[dbstate.QueryUnitGroup, bytes, int]:
        fini = lambda: None
        worker = await self._acquire_worker(**compiler_args)
        try:
            preargs, sync_state, fini = await self._compute_compile_preargs(
                "compile",
                worker,
                dbname,
                user_schema_pickle,
                global_schema_pickle,
                reflection_cache,
                database_config,
                system_config,
            )

            result = await worker.call(
                *preargs,
                *compile_args,
                sync_state=sync_state
            )
            worker._last_pickled_state = result[1]
            if len(result) == 2:
                return *result, 0
            else:
                return result

        finally:
            fini()
            self._release_worker(worker)

    async def compile_in_tx(
        self,
        dbname: str,
        user_schema_pickle: bytes,
        txid: int,
        pickled_state: bytes,
        state_id: int,
        *compile_args: Any,
        **compiler_args: Any,
    ) -> tuple[dbstate.QueryUnitGroup, bytes, int]:
        # When we compile a query, the compiler returns a tuple:
        # a QueryUnit and the state the compiler is in if it's in a
        # transaction.  The state contains the information about all savepoints
        # and transient schema changes, so the next time we need to
        # compile a new query in this transaction the state is needed
        # to be passed to the next compiler compiling it.
        #
        # The compile state can be quite heavy and contain multiple versions
        # of schema, configs, and other session-related data. So the compiler
        # worker pickles it before sending it to the IO process, and the
        # IO process doesn't need to ever unpickle it.
        #
        # There's one crucial optimization we do here though. We try to
        # find the compiler process that we used before, that already has
        # this state unpickled. If we can find it, it means that the
        # compiler process won't have to waste time unpickling the state.
        #
        # We use "is" in `w._last_pickled_state is pickled_state` deliberately,
        # because `pickled_state` is saved on the Worker instance and
        # stored in edgecon; we never modify it, so `is` is sufficient and
        # is faster than `==`.
        worker = await self._acquire_worker(
            condition=lambda w: (w._last_pickled_state is pickled_state),
            compiler_args=compiler_args,
        )

        dbname_arg = None
        user_schema_pickle_arg = None
        if worker._last_pickled_state is pickled_state:
            # Since we know that this particular worker already has the
            # state, we don't want to waste resources transferring the
            # state over the network. So we replace the state with a marker,
            # that the compiler process will recognize.
            pickled_state = state.REUSE_LAST_STATE_MARKER
        else:
            worker_db = worker.get_db(dbname)
            if (
                worker_db is not None
                and worker_db.user_schema_pickle is user_schema_pickle
            ):
                dbname_arg = dbname
            else:
                user_schema_pickle_arg = user_schema_pickle

        try:
            units, new_pickled_state = await worker.call(
                'compile_in_tx',
                dbname_arg,
                user_schema_pickle_arg,
                pickled_state,
                txid,
                *compile_args
            )
            worker._last_pickled_state = new_pickled_state
            return units, new_pickled_state, 0

        finally:
            # Put the worker at the end of the queue so that the chance
            # of reusing it later (and maximising the chance of
            # the w._last_pickled_state is pickled_state` check returning
            # `True` is higher.
            self._release_worker(worker, put_in_front=False)

    async def compile_notebook(
        self,
        dbname: str,
        user_schema_pickle: bytes,
        global_schema_pickle: bytes,
        reflection_cache: state.ReflectionCache,
        database_config: Config,
        system_config: Config,
        *compile_args: Any,
        **compiler_args: Any,
    ) -> list[
        tuple[
            bool,
            dbstate.QueryUnit | tuple[str, str, dict[int, str]]
        ]
    ]:
        fini = lambda: None
        worker = await self._acquire_worker(**compiler_args)
        try:
            preargs, sync_state, fini = await self._compute_compile_preargs(
                "compile_notebook",
                worker,
                dbname,
                user_schema_pickle,
                global_schema_pickle,
                reflection_cache,
                database_config,
                system_config,
            )

            return await worker.call(
                *preargs,
                *compile_args,
                sync_state=sync_state
            )

        finally:
            fini()
            self._release_worker(worker)

    async def compile_graphql(
        self,
        dbname: str,
        user_schema_pickle: bytes,
        global_schema_pickle: bytes,
        reflection_cache: state.ReflectionCache,
        database_config: Config,
        system_config: Config,
        *compile_args: Any,
        **compiler_args: Any,
    ) -> graphql.TranspiledOperation:
        fini = lambda: None
        worker = await self._acquire_worker(**compiler_args)
        try:
            preargs, sync_state, fini = await self._compute_compile_preargs(
                "compile_graphql",
                worker,
                dbname,
                user_schema_pickle,
                global_schema_pickle,
                reflection_cache,
                database_config,
                system_config,
            )

            return await worker.call(
                *preargs,
                *compile_args,
                sync_state=sync_state
            )

        finally:
            fini()
            self._release_worker(worker)

    async def compile_sql(
        self,
        dbname: str,
        user_schema_pickle: bytes,
        global_schema_pickle: bytes,
        reflection_cache: state.ReflectionCache,
        database_config: Config,
        system_config: Config,
        *compile_args: Any,
        **compiler_args: Any,
    ) -> list[dbstate.SQLQueryUnit]:
        fini = lambda: None
        worker = await self._acquire_worker(**compiler_args)
        try:
            preargs, sync_state, fini = await self._compute_compile_preargs(
                "compile_sql",
                worker,
                dbname,
                user_schema_pickle,
                global_schema_pickle,
                reflection_cache,
                database_config,
                system_config,
            )

            return await worker.call(
                *preargs,
                *compile_args,
                sync_state=sync_state
            )
        finally:
            fini()
            self._release_worker(worker)

    # We use a helper function instead of just fully generating the
    # functions in order to make the backtraces a little better.
    async def _simple_call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        worker = await self._acquire_worker()
        try:
            return await worker.call(
                name,
                *args,
                **kwargs
            )

        finally:
            self._release_worker(worker)

    async def interpret_backend_error(
        self,
        user_schema: bytes,
        global_schema: bytes,
        error_fields: dict[str, str],
        from_graphql: bool,
    ) -> errors.EdgeDBError:
        return await self._simple_call(
            'interpret_backend_error',
            user_schema,
            global_schema,
            error_fields,
            from_graphql,
        )

    async def parse_global_schema(self, global_schema_json: bytes) -> bytes:
        return await self._simple_call(
            'parse_global_schema', global_schema_json
        )

    async def parse_user_schema_db_config(
        self,
        user_schema_json: bytes,
        db_config_json: bytes,
        global_schema_pickle: bytes,
    ) -> dbstate.ParsedDatabase:
        return await self._simple_call(
            'parse_user_schema_db_config',
            user_schema_json,
            db_config_json,
            global_schema_pickle,
        )

    async def make_state_serializer(
        self,
        protocol_version: defines.ProtocolVersion,
        user_schema_pickle: bytes,
        global_schema_pickle: bytes,
    ) -> sertypes.StateSerializer:
        return await self._simple_call(
            'make_state_serializer',
            protocol_version,
            user_schema_pickle,
            global_schema_pickle,
        )

    async def make_compilation_config_serializer(
        self
    ) -> sertypes.CompilationConfigSerializer:
        return await self._simple_call('make_compilation_config_serializer')

    async def describe_database_dump(
        self,
        user_schema_json: bytes,
        global_schema_json: bytes,
        db_config_json: bytes,
        protocol_version: defines.ProtocolVersion,
        with_secrets: bool,
    ) -> compiler.DumpDescriptor:
        return await self._simple_call(
            'describe_database_dump',
            user_schema_json,
            global_schema_json,
            db_config_json,
            protocol_version,
            with_secrets,
        )

    async def describe_database_restore(
        self,
        user_schema_pickle: bytes,
        global_schema_pickle: bytes,
        dump_server_ver_str: str,
        dump_catalog_version: Optional[int],
        schema_ddl: bytes,
        schema_ids: list[tuple[str, str, bytes]],
        blocks: list[tuple[bytes, bytes]],  # type_id, typespec
        protocol_version: defines.ProtocolVersion,
    ) -> compiler.RestoreDescriptor:
        return await self._simple_call(
            'describe_database_restore',
            user_schema_pickle,
            global_schema_pickle,
            dump_server_ver_str,
            dump_catalog_version,
            schema_ddl,
            schema_ids,
            blocks,
            protocol_version,
        )

    async def analyze_explain_output(
        self,
        query_asts_pickled: bytes,
        data: list[list[bytes]],
    ) -> bytes:
        return await self._simple_call(
            'analyze_explain_output', query_asts_pickled, data
        )

    async def validate_schema_equivalence(
        self,
        schema_a: bytes,
        schema_b: bytes,
        global_schema: bytes,
        conn_state_pickle: Optional[bytes],
    ) -> None:
        return await self._simple_call(
            'validate_schema_equivalence',
            schema_a,
            schema_b,
            global_schema,
            conn_state_pickle,
        )

    async def compile_structured_config(
        self,
        objects: Mapping[str, config_compiler.ConfigObject],
        source: str | None = None,
        allow_nested: bool = False,
    ) -> dict[str, Config]:
        return await self._simple_call(
            'compile_structured_config', objects, source, allow_nested
        )

    def get_debug_info(self) -> dict[str, Any]:
        return {}

    def get_size_hint(self) -> int:
        raise NotImplementedError

    def refresh_metrics(self) -> None:
        pass

    def _maybe_update_last_active_time(self) -> None:
        if sys.exc_info()[0] is None:
            self._last_active_time = time.monotonic()

    async def health_check(self) -> bool:
        elapsed = time.monotonic() - self._last_active_time
        if elapsed > HEALTH_CHECK_MIN_INTERVAL:
            async with asyncio.timeout(HEALTH_CHECK_TIMEOUT):
                await self.make_compilation_config_serializer()
            self._maybe_update_last_active_time()
        return True


class BaseLocalPool[Worker_T: Worker, InitArgs_T](
    AbstractPool[Worker_T, InitArgs_T, bytes],
    amsg.ServerProtocol,
    asyncio.SubprocessProtocol,
):

    _worker_class: type[Worker_T]
    _worker_mod: str = "worker"
    _workers_queue: queue.WorkerQueue[Worker_T]
    _workers: dict[int, Worker_T]

    _poolsock_name: str
    _pool_size: int
    _worker_max_rss: Optional[int]
    _server: Optional[amsg.Server]
    _ready_evt: asyncio.Event
    _running: Optional[bool]
    _stats_spawned: int
    _stats_killed: int

    def __init__(
        self,
        *,
        runstate_dir: str,
        pool_size: int,
        worker_max_rss: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self._poolsock_name = os.path.join(runstate_dir, 'ipc')
        assert len(self._poolsock_name) <= (
            defines.MAX_RUNSTATE_DIR_PATH
            + defines.MAX_UNIX_SOCKET_PATH_LENGTH
            + 1
        ), "pool IPC socket length exceeds maximum allowed"

        assert pool_size >= 1
        self._pool_size = pool_size
        self._worker_max_rss = worker_max_rss
        self._workers = {}

        self._server = amsg.Server(self._poolsock_name, self._loop, self)
        self._ready_evt = asyncio.Event()

        self._running = None

        self._stats_spawned = 0
        self._stats_killed = 0

    def _report_branch_request(
        self, worker: Worker_T, cache_hit: bool, client: str = DEFAULT_CLIENT
    ) -> None:
        pid = str(worker.get_pid())
        metrics.compiler_process_branch_actions.inc(
            1, pid, client, 'request'
        )
        if cache_hit:
            metrics.compiler_process_branch_actions.inc(
                1, pid, client, 'cache-hit'
            )

    def is_running(self) -> bool:
        return bool(self._running)

    async def _attach_worker(self, pid: int) -> Optional[Worker_T]:
        if not self._running:
            return None
        assert self._server is not None
        logger.debug("Sending init args to worker with PID %s.", pid)
        init_args, init_args_pickled = self._get_init_args()
        worker = self._worker_class(  # type: ignore
            self,
            self._server,
            pid,
            *init_args,
        )
        await worker._attach(init_args_pickled)
        self._report_worker(worker)

        self._workers[pid] = worker
        self._workers_queue.release(worker)
        self._worker_attached()

        logger.debug("started compiler worker process (PID %s)", pid)
        if (
            not self._ready_evt.is_set()
            and len(self._workers) == self._pool_size
        ):
            logger.info(
                f"started {self._pool_size} compiler worker "
                f"process{'es' if self._pool_size > 1 else ''}",
            )
            self._ready_evt.set()

        return worker

    def _worker_attached(self) -> None:
        pass

    def worker_connected(self, pid: int, version: int) -> None:
        logger.debug("Worker with PID %s connected.", pid)
        self._loop.create_task(self._attach_worker(pid))
        metrics.compiler_process_spawns.inc()
        metrics.current_compiler_processes.inc()

    def worker_disconnected(self, pid: int) -> None:
        logger.debug("Worker with PID %s disconnected.", pid)
        self._workers.pop(pid, None)
        metrics.current_compiler_processes.dec()

        expect = str(pid)

        def pid_filter(pid_str: str, *remaining_tags) -> bool:
            return pid_str == expect

        metrics.compiler_process_memory.clear(pid_filter)
        metrics.compiler_process_schema_size.clear(pid_filter)
        metrics.compiler_process_branches.clear(pid_filter)
        metrics.compiler_process_branch_actions.clear(pid_filter)
        metrics.compiler_process_client_actions.clear(pid_filter)

    async def start(self) -> None:
        if self._running is not None:
            raise RuntimeError(
                'the compiler pool has already been started once')
        assert self._server is not None

        self._workers_queue = queue.WorkerQueue(self._loop)

        await self._server.start()
        self._running = True

        await self._start()

        await self._wait_ready()

    async def _wait_ready(self) -> None:
        await asyncio.wait_for(
            self._ready_evt.wait(),
            PROCESS_INITIAL_RESPONSE_TIMEOUT
        )

    async def _create_compiler_process(
        self, numproc: Optional[int] = None, version: int = 0
    ) -> asyncio.SubprocessTransport:
        # Create a new compiler process. When numproc is None, a single
        # standalone compiler worker process is started; if numproc is an int,
        # a compiler template process will be created, which will then fork
        # itself into `numproc` actual worker processes and run as a supervisor

        env = _ENV
        if debug.flags.server:
            env = {'EDGEDB_DEBUG_SERVER': '1', **_ENV}

        cmdline = [sys.executable]
        if sys.flags.isolated:
            cmdline.append('-I')

        cmdline.extend([
            '-m', WORKER_PKG + self._worker_mod,
            '--sockname', self._poolsock_name,
            '--version-serial', str(version),
        ])
        if numproc:
            cmdline.extend([
                '--numproc', str(numproc),
            ])

        transport, _ = await self._loop.subprocess_exec(
            lambda: self,
            *cmdline,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=None,
        )
        return transport

    async def _start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False

        assert self._server is not None
        await self._server.stop()
        self._server = None

        self._workers_queue = queue.WorkerQueue(self._loop)
        self._workers.clear()

        await self._stop()

    async def _stop(self) -> None:
        raise NotImplementedError

    def _report_worker(
        self, worker: Worker_T, *, action: str = "spawn"
    ) -> None:
        action = action.capitalize()
        if not action.endswith("e"):
            action += "e"
        action += "d"
        log_metrics.info(
            "%s a compiler worker with PID %d; pool=%d;"
            + " spawned=%d; killed=%d",
            action,
            worker.get_pid(),
            len(self._workers),
            self._stats_spawned,
            self._stats_killed,
        )

    async def _acquire_worker(
        self,
        *,
        condition: Optional[queue.AcquireCondition[Worker_T]] = None,
        weighter: Optional[queue.Weighter[Worker_T]] = None,
        **compiler_args: Any,
    ) -> Worker_T:
        start_time = time.monotonic()
        try:
            while (
                worker := await self._workers_queue.acquire(
                    condition=condition, weighter=weighter
                )
            ).get_pid() not in self._workers:
                # The worker was disconnected; skip to the next one.
                pass
        except TimeoutError:
            metrics.compiler_pool_queue_errors.inc(1.0, "timeout")
            raise
        except Exception:
            metrics.compiler_pool_queue_errors.inc(1.0, "ise")
            raise
        else:
            metrics.compiler_pool_wait_time.observe(
                time.monotonic() - start_time
            )
            return worker

    def _release_worker(
        self,
        worker: Worker_T,
        *,
        put_in_front: bool = True,
    ) -> None:
        # Skip disconnected workers
        if worker.get_pid() in self._workers:
            if self._worker_max_rss is not None:
                if worker.maybe_close_for_high_rss(self._worker_max_rss):
                    return
            self._workers_queue.release(worker, put_in_front=put_in_front)
        self._maybe_update_last_active_time()

    def get_debug_info(self) -> dict[str, Any]:
        return dict(
            worker_pids=list(self._workers.keys()),
            template_pid=self.get_template_pid(),
        )

    def refresh_metrics(self) -> None:
        for w in self._workers.values():
            metrics.compiler_process_memory.set(w.get_rss(), str(w.get_pid()))

    async def health_check(self) -> bool:
        if not (
            self._running
            and self._ready_evt.is_set()
            and len(self._workers) > 0
        ):
            return False
        return await super().health_check()


class FixedPoolImpl[Worker_T: Worker, InitArgs_T](
    BaseLocalPool[Worker_T, InitArgs_T],
):

    _template_transport: Optional[asyncio.SubprocessTransport]
    _template_proc_scheduled: bool
    _template_proc_version: int

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._template_transport = None
        self._template_proc_scheduled = False
        self._template_proc_version = 0

    def _worker_attached(self) -> None:
        if not self._running:
            return
        assert self._server is not None
        if len(self._workers) > self._pool_size:
            self._server.kill_outdated_worker(self._template_proc_version)

    def worker_connected(self, pid: int, version: int) -> None:
        if not self._running:
            return
        assert self._server is not None
        if version < self._template_proc_version:
            logger.debug(
                "Outdated worker with PID %s connected; discard now.", pid
            )
            self._server.get_by_pid(pid).abort()
            metrics.compiler_process_spawns.inc()
        else:
            super().worker_connected(pid, version)

    def process_exited(self) -> None:
        # Template process exited
        self._template_transport = None
        if self._running:
            logger.error("Template compiler process exited; recreating now.")
            self._schedule_template_proc(0)

    def get_template_pid(self) -> Optional[int]:
        if self._template_transport is None:
            return None
        else:
            return self._template_transport.get_pid()

    async def _start(self) -> None:
        await self._create_template_proc(retry=False)

    async def _create_template_proc(self, retry: bool = True) -> None:
        self._template_proc_scheduled = False
        if not self._running:
            return
        self._template_proc_version += 1
        try:
            # Create the template process, which will then fork() into numproc
            # child processes and manage them, so that we don't have to manage
            # the actual compiler worker processes in the main process.
            self._template_transport = await self._create_compiler_process(
                numproc=self._pool_size,
                version=self._template_proc_version,
            )
        except Exception:
            if retry:
                if self._running:
                    t = defines.BACKEND_COMPILER_TEMPLATE_PROC_RESTART_INTERVAL
                    logger.exception(
                        f"Unexpected error occurred creating template compiler"
                        f" process; retry in {t} second{'s' if t > 1 else ''}."
                    )
                    self._schedule_template_proc(t)
            else:
                raise

    def _schedule_template_proc(self, sleep: float) -> None:
        if self._template_proc_scheduled:
            return
        self._template_proc_scheduled = True
        self._loop.call_later(
            sleep, self._loop.create_task, self._create_template_proc()
        )

    async def _stop(self) -> None:
        trans, self._template_transport = self._template_transport, None
        if trans is not None:
            trans.terminate()
            await trans._wait()  # type: ignore
            trans.close()

    def get_size_hint(self) -> int:
        return self._pool_size


@srvargs.CompilerPoolMode.Fixed.assign_implementation
class FixedPool(FixedPoolImpl[Worker, InitArgs]):

    _worker_class = Worker

    @lru.lru_method_cache(1)
    def _make_cached_init_args(
        self,
        global_schema_pickle: bytes,
        system_config: Config,
    ) -> tuple[InitArgs, bytes]:
        init_args = self._make_init_args(
            global_schema_pickle, system_config
        )
        pickled_args = pickle.dumps(init_args, -1)
        return init_args, pickled_args


@srvargs.CompilerPoolMode.OnDemand.assign_implementation
class SimpleAdaptivePool(BaseLocalPool[Worker, InitArgs]):

    _worker_class = Worker
    _worker_transports: dict[int, asyncio.SubprocessTransport]
    _expected_num_workers: int
    _scale_down_handle: Optional[asyncio.Handle]
    _max_num_workers: int
    _cleanups: dict[int, asyncio.Future]

    def __init__(self, *, pool_size: int, **kwargs: Any) -> None:
        super().__init__(pool_size=1, **kwargs)
        self._worker_transports = {}
        self._expected_num_workers = 0
        self._scale_down_handle = None
        self._max_num_workers = pool_size
        self._cleanups = {}

    @lru.lru_method_cache(1)
    def _make_cached_init_args(
        self,
        global_schema_pickle: bytes,
        system_config: Config,
    ) -> tuple[InitArgs, bytes]:
        init_args = self._make_init_args(
            global_schema_pickle, system_config
        )
        pickled_args = pickle.dumps(init_args, -1)
        return init_args, pickled_args

    async def _start(self) -> None:
        async with asyncio.TaskGroup() as g:
            for _i in range(self._pool_size):
                g.create_task(self._create_worker())

    async def _stop(self) -> None:
        self._expected_num_workers = 0
        transports, self._worker_transports = self._worker_transports, {}
        for transport in transports.values():
            await transport._wait()  # type: ignore
            transport.close()
        for cleanup in list(self._cleanups.values()):
            await cleanup

    async def _acquire_worker(
        self,
        *,
        condition: Optional[queue.AcquireCondition[Worker]] = None,
        weighter: Optional[queue.Weighter[Worker]] = None,
        **compiler_args: Any,
    ) -> Worker:
        scale_up_handle = None
        if (
            self._running
            and self._workers_queue.qsize() == 0
            and (
                len(self._workers)
                == self._expected_num_workers
                < self._max_num_workers
            )
        ):
            scale_up_handle = self._loop.call_later(
                ADAPTIVE_SCALE_UP_WAIT_TIME, self._maybe_scale_up
            )
        if self._scale_down_handle is not None:
            self._scale_down_handle.cancel()
            self._scale_down_handle = None
        try:
            return await super()._acquire_worker(
                condition=condition, weighter=weighter, **compiler_args
            )
        finally:
            if scale_up_handle is not None:
                scale_up_handle.cancel()

    def _release_worker(
        self,
        worker: Worker,
        *,
        put_in_front: bool = True,
    ) -> None:
        if self._scale_down_handle is not None:
            self._scale_down_handle.cancel()
            self._scale_down_handle = None
        super()._release_worker(worker, put_in_front=put_in_front)
        if (
            self._running and
            self._workers_queue.count_waiters() == 0 and
            len(self._workers) > self._pool_size
        ):
            self._scale_down_handle = self._loop.call_later(
                ADAPTIVE_SCALE_DOWN_WAIT_TIME,
                self._scale_down,
            )

    async def _wait_on_dying(
        self,
        pid: int,
        trans: asyncio.SubprocessTransport,
    ) -> None:
        await trans._wait()  # type: ignore
        self._cleanups.pop(pid)

    def worker_disconnected(self, pid: int) -> None:
        num_workers_before = len(self._workers)
        super().worker_disconnected(pid)
        trans = self._worker_transports.pop(pid, None)
        if trans:
            trans.close()
            # amsg.Server notifies us when the *pipe* to the worker closes,
            # so we need to fire off a task to make sure that we wait for
            # the worker to exit, in order to avoid a warning.
            self._cleanups[pid] = (
                self._loop.create_task(self._wait_on_dying(pid, trans)))
        if not self._running:
            return
        if len(self._workers) < self._pool_size:
            # The auto-scaler will not scale down below the pool_size, so we
            # should restart the unexpectedly-exited worker process.
            logger.warning(
                "Compiler worker process[%d] exited unexpectedly; "
                "start a new one now.", pid
            )
            self._loop.create_task(self._create_worker())
            self._expected_num_workers = len(self._workers)
        elif num_workers_before == self._expected_num_workers:
            # This is likely the case when a worker died unexpectedly, and we
            # don't want to restart the worker because the auto-scaler will
            # start a new one again if necessary.
            self._expected_num_workers = len(self._workers)

    def process_exited(self) -> None:
        if self._running:
            for pid, transport in list(self._worker_transports.items()):
                if transport.is_closing():
                    self._worker_transports.pop(pid, None)

    async def _create_worker(self) -> None:
        # Creates a single compiler worker process.
        transport = await self._create_compiler_process()
        self._worker_transports[transport.get_pid()] = transport
        self._expected_num_workers += 1

    def _maybe_scale_up(self) -> None:
        if not self._running:
            return
        logger.info(
            "A compile request has waited for more than %d seconds, "
            "spawn a new compiler worker process now.",
            ADAPTIVE_SCALE_UP_WAIT_TIME,
        )
        self._loop.create_task(self._create_worker())

    def _scale_down(self) -> None:
        self._scale_down_handle = None
        if not self._running or len(self._workers) <= self._pool_size:
            return
        logger.info(
            "The compiler pool is not used in %d seconds, scaling down to %d.",
            ADAPTIVE_SCALE_DOWN_WAIT_TIME, self._pool_size,
        )
        self._expected_num_workers = self._pool_size
        for worker in sorted(
            self._workers.values(), key=lambda w: w._last_used
        )[:-self._pool_size]:
            worker.close()

    def get_size_hint(self) -> int:
        return self._max_num_workers


class RemoteWorker(BaseWorker):
    _con: amsg.HubConnection
    _secret: bytes

    def __init__(
        self,
        con: amsg.HubConnection,
        secret: bytes,
        *args: Any,
    ) -> None:
        super().__init__(*args)
        self._con = con
        self._secret = secret

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._con.abort()

    async def _request(
        self,
        method_name: str,
        args: tuple[Any, ...],
    ) -> memoryview:
        msg = pickle.dumps((method_name, args))
        digest = hmac.digest(self._secret, msg, "sha256")
        return await self._con.request(digest + msg)


@srvargs.CompilerPoolMode.Remote.assign_implementation
class RemotePool(AbstractPool[RemoteWorker, InitArgs, RemoteInitArgsPickle]):

    _pool_addr: tuple[str, int]
    _worker: Optional[asyncio.Future[RemoteWorker]]
    _sync_lock: asyncio.Lock
    _semaphore: asyncio.BoundedSemaphore
    _pool_size: int
    _secret: bytes

    def __init__(
        self,
        *,
        address: tuple[str, int],
        pool_size: int,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._pool_addr = address
        self._worker = None
        self._sync_lock = asyncio.Lock()
        self._semaphore = asyncio.BoundedSemaphore(pool_size)
        self._pool_size = pool_size
        secret = os.environ.get("_EDGEDB_SERVER_COMPILER_POOL_SECRET")
        if not secret:
            raise AssertionError(
                "_EDGEDB_SERVER_COMPILER_POOL_SECRET environment variable "
                "is not set"
            )
        self._secret = secret.encode()

    async def start(self, *, retry: bool = False) -> None:
        if self._worker is None:
            self._worker = self._loop.create_future()
        try:
            def on_pid(*args: Any) -> None:
                self._loop.create_task(self._connection_made(retry, *args))

            await self._loop.create_connection(
                lambda: amsg.HubProtocol(
                    loop=self._loop,
                    on_pid=on_pid,
                    on_connection_lost=self._connection_lost,
                ),
                *self._pool_addr,
            )
        except Exception:
            if not retry:
                raise
            if self._worker is not None:
                self._loop.call_later(1, lambda: self._loop.create_task(
                    self.start(retry=True)
                ))
        else:
            if not retry:
                await self._worker

    async def stop(self) -> None:
        if self._worker is not None:
            worker, self._worker = self._worker, None
            if worker.done():
                (await worker).close()

    @lru.lru_method_cache(1)
    def _make_cached_init_args(
        self,
        global_schema_pickle: bytes,
        system_config: Config,
    ) -> tuple[InitArgs, RemoteInitArgsPickle]:
        init_args = self._make_init_args(
            global_schema_pickle,
            system_config,
        )
        std_args = (
            self._std_schema, self._refl_schema, self._schema_class_layout
        )
        client_args = (self._backend_runtime_params,)
        return init_args, (
            pickle.dumps(std_args, -1),
            pickle.dumps(client_args, -1),
            global_schema_pickle,
            pickle.dumps(system_config, -1),
        )

    async def _connection_made(
        self,
        retry: bool,
        protocol: amsg.HubProtocol,
        transport: asyncio.Transport,
        _pid: int,
        version: int,
    ) -> None:
        if self._worker is None:
            return
        compiler_protocol = CURRENT_COMPILER_PROTOCOL
        try:
            init_args, init_args_pickled = self._get_init_args()
            worker = RemoteWorker(
                amsg.HubConnection(transport, protocol, self._loop, version),
                self._secret,
                *init_args,
            )
            await worker.call(
                '__init_server__',
                compiler_protocol,
                defines.EDGEDB_CATALOG_VERSION,
                init_args_pickled,
            )
        except state.IncompatibleClient as ex:
            transport.abort()
            if self._worker is not None:
                self._worker.set_exception(ex)
                self._worker = None
        except BaseException as ex:
            transport.abort()
            if self._worker is not None:
                if retry:
                    await self.start(retry=True)
                else:
                    self._worker.set_exception(ex)
                    self._worker = None
        else:
            if self._worker is not None:
                self._worker.set_result(worker)

    def _connection_lost(self, _pid: Optional[int]) -> None:
        if self._worker is not None:
            self._worker = self._loop.create_future()
            self._loop.create_task(self.start(retry=True))

    async def _acquire_worker(self, **compiler_args: Any) -> RemoteWorker:
        start_time = time.monotonic()
        try:
            await self._semaphore.acquire()
            assert self._worker is not None
            rv = await self._worker
        except TimeoutError:
            metrics.compiler_pool_queue_errors.inc(1.0, "timeout")
            raise
        except Exception:
            metrics.compiler_pool_queue_errors.inc(1.0, "ise")
            raise
        else:
            metrics.compiler_pool_wait_time.observe(
                time.monotonic() - start_time
            )
            return rv

    def _release_worker(
        self,
        worker: RemoteWorker,
        *,
        put_in_front: bool = True,
    ) -> None:
        self._semaphore.release()
        self._maybe_update_last_active_time()

    async def compile_in_tx(
        self,
        dbname: str,
        user_schema_pickle: bytes,
        txid: int,
        pickled_state: bytes,
        state_id: int,
        *compile_args: Any,
        **compiler_args: Any,
    ) -> tuple[dbstate.QueryUnitGroup, bytes, int]:
        worker = await self._acquire_worker()
        try:
            return await worker.call(
                'compile_in_tx',
                state_id,
                None,  # client_id
                None,  # dbname
                None,  # user_schema_pickle
                state.REUSE_LAST_STATE_MARKER,
                txid,
                *compile_args
            )
        except state.StateNotFound:
            return await worker.call(
                'compile_in_tx',
                0,  # state_id
                None,  # client_id
                None,  # dbname
                user_schema_pickle,
                pickled_state,
                txid,
                *compile_args
            )
        finally:
            self._release_worker(worker)

    async def _compute_compile_preargs(
        self, *args: Any
    ) -> tuple[PreArgs, Optional[SyncStateCallback], SyncFinalizer]:
        # State sync with the compiler server is serialized with _sync_lock,
        # also blocking any other compile requests that may sync state, so as
        # to avoid inconsistency. Meanwhile, we'd like to avoid locking when
        # sync is not needed (callback is None), so we have 2 fast paths here:
        #
        #   1. When _sync_lock is not held AND sync is not needed here, or
        #   2. after acquiring _sync_lock, we found that sync is not needed.
        #
        # In such cases, we avoid locking or release the lock immediately, so
        # that concurrent compile requests can proceed in parallel.
        preargs: PreArgs = ()
        callback: Optional[SyncStateCallback] = lambda: None
        fini = lambda: None

        if not self._sync_lock.locked():
            # Case 1: check if we need to sync state.
            (
                preargs, callback, fini
            ) = await super()._compute_compile_preargs(*args)

        if callback is not None:
            # Check again with the lock acquired
            del preargs, callback
            await self._sync_lock.acquire()
            (
                preargs, callback, fini
            ) = await super()._compute_compile_preargs(*args)
            if callback:
                # State sync is only considered done when we received a
                # successful response from the compiler server, when we
                # update the local state in the worker in the `callback`
                # function. We should usually release the lock after the
                # `callback`, but we must also release it if anything
                # failed along the way.
                fini = lambda: self._sync_lock.release()
            else:
                # Case 2: no state sync needed, release the lock immediately.
                self._sync_lock.release()
        return preargs, callback, fini

    def get_debug_info(self) -> dict[str, Any]:
        return dict(
            address="{}:{}".format(*self._pool_addr),
            size=self._semaphore._bound_value,  # type: ignore
            free=self._semaphore._value,  # type: ignore
        )

    def get_size_hint(self) -> int:
        return self._pool_size

    async def health_check(self) -> bool:
        if self._worker is None or not self._worker.done():
            return False
        return await super().health_check()


@dataclasses.dataclass
class TenantSchema:
    client_id: int
    dbs: collections.OrderedDict[str, state.PickledDatabaseState]
    global_schema_pickle: bytes
    system_config: Config

    def get_db(self, name: str) -> Optional[state.PickledDatabaseState]:
        rv = self.dbs.get(name)
        if rv is not None:
            self.dbs.move_to_end(name, last=False)
        return rv

    def set_db(self, name: str, db: state.PickledDatabaseState) -> None:
        self.dbs[name] = db
        self.dbs.move_to_end(name, last=False)

    def prepare_evict_db(self, keep: int) -> list[str]:
        return list(self.dbs.keys())[keep:]

    def evict_db(self, name: str) -> None:
        self.dbs.pop(name, None)

    def get_estimated_size(self) -> int:
        return sum(db.get_estimated_size() for db in self.dbs.values())


class PickledState(NamedTuple):
    user_schema: Optional[bytes]
    reflection_cache: Optional[bytes]
    database_config: Optional[bytes]


class PickledSchema(NamedTuple):
    dbs: Optional[immutables.Map[str, PickledState]] = None
    global_schema: Optional[bytes] = None
    instance_config: Optional[bytes] = None
    dropped_dbs: tuple = ()


class BaseMultiTenantWorker[
    TenantStore_T, BaseLocalPool_T: BaseLocalPool
](Worker):

    _manager: BaseLocalPool_T
    _cache: collections.OrderedDict[int, TenantStore_T]
    _invalidated_clients: list[int]
    _last_used_by_client: dict[int, float]
    _client_names: dict[int, str]

    def __init__(
        self,
        manager: BaseLocalPool_T,
        server: amsg.Server,
        pid: int,
        backend_runtime_params: pgparams.BackendRuntimeParams,
        std_schema: s_schema.FlatSchema,
        refl_schema: s_schema.FlatSchema,
        schema_class_layout: s_refl.SchemaClassLayout,
    ):
        super().__init__(
            manager,
            server,
            pid,
            backend_runtime_params,
            std_schema,
            refl_schema,
            schema_class_layout,
            None,
            None,
        )
        self._cache = collections.OrderedDict()
        self._invalidated_clients = []
        self._last_used_by_client = {}
        self._client_names = {}
        self._init()

    def _init(self) -> None:
        pass

    def get_tenant_schema(
        self, client_id: int, *, touch: bool = True
    ) -> Optional[TenantStore_T]:
        rv = self._cache.get(client_id)
        if rv is not None and touch:
            self._cache.move_to_end(client_id, last=False)
        return rv

    def set_tenant_schema(
        self, client_id: int, tenant_schema: TenantStore_T
    ) -> None:
        self._cache[client_id] = tenant_schema
        self._cache.move_to_end(client_id, last=False)
        self._last_used_by_client[client_id] = time.monotonic()

    def cache_size(self) -> int:
        return len(self._cache) - len(self._invalidated_clients)

    def last_used(self, client_id: int) -> float:
        return self._last_used_by_client.get(client_id, 0)

    def flush_invalidation(self) -> list[int]:
        evicted = 0
        pid_str = str(self.get_pid())
        evicted_names = set()

        client_ids, self._invalidated_clients = self._invalidated_clients, []
        for client_id in client_ids:
            if self._cache.pop(client_id, None) is not None:
                evicted += 1
            self._last_used_by_client.pop(client_id, None)

            client_name = self._client_names.pop(client_id, None)
            if client_name is not None:
                evicted_names.add(client_name)

        if evicted:
            metrics.compiler_process_client_actions.inc(
                evicted, pid_str, 'cache-evict'
            )
        if evicted_names:
            def tag_filter(pid: str, client: str, *remaining_tags) -> bool:
                return pid == pid_str and client in evicted_names

            metrics.compiler_process_schema_size.clear(tag_filter)
            metrics.compiler_process_branches.clear(tag_filter)
            metrics.compiler_process_branch_actions.clear(tag_filter)

        return client_ids

    def set_client_name(self, client_id: int, name: Optional[str]) -> None:
        if client_id not in self._client_names:
            self._client_names[client_id] = name or f'unknown-{client_id}'

    def get_client_name(self, client_id: int) -> str:
        return self._client_names.get(client_id) or f'unknown-{client_id}'


class MultiTenantWorker(
    BaseMultiTenantWorker[TenantSchema, "MultiTenantPool"]
):

    current_client_id: Optional[int]

    def _init(self) -> None:
        self.current_client_id = None

    def invalidate(self, client_id: int) -> None:
        if client_id in self._cache:
            self._invalidated_clients.append(client_id)

    def maybe_invalidate_last(self) -> None:
        if self.cache_size() == self._manager.cache_size:
            client_id = next(reversed(self._cache))
            self._invalidated_clients.append(client_id)

    def get_invalidation(self) -> list[int]:
        return self._invalidated_clients[:]


@srvargs.CompilerPoolMode.MultiTenant.assign_implementation
class MultiTenantPool(FixedPoolImpl[MultiTenantWorker, MultiTenantInitArgs]):
    _worker_class = MultiTenantWorker
    _worker_mod = "multitenant_worker"

    def __init__(self, *, cache_size: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._cache_size = cache_size

    @property
    def cache_size(self) -> int:
        return self._cache_size

    def drop_tenant(self, client_id: int) -> None:
        for worker in self._workers.values():
            worker.invalidate(client_id)

    @lru.method_cache
    def _get_init_args(self) -> tuple[MultiTenantInitArgs, bytes]:
        init_args = (
            self._backend_runtime_params,
            self._std_schema,
            self._refl_schema,
            self._schema_class_layout,
        )
        return init_args, pickle.dumps(init_args, -1)

    def _weighter(
        self,
        client_id: int,
        worker: MultiTenantWorker,
    ) -> queue.Comparable:
        tenant_schema = worker.get_tenant_schema(client_id, touch=False)
        return (
            bool(tenant_schema),
            worker.last_used(client_id)
            if tenant_schema
            else self._cache_size - worker.cache_size(),
        )

    async def _acquire_worker(
        self,
        *,
        condition: Optional[queue.AcquireCondition[MultiTenantWorker]] = None,
        weighter: Optional[queue.Weighter[MultiTenantWorker]] = None,
        **compiler_args: Any
    ) -> MultiTenantWorker:
        client_id: Optional[int] = compiler_args.get("client_id")
        if weighter is None and client_id is not None:
            weighter = functools.partial(self._weighter, client_id)
        rv = await super()._acquire_worker(
            condition=condition, weighter=weighter, **compiler_args
        )
        rv.current_client_id = client_id
        if client_id is not None:
            rv.set_client_name(client_id, compiler_args.get("client_name"))
        return rv

    def _release_worker(
        self,
        worker: MultiTenantWorker,
        *,
        put_in_front: bool = True,
    ) -> None:
        worker.current_client_id = None
        super()._release_worker(worker, put_in_front=put_in_front)

    async def _compute_compile_preargs(
        self,
        method_name: str,
        worker: MultiTenantWorker,
        dbname: str,
        user_schema_pickle: bytes,
        global_schema_pickle: bytes,
        reflection_cache: state.ReflectionCache,
        database_config: Config,
        system_config: Config,
    ) -> tuple[PreArgs, Optional[SyncStateCallback], SyncFinalizer]:
        assert isinstance(worker, MultiTenantWorker)

        def sync_worker_state_cb(
            *,
            worker: MultiTenantWorker,
            client_id: int,
            client_name: str,
            dbname: str,
            evicted_dbs: list[str],
            user_schema_pickle: Optional[bytes] = None,
            global_schema_pickle: Optional[bytes] = None,
            reflection_cache: Optional[state.ReflectionCache] = None,
            database_config: Optional[Config] = None,
            instance_config: Optional[Config] = None,
        ) -> None:
            pid = str(worker.get_pid())
            tenant_schema = worker.get_tenant_schema(client_id)
            if tenant_schema is None:
                assert user_schema_pickle is not None
                assert reflection_cache is not None
                assert global_schema_pickle is not None
                assert database_config is not None
                assert instance_config is not None
                assert len(evicted_dbs) == 0

                tenant_schema = TenantSchema(
                    client_id,
                    collections.OrderedDict(
                        {
                            dbname: state.PickledDatabaseState(
                                user_schema_pickle,
                                reflection_cache,
                                database_config,
                            ),
                        }
                    ),
                    global_schema_pickle,
                    instance_config,
                )
                worker.set_tenant_schema(client_id, tenant_schema)

                metrics.compiler_process_branch_actions.inc(
                    1, pid, client_name, 'cache-add'
                )
                metrics.compiler_process_client_actions.inc(
                    1, pid, 'cache-add'
                )

            else:
                for name in evicted_dbs:
                    tenant_schema.evict_db(name)
                if evicted_dbs:
                    metrics.compiler_process_branch_actions.inc(
                        len(evicted_dbs), pid, client_name, 'cache-evict'
                    )

                worker_db = tenant_schema.get_db(dbname)
                if worker_db is None:
                    assert user_schema_pickle is not None
                    assert reflection_cache is not None
                    assert database_config is not None

                    tenant_schema.set_db(
                        dbname,
                        state.PickledDatabaseState(
                            user_schema_pickle=user_schema_pickle,
                            reflection_cache=reflection_cache,
                            database_config=database_config,
                        ),
                    )
                    metrics.compiler_process_branch_actions.inc(
                        1, pid, client_name, 'cache-add'
                    )
                    metrics.compiler_process_client_actions.inc(
                        1, pid, 'cache-update'
                    )

                elif (
                    user_schema_pickle is not None
                    or reflection_cache is not None
                    or database_config is not None
                ):
                    tenant_schema.set_db(
                        dbname,
                        state.PickledDatabaseState(
                            user_schema_pickle=(
                                user_schema_pickle
                                or worker_db.user_schema_pickle
                            ),
                            reflection_cache=(
                                reflection_cache or worker_db.reflection_cache
                            ),
                            database_config=(
                                database_config or worker_db.database_config
                            ),
                        )
                    )
                    metrics.compiler_process_branch_actions.inc(
                        1, pid, client_name, 'cache-update'
                    )
                    metrics.compiler_process_client_actions.inc(
                        1, pid, 'cache-update'
                    )

                if global_schema_pickle is not None:
                    tenant_schema.global_schema_pickle = global_schema_pickle
                if instance_config is not None:
                    tenant_schema.system_config = instance_config

            worker.flush_invalidation()

            metrics.compiler_process_schema_size.set(
                tenant_schema.get_estimated_size(), pid, client_name
            )
            metrics.compiler_process_branches.set(
                len(tenant_schema.dbs), pid, client_name
            )

        client_id = worker.current_client_id
        assert client_id is not None
        client_name = worker.get_client_name(client_id)
        tenant_schema = worker.get_tenant_schema(client_id, touch=False)
        to_update: dict[str, Hashable]
        evicted_dbs = []
        branch_cache_hit = True
        if tenant_schema is None:
            branch_cache_hit = False
            # make room for the new client in this worker
            worker.maybe_invalidate_last()
            to_update = {
                "user_schema_pickle": user_schema_pickle,
                "reflection_cache": reflection_cache,
                "global_schema_pickle": global_schema_pickle,
                "database_config": database_config,
                "instance_config": system_config,
            }
        else:
            worker_db = tenant_schema.get_db(dbname)
            if worker_db is None:
                branch_cache_hit = False
                evicted_dbs = tenant_schema.prepare_evict_db(
                    self._worker_branch_limit - 1
                )
                to_update = {
                    "user_schema_pickle": user_schema_pickle,
                    "reflection_cache": reflection_cache,
                    "database_config": database_config,
                }
            else:
                to_update = {}
                if worker_db.user_schema_pickle is not user_schema_pickle:
                    branch_cache_hit = False
                    to_update["user_schema_pickle"] = user_schema_pickle
                if worker_db.reflection_cache is not reflection_cache:
                    branch_cache_hit = False
                    to_update["reflection_cache"] = reflection_cache
                if worker_db.database_config is not database_config:
                    branch_cache_hit = False
                    to_update["database_config"] = database_config
            if (
                tenant_schema.global_schema_pickle
                is not global_schema_pickle
            ):
                to_update["global_schema_pickle"] = global_schema_pickle
            if tenant_schema.system_config is not system_config:
                to_update["instance_config"] = system_config

        self._report_branch_request(worker, branch_cache_hit, client_name)

        if to_update:
            pickled = {
                k.removesuffix("_pickle"): v
                if k.endswith("_pickle")
                else _pickle_memoized(v)
                for k, v in to_update.items()
            }
            if any(f in pickled for f in PickledState._fields):
                db_state = PickledState(
                    **{
                        f: pickled.pop(f, None)
                        for f in PickledState._fields
                    }  # type: ignore
                )
                pickled["dbs"] = immutables.Map([(dbname, db_state)])
            pickled_schema = PickledSchema(
                dropped_dbs=tuple(evicted_dbs), **pickled  # type: ignore
            )
            callback = functools.partial(
                sync_worker_state_cb,
                worker=worker,
                client_id=client_id,
                client_name=client_name,
                dbname=dbname,
                evicted_dbs=evicted_dbs,
                **to_update,  # type: ignore
            )
        else:
            pickled_schema = None
            callback = None
            metrics.compiler_process_client_actions.inc(
                1, str(worker.get_pid()), 'cache-hit'
            )

        return (
            "call_for_client",
            client_id,
            pickled_schema,
            worker.get_invalidation(),
            None,  # forwarded msg is only used in remote compiler server
            method_name,
            dbname,
        ), callback, lambda: None

    async def compile_in_tx(
        self,
        dbname: str,
        user_schema_pickle: bytes,
        txid: int,
        pickled_state: bytes,
        state_id: int,
        *compile_args: Any,
        **compiler_args: Any,
    ) -> tuple[dbstate.QueryUnitGroup, bytes, int]:
        client_id: int = compiler_args["client_id"]

        # Prefer a worker we used last time in the transaction (condition), or
        # (weighter) one with the user schema at tx start so that we can pass
        # over only the pickled state. Then prefer the least-recently used one
        # if many workers passed any check in the weighter, or the most vacant.
        def weighter(w: MultiTenantWorker) -> queue.Comparable:
            if ts := w.get_tenant_schema(client_id, touch=False):
                # Don't use ts.get_db() here to avoid confusing the LRU queue
                if db := ts.dbs.get(dbname):
                    return (
                        True,
                        db.user_schema_pickle is user_schema_pickle,
                        w.last_used(client_id),
                    )
                else:
                    return True, False, w.last_used(client_id)
            else:
                return False, False, self._cache_size - w.cache_size()

        worker = await self._acquire_worker(
            condition=lambda w: (w._last_pickled_state is pickled_state),
            weighter=cast(queue.Weighter, weighter),
            **compiler_args,
        )

        # Avoid sending information that we know the worker already have.
        dbname_arg = None
        client_id_arg = None
        user_schema_pickle_arg = None

        if worker._last_pickled_state is pickled_state:
            pickled_state = state.REUSE_LAST_STATE_MARKER
        else:
            tenant_schema = worker.get_tenant_schema(client_id)
            if tenant_schema is None:
                # Just pass state + root user schema if this is a new client in
                # the worker; we don't want to initialize the client as we
                # don't have enough information to do so.
                user_schema_pickle_arg = user_schema_pickle
            else:
                # Don't use ts.get_db() here to avoid confusing the LRU queue
                worker_db = tenant_schema.dbs.get(dbname)
                if worker_db is None:
                    # The worker has the client but not the database
                    user_schema_pickle_arg = user_schema_pickle
                elif worker_db.user_schema_pickle is user_schema_pickle:
                    # Avoid sending the root user schema because the worker has
                    # it - just send client_id + dbname to reference it, as
                    # well as the state of course.
                    dbname_arg = dbname
                    client_id_arg = client_id
                    # Touch dbname to bump it in the LRU queue
                    tenant_schema.get_db(dbname)
                else:
                    # The worker has a different root user schema
                    user_schema_pickle_arg = user_schema_pickle

        try:
            units, new_pickled_state = await worker.call(
                'compile_in_tx',
                # multitenant_worker is also used in MultiSchemaPool for remote
                # compilers where the first argument "state_id" is used to find
                # worker without passing the pickled state. Here in multi-
                # tenant mode, we already have the pickled state, so "state_id"
                # is not used. Just prepend a fake ID to comply to the API.
                0,  # state_id
                client_id_arg,
                dbname_arg,
                user_schema_pickle_arg,
                pickled_state,
                txid,
                *compile_args
            )
            worker._last_pickled_state = new_pickled_state
            return units, new_pickled_state, 0

        finally:
            self._release_worker(worker, put_in_front=False)


async def create_compiler_pool[AbstractPool_T: AbstractPool](
    *,
    runstate_dir: str,
    pool_size: int,
    worker_branch_limit: int,
    backend_runtime_params: pgparams.BackendRuntimeParams,
    std_schema: s_schema.FlatSchema,
    refl_schema: s_schema.FlatSchema,
    schema_class_layout: s_refl.SchemaClassLayout,
    pool_class: type[AbstractPool_T],
    **kwargs: Any,
) -> AbstractPool_T:
    assert issubclass(pool_class, AbstractPool)
    loop = asyncio.get_running_loop()
    pool = pool_class(
        loop=loop,
        pool_size=pool_size,
        worker_branch_limit=worker_branch_limit,
        runstate_dir=runstate_dir,
        backend_runtime_params=backend_runtime_params,
        std_schema=std_schema,
        refl_schema=refl_schema,
        schema_class_layout=schema_class_layout,
        **kwargs,
    )

    await pool.start()
    return pool
