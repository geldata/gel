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
from typing import Any, Callable, cast, NamedTuple, Optional, Sequence

import asyncio
import hmac
import functools
import logging
import os
import pathlib
import pickle
import secrets
import tempfile
import traceback

import click
import httptools
import immutables

from edb.common import debug
from edb.common import lru
from edb.common import markup
from edb.server import metrics
from edb.server import args as srvargs
from edb.server import defines
from edb.server import logsetup

from . import amsg
from . import pool as pool_mod
from . import queue
from . import worker_proc
from . import state as state_mod


_client_id_seq = 0
_tx_state_id_seq = 0
logger = logging.getLogger("edb.server")


def next_tx_state_id():
    global _tx_state_id_seq
    _tx_state_id_seq = (_tx_state_id_seq + 1) % (2 ** 63 - 1)
    return _tx_state_id_seq


class PickledState(NamedTuple):
    user_schema: Optional[bytes]
    reflection_cache: Optional[bytes]
    database_config: Optional[bytes]

    def diff(self, other: PickledState):
        # Compare this state with the other state, generate a new state with
        # fields from this state which are different in the other state, while
        # the identical fields are left None, so that we can send the minimum
        # diff to the worker to update the changed fields only.
        user_schema = reflection_cache = database_config = None
        if self.user_schema is not other.user_schema:
            user_schema = self.user_schema
        if self.reflection_cache is not other.reflection_cache:
            reflection_cache = self.reflection_cache
        if self.database_config is not other.database_config:
            database_config = self.database_config
        return PickledState(user_schema, reflection_cache, database_config)

    def get_estimated_size(self) -> int:
        rv = 0
        if self.user_schema is not None:
            rv += len(self.user_schema)
        if self.reflection_cache is not None:
            rv += len(self.reflection_cache)
        if self.database_config is not None:
            rv += len(self.database_config)
        return rv


class ClientSchema(NamedTuple):
    dbs: immutables.Map[str, PickledState]
    global_schema: Optional[bytes]
    instance_config: Optional[bytes]
    dropped_dbs: tuple

    def diff(self, other: ClientSchema) -> tuple[ClientSchema, int, int]:
        # Compare this schema with the other schema, generate a new schema with
        # fields from this schema which are different in the other schema,
        # while the identical fields are left None, so that we can send the
        # minimum diff to the worker to update the changed fields only.
        # NOTE: this is a deep diff that compares all children fields.
        dropped_dbs = tuple(
            dbname for dbname in other.dbs if dbname not in self.dbs
        )
        added = 0
        updated = 0
        dbs: immutables.Map[str, PickledState] = immutables.Map()
        for dbname, state in self.dbs.items():
            other_state = other.dbs.get(dbname)
            if other_state is None:
                dbs = dbs.set(dbname, state)
                added += 1
            elif state is not other_state:
                dbs = dbs.set(dbname, state.diff(other_state))
                updated += 1
        global_schema = instance_config = None
        if self.global_schema is not other.global_schema:
            global_schema = self.global_schema
        if self.instance_config is not other.instance_config:
            instance_config = self.instance_config
        return (
            ClientSchema(dbs, global_schema, instance_config, dropped_dbs),
            added,
            updated,
        )

    def get_estimated_size(self) -> int:
        return sum(db.get_estimated_size() for db in self.dbs.values())


class Worker(pool_mod.BaseMultiTenantWorker[ClientSchema, "MultiSchemaPool"]):

    _last_pickled_state_id: int

    def _init(self) -> None:
        self._last_pickled_state_id = 0

    def invalidate(self, client_id: int) -> None:
        if self._cache.pop(client_id, None):
            self._invalidated_clients.append(client_id)
        self._last_used_by_client.pop(client_id, None)

    def invalidate_last(self, cache_size: int) -> None:
        if len(self._cache) == cache_size:
            client_id, _ = self._cache.popitem(last=True)
            self._invalidated_clients.append(client_id)
            self._last_used_by_client.pop(client_id, None)

    async def call(
        self,
        method_name: str,
        *args: Any,
        sync_state: Optional[pool_mod.SyncStateCallback] = None,
        msg: Optional[bytes] = None,
    ) -> Any:
        assert not self._closed
        assert self._con is not None

        if self._con.is_closed():
            raise RuntimeError(
                "the connection to the compiler worker process is "
                "unexpectedly closed"
            )

        if msg is None:
            msg = pickle.dumps((method_name, args))
        return await self._con.request(msg)


class MultiSchemaPool(
    pool_mod.FixedPoolImpl[Worker, pool_mod.MultiTenantInitArgs]
):
    _worker_class = Worker
    _worker_mod = "multitenant_worker"
    _workers: dict[int, Worker]  # type: ignore

    _catalog_version: Optional[int]
    _inited: asyncio.Event
    _clients: dict[int, ClientSchema]
    _client_names: dict[int, str]
    _secret: bytes

    def __init__(self, cache_size, *, secret, **kwargs):
        super().__init__(**kwargs)
        self._catalog_version = None
        self._inited = asyncio.Event()
        self._cache_size = cache_size
        self._clients = {}
        self._client_names = {}
        self._secret = secret

    def _init(self, kwargs: dict[str, Any]) -> None:
        # this is deferred to _init_server()
        pass

    @lru.method_cache
    def _get_init_args(self) -> tuple[pool_mod.MultiTenantInitArgs, bytes]:
        init_args = (
            self._backend_runtime_params,
            self._std_schema,
            self._refl_schema,
            self._schema_class_layout,
        )
        return init_args, pickle.dumps(init_args, -1)

    async def _attach_worker(self, pid: int) -> Optional[Worker]:
        if not self._running:
            return None
        if not self._inited.is_set():
            await self._inited.wait()
        return await super()._attach_worker(pid)

    async def _wait_ready(self) -> None:
        pass

    async def _init_server(
        self,
        client_id: int,
        client_name: str,
        compiler_protocol: int,
        catalog_version: int,
        init_args_pickled: pool_mod.RemoteInitArgsPickle,
    ) -> None:
        if compiler_protocol > pool_mod.CURRENT_COMPILER_PROTOCOL:
            raise state_mod.IncompatibleClient("compiler_protocol")

        (
            std_args_pickled,
            client_args_pickled,
            global_schema_pickle,
            system_config_pickled,
        ) = init_args_pickled
        backend_runtime_params, = pickle.loads(client_args_pickled)
        if self._inited.is_set():
            logger.debug("New client %d connected.", client_id)
            assert self._catalog_version is not None
            if self._catalog_version != catalog_version:
                raise state_mod.IncompatibleClient("catalog_version")
            if self._backend_runtime_params != backend_runtime_params:
                raise state_mod.IncompatibleClient("backend_runtime_params")
        else:
            (
                self._std_schema,
                self._refl_schema,
                self._schema_class_layout,
            ) = pickle.loads(std_args_pickled)
            self._backend_runtime_params = backend_runtime_params
            assert self._catalog_version is None
            self._catalog_version = catalog_version
            self._inited.set()
            logger.info(
                "New client %d connected, compiler server initialized.",
                client_id,
            )
        self._clients[client_id] = ClientSchema(
            dbs=immutables.Map(),
            global_schema=global_schema_pickle,
            instance_config=system_config_pickled,
            dropped_dbs=(),
        )
        self._client_names[client_id] = client_name

    def _sync(
        self,
        *,
        client_id: int,
        dbname: str,
        evicted_dbs: list[str],
        user_schema: Optional[bytes],
        reflection_cache: Optional[bytes],
        global_schema: Optional[bytes],
        database_config: Optional[bytes],
        system_config: Optional[bytes],
    ) -> bool:
        """Sync the client state in the compiler server.

        The client state is carried over with the compile(), compile_sql(),
        compile_notebook(), compile_graphql() calls.

        Returns True if the client state changed, False otherwise.
        """
        # EdgeDB instance syncs the schema with the compiler server
        client = self._clients[client_id]
        client_updates: dict[str, Any] = {}
        dbs = client.dbs.mutate()
        dbs_changed = False
        if evicted_dbs:
            for name in evicted_dbs:
                if dbs.pop(name, None) is not None:
                    dbs_changed = True

        db = dbs.get(dbname)
        if db is None:
            assert user_schema is not None
            assert reflection_cache is not None
            assert database_config is not None
            dbs[dbname] = PickledState(
                user_schema, reflection_cache, database_config
            )
            dbs_changed = True
        else:
            updates = {}

            if user_schema is not None:
                updates["user_schema"] = user_schema
            if reflection_cache is not None:
                updates["reflection_cache"] = reflection_cache
            if database_config is not None:
                updates["database_config"] = database_config

            if updates:
                db = db._replace(**updates)
                dbs[dbname] = db
                dbs_changed = True

        if global_schema is not None:
            client_updates["global_schema"] = global_schema

        if system_config is not None:
            client_updates["instance_config"] = system_config

        if dbs_changed:
            client_updates["dbs"] = dbs.finish()

        if client_updates:
            self._clients[client_id] = client._replace(**client_updates)
            return True
        else:
            return False

    def _weighter(self, client_id: int, worker: Worker) -> queue.Comparable:
        client_schema = worker.get_tenant_schema(client_id, touch=False)
        return (
            bool(client_schema),
            worker.last_used(client_id)
            if client_schema
            else self._cache_size - worker.cache_size(),
        )

    async def _call_for_client(
        self,
        *,
        client_id: int,
        method_name: str,
        dbname: str,
        evicted_dbs: list[str],
        user_schema: Optional[bytes],
        reflection_cache: Optional[bytes],
        global_schema: Optional[bytes],
        database_config: Optional[bytes],
        system_config: Optional[bytes],
        args: tuple[Any, ...],
        msg: memoryview,
    ) -> Any:
        try:
            updated = self._sync(
                client_id=client_id,
                dbname=dbname,
                evicted_dbs=evicted_dbs,
                user_schema=user_schema,
                reflection_cache=reflection_cache,
                global_schema=global_schema,
                database_config=database_config,
                system_config=system_config,
            )
        except Exception as ex:
            raise state_mod.FailedStateSync(
                f"failed to sync compiler server state: "
                f"{type(ex).__name__}({ex})"
            ) from ex
        worker = await self._acquire_worker(
            weighter=functools.partial(self._weighter, client_id)
        )
        try:
            pid = str(worker.get_pid())
            client_schema = self._clients[client_id]
            client_name = self._client_names[client_id]
            worker.set_client_name(client_id, client_name)
            diff: Optional[ClientSchema] = client_schema
            cache = worker.get_tenant_schema(client_id)
            extra_args: tuple[Any, ...] = ()
            metrics.compiler_process_branch_actions.inc(
                1, pid, client_name, 'request'
            )
            if cache is client_schema:
                # client schema is already in sync, don't send again
                diff = None
                msg_arg = bytes(msg)
                metrics.compiler_process_client_actions.inc(
                    1, pid, 'cache-hit'
                )
                metrics.compiler_process_branch_actions.inc(
                    1, pid, client_name, 'cache-hit'
                )

            else:
                metrics.compiler_process_schema_size.set(
                    client_schema.get_estimated_size(), pid, client_name
                )
                metrics.compiler_process_branches.set(
                    len(client_schema.dbs), pid, client_name
                )

                if cache is None:
                    # make room for the new client in this worker
                    worker.invalidate_last(self._cache_size)
                    metrics.compiler_process_branch_actions.inc(
                        len(client_schema.dbs), pid, client_name, 'cache-add'
                    )
                    metrics.compiler_process_client_actions.inc(
                        1, pid, 'cache-add'
                    )

                else:
                    # only send the difference in user schema
                    diff, dbs_added, dbs_updated = client_schema.diff(cache)
                    if dbname not in diff.dbs:
                        metrics.compiler_process_branch_actions.inc(
                            1, pid, client_name, 'cache-hit'
                        )
                    if dbs_added:
                        metrics.compiler_process_branch_actions.inc(
                            dbs_added, pid, client_name, 'cache-add'
                        )
                    if dbs_updated:
                        metrics.compiler_process_branch_actions.inc(
                            dbs_updated, pid, client_name, 'cache-update'
                        )
                    if diff.dropped_dbs:
                        metrics.compiler_process_branch_actions.inc(
                            len(diff.dropped_dbs),
                            pid,
                            client_name,
                            'cache-evict',
                        )
                    metrics.compiler_process_client_actions.inc(
                        1, pid, 'cache-update'
                    )

                if updated:
                    # re-pickle the request if user schema changed
                    msg_arg = None
                    extra_args = (method_name, dbname, *args)
                else:
                    msg_arg = bytes(msg)
            invalidation = worker.flush_invalidation()
            resp = await worker.call(
                "call_for_client",
                client_id,
                diff,
                invalidation,
                msg_arg,
                *extra_args,
            )
            status, *data = pickle.loads(resp)
            if status == 0:
                worker.set_tenant_schema(client_id, client_schema)
                if method_name == "compile":
                    _units, new_pickled_state = data[0]
                    if new_pickled_state:
                        sid = next_tx_state_id()
                        worker._last_pickled_state_id = sid
                        resp = pickle.dumps((0, (*data[0], sid)), -1)
            elif status == 1:
                exc, _tb = data
                if not isinstance(exc, state_mod.FailedStateSync):
                    worker.set_tenant_schema(client_id, client_schema)
            else:
                exc = RuntimeError(
                    "could not serialize result in worker subprocess"
                )
                exc.__formatted_error__ = data[0]
                raise exc

            return resp
        finally:
            self._release_worker(worker)

    async def compile_in_tx_(
        self,
        state_id: int,
        client_id: Optional[int],
        dbname: Optional[str],
        user_schema_pickle: Optional[bytes],
        pickled_state: bytes,
        txid: int,
        *compile_args: Any,
        msg: bytes,
    ):
        if pickled_state == state_mod.REUSE_LAST_STATE_MARKER:
            worker = await self._acquire_worker(
                condition=lambda w: (w._last_pickled_state_id == state_id)
            )
            if worker._last_pickled_state_id != state_id:
                self._release_worker(worker)
                raise state_mod.StateNotFound()
        else:
            worker = await self._acquire_worker()
        try:
            resp = await worker.call(
                "compile_in_tx",
                state_id,
                client_id,
                dbname,
                user_schema_pickle,
                pickled_state,
                txid,
                *compile_args,
                msg=msg,
            )
            status, *data = pickle.loads(resp)
            if status == 0:
                state_id = worker._last_pickled_state_id = next_tx_state_id()
                resp = pickle.dumps((0, (*data[0], state_id)), -1)
            return resp
        finally:
            self._release_worker(worker, put_in_front=False)

    async def _request(self, method_name: str, msg: bytes) -> Any:
        worker = await self._acquire_worker()
        try:
            return await worker.call(method_name, msg=msg)
        finally:
            self._release_worker(worker)

    async def handle_client_call(
        self,
        protocol: CompilerServerProtocol,
        req_id: int,
        msg: memoryview,
    ) -> None:
        client_id = protocol.client_id
        digest = msg[:32]
        msg = msg[32:]
        try:
            expected_digest = hmac.digest(self._secret, msg, "sha256")
            if not hmac.compare_digest(digest, expected_digest):
                raise AssertionError("message signature verification failed")

            method_name, args = pickle.loads(msg)
            if method_name != "__init_server__":
                await self._ready_evt.wait()
            if method_name == "__init_server__":
                await self._init_server(client_id, protocol.client_name, *args)
                pickled = pickle.dumps((0, None), -1)
            elif method_name in {
                "compile",
                "compile_notebook",
                "compile_graphql",
                "compile_sql",
            }:
                (
                    dbname,
                    evicted_dbs,
                    user_schema,
                    reflection_cache,
                    global_schema,
                    database_config,
                    system_config,
                    *args,
                ) = args
                pickled = await self._call_for_client(
                    client_id=client_id,
                    method_name=method_name,
                    dbname=dbname,
                    evicted_dbs=evicted_dbs,
                    user_schema=user_schema,
                    reflection_cache=reflection_cache,
                    global_schema=global_schema,
                    database_config=database_config,
                    system_config=system_config,
                    args=args,
                    msg=msg,
                )
            elif method_name == "compile_in_tx":
                pickled = await self.compile_in_tx_(*args, msg=bytes(msg))
            else:
                pickled = await self._request(method_name, bytes(msg))
        except Exception as ex:
            worker_proc.prepare_exception(ex)
            if debug.flags.server and not isinstance(
                ex, state_mod.StateNotFound
            ):
                markup.dump(ex)
            data = (1, ex, traceback.format_exc())
            try:
                pickled = pickle.dumps(data, -1)
            except Exception as ex:
                ex_tb = traceback.format_exc()
                ex_str = f"{ex}:\n\n{ex_tb}"
                pickled = pickle.dumps((2, ex_str), -1)
        protocol.reply(req_id, pickled)

    def client_disconnected(self, client_id: int) -> None:
        logger.debug("Client %d disconnected, invalidating cache.", client_id)
        self._clients.pop(client_id, None)
        self._client_names.pop(client_id, None)
        for worker in self._workers.values():
            worker.invalidate(client_id)


class CompilerServerProtocol(asyncio.Protocol):
    _pool: MultiSchemaPool
    _loop: asyncio.AbstractEventLoop
    _stream: amsg.MessageStream
    _transport: Optional[asyncio.Transport]
    _client_id: int
    _client_name: str

    def __init__(
        self,
        pool: MultiSchemaPool,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        global _client_id_seq
        self._pool = pool
        self._loop = loop
        self._stream = amsg.MessageStream()
        self._transport = None
        self._client_id = _client_id_seq = _client_id_seq + 1
        self._client_name = 'unknown'

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = cast(asyncio.Transport, transport)
        self._transport.write(
            amsg._uint64_packer(os.getpid()) + amsg._uint64_packer(0)
        )
        peername = transport.get_extra_info('peername')
        try:
            self._client_name = '%s:%d' % peername
        except Exception:
            self._client_name = str(peername)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self._transport = None
        self._pool.client_disconnected(self._client_id)

    def data_received(self, data: bytes) -> None:
        for msg in self._stream.feed_data(data):
            msgview = memoryview(msg)
            req_id = amsg._uint64_unpacker(msgview[:8])[0]
            self._loop.create_task(
                self._pool.handle_client_call(self, req_id, msgview[8:])
            )

    @property
    def client_id(self) -> int:
        return self._client_id

    @property
    def client_name(self) -> str:
        return self._client_name

    def reply(self, req_id: int, resp: bytes) -> None:
        if self._transport is None:
            return
        self._transport.write(
            b"".join(
                (
                    amsg._uint64_packer(len(resp) + 8),
                    amsg._uint64_packer(req_id),
                    resp,
                )
            )
        )


class MetricsProtocol(asyncio.Protocol):
    _pool: MultiSchemaPool
    transport: Optional[asyncio.Transport]
    parser: httptools.HttpRequestParser
    url: Optional[bytes]

    def __init__(self, pool: MultiSchemaPool) -> None:
        self._pool = pool
        self.transport = None
        self.parser = httptools.HttpRequestParser(self)
        self.url = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.Transport, transport)

    def data_received(self, data: bytes) -> None:
        try:
            self.parser.feed_data(data)
        except Exception as ex:
            logger.exception(ex)

    def on_url(self, url: bytes) -> None:
        self.url = url

    def on_message_complete(self) -> None:
        match self.parser.get_method().upper(), self.url:
            case b"GET", b"/ready":
                self.respond("200 OK", "OK")

            case b"GET", b"/metrics":
                self._pool.refresh_metrics()
                self.respond(
                    "200 OK",
                    metrics.registry.generate(),
                    "Content-Type: text/plain; version=0.0.4; charset=utf-8",
                )

            case _:
                self.respond("404 Not Found", "Not Found")

    def respond(
        self,
        status: str,
        content: str,
        *extra_headers: str,
        encoding: str = "utf-8",
    ) -> None:
        content_bytes = content.encode(encoding)
        response = [
            f"HTTP/{self.parser.get_http_version()} {status}",
            f"Content-Length: {len(content_bytes)}",
            *extra_headers,
            "",
            "",
        ]

        assert self.transport is not None
        self.transport.write("\r\n".join(response).encode("ascii"))
        self.transport.write(content_bytes)
        if not self.parser.should_keep_alive():
            self.transport.close()


async def server_main(
    listen_addresses: Sequence[str],
    listen_port: Optional[int],
    pool_size: int,
    client_schema_cache_size: int,
    runstate_dir: Optional[str | pathlib.Path],
    metrics_port: Optional[int],
    worker_max_rss: Optional[int],
):
    logsetup.setup_logging('i', 'stderr')
    if listen_port is None:
        listen_port = defines.EDGEDB_REMOTE_COMPILER_PORT
    if runstate_dir is None:
        temp_runstate_dir = tempfile.TemporaryDirectory(prefix='edbcompiler-')
        runstate_dir = temp_runstate_dir.name
        logger.debug("Using temporary runstate dir: %s", runstate_dir)
    else:
        temp_runstate_dir = None
        runstate_dir = str(runstate_dir)

    secret = os.environ.get("_EDGEDB_SERVER_COMPILER_POOL_SECRET")
    if not secret:
        logger.warning(
            "_EDGEDB_SERVER_COMPILER_POOL_SECRET is not set, "
            f"compilation requests will fail")
        secret = secrets.token_urlsafe()

    try:
        loop = asyncio.get_running_loop()
        pool = MultiSchemaPool(
            loop=loop,
            runstate_dir=runstate_dir,
            pool_size=pool_size,
            worker_branch_limit=0,  # compiler server doesn't use this limit
            cache_size=client_schema_cache_size,
            secret=secret.encode(),
            worker_max_rss=worker_max_rss,
        )
        await pool.start()
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(
                    _run_server(
                        loop,
                        listen_addresses,
                        listen_port,
                        lambda: CompilerServerProtocol(pool, loop),
                        "compile",
                    )
                )
                if metrics_port:
                    tg.create_task(
                        _run_server(
                            loop,
                            listen_addresses,
                            metrics_port,
                            lambda: MetricsProtocol(pool),
                            "metrics",
                        )
                    )
        finally:
            await pool.stop()
    finally:
        if temp_runstate_dir is not None:
            temp_runstate_dir.cleanup()


async def _run_server(
    loop: asyncio.AbstractEventLoop,
    listen_addresses: Sequence[str],
    listen_port: int,
    protocol: Callable[[], asyncio.Protocol],
    purpose: str,
) -> None:
    server = await loop.create_server(
        protocol,
        listen_addresses,
        listen_port,
        start_serving=False,
    )
    if len(listen_addresses) == 1:
        logger.info(
            "Listening for %s on %s:%s",
            purpose,
            listen_addresses[0],
            listen_port,
        )
    else:
        logger.info(
            "Listening for %s on [%s]:%s",
            purpose,
            ",".join(listen_addresses),
            listen_port,
        )
    try:
        await server.serve_forever()
    finally:
        server.close()
        await server.wait_closed()


@click.command()
@srvargs.compiler_options
def main(**kwargs: Any) -> None:
    asyncio.run(server_main(**kwargs))


if __name__ == "__main__":
    main()
