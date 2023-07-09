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
from typing import *

import asyncio
import collections
import contextlib
import ipaddress
import json
import logging
import os
import pickle
import socket
import ssl
import stat
import time
import uuid
import weakref

import immutables
from jwcrypto import jwk

from edb import buildmeta
from edb import errors

from edb.common import devmode
from edb.common import secretkey
from edb.common import taskgroup
from edb.common import windowedsum

from edb.schema import reflection as s_refl
from edb.schema import schema as s_schema

from edb.server import args as srvargs
from edb.server import cache
from edb.server import config
from edb.server import compiler_pool
from edb.server import defines
from edb.server import protocol
from edb.server import tenant as edbtenant
from edb.server.protocol import binary  # type: ignore
from edb.server.protocol import pg_ext  # type: ignore
from edb.server import metrics
from edb.server import pgcon

from edb.pgsql import patches as pg_patches

from . import dbview

if TYPE_CHECKING:
    import asyncio.base_events
    import pathlib


ADMIN_PLACEHOLDER = "<edgedb:admin>"
logger = logging.getLogger('edb.server')
log_metrics = logging.getLogger('edb.server.metrics')


class StartupError(Exception):
    pass


class Server:

    _tenant: edbtenant.Tenant
    _tenants_by_sslobj: MutableMapping

    _sys_queries: Mapping[str, str]
    _local_intro_query: bytes
    _global_intro_query: bytes
    _report_config_typedesc: dict[defines.ProtocolVersion, bytes]
    _file_watch_handles: list[asyncio.Handle]

    _std_schema: s_schema.Schema
    _refl_schema: s_schema.Schema
    _schema_class_layout: s_refl.SchemaClassLayout

    _servers: Mapping[str, asyncio.AbstractServer]

    _testmode: bool

    # We maintain an OrderedDict of all active client connections.
    # We use an OrderedDict because it allows to move keys to either
    # end of the dict. That's used to keep all active client connections
    # grouped at the right end of the dict. The idea is that we can then
    # have a periodically run coroutine to GC all inactive connections.
    # This should be more economical than maintaining a TimerHandle for
    # every open connection. Also, this way, we can react to the
    # `session_idle_timeout` config setting changed mid-flight.
    _binary_conns: collections.OrderedDict[binary.EdgeConnection, bool]
    _pgext_conns: dict[str, pg_ext.PgConnection]
    _idle_gc_handler: asyncio.TimerHandle | None = None
    _session_idle_timeout: int | None = None
    _stmt_cache_size: int | None = None

    def __init__(
        self,
        *,
        runstate_dir,
        internal_runstate_dir,
        compiler_pool_size,
        compiler_pool_mode: srvargs.CompilerPoolMode,
        compiler_pool_addr,
        nethosts,
        netport,
        new_instance: bool,
        listen_sockets: tuple[socket.socket, ...] = (),
        testmode: bool = False,
        binary_endpoint_security: srvargs.ServerEndpointSecurityMode = (
            srvargs.ServerEndpointSecurityMode.Tls),
        http_endpoint_security: srvargs.ServerEndpointSecurityMode = (
            srvargs.ServerEndpointSecurityMode.Tls),
        auto_shutdown_after: float = -1,
        echo_runtime_info: bool = False,
        status_sinks: Sequence[Callable[[str], None]] = (),
        startup_script: Optional[srvargs.StartupScript] = None,
        default_auth_method: srvargs.ServerAuthMethods = (
            srvargs.DEFAULT_AUTH_METHODS),
        admin_ui: bool = False,
        instance_name: str,
        disable_dynamic_system_config: bool = False,
        tenant: edbtenant.Tenant,
    ):
        self.__loop = asyncio.get_running_loop()

        self._tenant = tenant
        tenant.set_server(self)
        self._config_settings = config.get_settings()

        # Used to tag PG notifications to later disambiguate them.
        self._server_id = str(uuid.uuid4())

        self._initing = False

        self._runstate_dir = runstate_dir
        self._internal_runstate_dir = internal_runstate_dir
        self._compiler_pool = None
        self._compiler_pool_size = compiler_pool_size
        self._compiler_pool_mode = compiler_pool_mode
        self._compiler_pool_addr = compiler_pool_addr

        self._listen_sockets = listen_sockets
        if listen_sockets:
            nethosts = tuple(s.getsockname()[0] for s in listen_sockets)
            netport = listen_sockets[0].getsockname()[1]

        self._listen_hosts = nethosts
        self._listen_port = netport

        self._sys_auth: Tuple[Any, ...] = tuple()

        # Shutdown the server after the last management
        # connection has disconnected
        # and there have been no new connections for n seconds
        self._auto_shutdown_after = auto_shutdown_after
        self._auto_shutdown_handler = None

        self._echo_runtime_info = echo_runtime_info
        self._status_sinks = status_sinks

        self._startup_script = startup_script
        self._new_instance = new_instance

        self._instance_name = instance_name

        self._sys_queries = immutables.Map()

        self._devmode = devmode.is_in_dev_mode()
        self._testmode = testmode

        self._binary_proto_id_counter = 0
        self._binary_conns = collections.OrderedDict()
        self._pgext_conns = {}

        self._servers = {}

        self._http_query_cache = cache.StatementsCache(
            maxsize=defines.HTTP_PORT_QUERY_CACHE_SIZE)

        self._http_last_minute_requests = windowedsum.WindowedSum()
        self._http_request_logger = None

        self._stop_evt = asyncio.Event()
        self._tls_cert_file = None
        self._tls_cert_newly_generated = False
        self._sslctx = None
        self._sslctx_pgext = None
        self._tenants_by_sslobj = weakref.WeakKeyDictionary()

        self._jws_key: jwk.JWK | None = None
        self._jws_keys_newly_generated = False
        self._jwt_sub_allowlist: frozenset[str] | None = None
        self._jwt_revocation_list: frozenset[str] | None = None

        self._default_auth_method = default_auth_method
        self._binary_endpoint_security = binary_endpoint_security
        self._http_endpoint_security = http_endpoint_security

        self._idle_gc_handler = None
        self._session_idle_timeout = None

        self._admin_ui = admin_ui

        self._readiness = srvargs.ReadinessState.Default
        self._readiness_reason = ""

        self._file_watch_handles = []
        self._tls_certs_reload_retry_handle = None

        self._disable_dynamic_system_config = disable_dynamic_system_config
        self._report_config_typedesc = {}

    @property
    def _accept_new_tasks(self):
        return self._tenant._accept_new_tasks

    @property
    def _serving(self):
        return self._tenant._running

    async def _request_stats_logger(self):
        last_seen = -1
        while True:
            current = int(self._http_last_minute_requests)
            if current != last_seen:
                log_metrics.info(
                    "HTTP requests in last minute: %d",
                    current,
                )
                last_seen = current

            await asyncio.sleep(30)

    def get_server_id(self):
        return self._server_id

    def get_listen_hosts(self):
        return self._listen_hosts

    def get_listen_port(self):
        return self._listen_port

    def get_loop(self):
        return self.__loop

    def get_instance_name(self):
        return self._instance_name

    def in_dev_mode(self):
        return self._devmode

    def in_test_mode(self):
        return self._testmode

    def is_admin_ui_enabled(self):
        return self._admin_ui

    def is_online(self) -> bool:
        return self._readiness is not srvargs.ReadinessState.Offline

    def is_ready(self) -> bool:
        return (
            self._readiness is srvargs.ReadinessState.Default
            or self._readiness is srvargs.ReadinessState.ReadOnly
        )

    def is_readonly(self) -> bool:
        return self._readiness is srvargs.ReadinessState.ReadOnly

    def get_readiness_reason(self) -> str:
        return self._readiness_reason

    def on_binary_client_created(self) -> str:
        self._binary_proto_id_counter += 1

        if self._auto_shutdown_handler:
            self._auto_shutdown_handler.cancel()
            self._auto_shutdown_handler = None

        return str(self._binary_proto_id_counter)

    def on_binary_client_connected(self, conn):
        self._binary_conns[conn] = True
        metrics.current_client_connections.inc()

    def on_binary_client_authed(self, conn):
        self._report_connections(event='opened')
        metrics.total_client_connections.inc()

    def on_binary_client_after_idling(self, conn):
        try:
            self._binary_conns.move_to_end(conn, last=True)
        except KeyError:
            # Shouldn't happen, but just in case some weird async twist
            # gets us here we don't want to crash the connection with
            # this error.
            metrics.background_errors.inc(1.0, 'client_after_idling')

    def on_binary_client_disconnected(self, conn):
        self._binary_conns.pop(conn, None)
        self._report_connections(event="closed")
        metrics.current_client_connections.dec()
        self.maybe_auto_shutdown()

    def maybe_auto_shutdown(self):
        if (
            not self._binary_conns
            and self._auto_shutdown_after >= 0
            and self._auto_shutdown_handler is None
        ):
            self._auto_shutdown_handler = self.__loop.call_later(
                self._auto_shutdown_after, self.request_auto_shutdown)

    def _report_connections(self, *, event: str) -> None:
        log_metrics.info(
            "%s a connection; open_count=%d",
            event,
            len(self._binary_conns),
        )

    def on_pgext_client_connected(self, conn):
        self._pgext_conns[conn.get_id()] = conn

    def on_pgext_client_disconnected(self, conn):
        self._pgext_conns.pop(conn.get_id(), None)
        self.maybe_auto_shutdown()

    def cancel_pgext_connection(self, pid, secret):
        conn = self._pgext_conns.get(pid)
        if conn is not None:
            conn.cancel(secret)

    @property
    def _dbindex(self) -> dbview.DatabaseIndex | None:
        return self._tenant._dbindex

    async def init(self):
        self._initing = True
        try:
            await self._tenant.init_sys_pgcon()

            await self._load_instance_data()
            await self._maybe_patch()

            await self._tenant.init()

            self._populate_sys_auth()

            sys_config = self._dbindex.get_sys_config()
            if not self._listen_hosts:
                self._listen_hosts = (
                    config.lookup('listen_addresses', sys_config)
                    or ('localhost',)
                )

            if self._listen_port is None:
                self._listen_port = (
                    config.lookup('listen_port', sys_config)
                    or defines.EDGEDB_PORT
                )

            self._stmt_cache_size = config.lookup(
                '_pg_prepared_statement_cache_size', sys_config
            )

            self._reinit_idle_gc_collector()

        finally:
            self._initing = False

    def _reinit_idle_gc_collector(self) -> float:
        if self._auto_shutdown_after >= 0:
            return -1

        if self._idle_gc_handler is not None:
            self._idle_gc_handler.cancel()
            self._idle_gc_handler = None

        assert self._dbindex is not None
        session_idle_timeout = config.lookup(
            'session_idle_timeout', self._dbindex.get_sys_config())

        timeout = session_idle_timeout.to_microseconds()
        timeout /= 1_000_000.0  # convert to seconds

        if timeout > 0:
            self._idle_gc_handler = self.__loop.call_later(
                timeout, self._idle_gc_collector)

        return timeout

    def _reload_stmt_cache_size(self):
        size = config.lookup(
            '_pg_prepared_statement_cache_size', self._dbindex.get_sys_config()
        )
        self._stmt_cache_size = size
        for conn in self._tenant._pg_pool.iterate_connections():
            conn.set_stmt_cache_size(size)

    def _idle_gc_collector(self):
        try:
            self._idle_gc_handler = None
            idle_timeout = self._reinit_idle_gc_collector()

            if idle_timeout <= 0:
                return

            now = time.monotonic()
            expiry_time = now - idle_timeout
            for conn in self._binary_conns:
                try:
                    if conn.is_idle(expiry_time):
                        metrics.idle_client_connections.inc()
                        conn.close_for_idling()
                    elif conn.is_alive():
                        # We are sorting connections in
                        # 'on_binary_client_after_idling' to specifically
                        # enable this optimization. As soon as we find first
                        # non-idle active connection we're guaranteed
                        # to have traversed all of the potentially idling
                        # connections.
                        break
                except Exception:
                    metrics.background_errors.inc(1.0, 'close_for_idling')
                    conn.abort()
        except Exception:
            metrics.background_errors.inc(1.0, 'idle_clients_collector')
            raise

    async def _create_compiler_pool(self):
        # Force Postgres version in BackendRuntimeParams to be the
        # minimal supported, because the compiler does not rely on
        # the version, and not pinning it would make the remote compiler
        # pool refuse connections from clients that have differing versions
        # of Postgres backing them.
        runtime_params = self._tenant.get_backend_runtime_params()
        min_ver = '.'.join(str(v) for v in defines.MIN_POSTGRES_VERSION)
        runtime_params = runtime_params._replace(
            instance_params=runtime_params.instance_params._replace(
                version=buildmeta.parse_pg_version(min_ver),
            ),
        )

        args = dict(
            pool_size=self._compiler_pool_size,
            pool_class=self._compiler_pool_mode.pool_class,
            dbindex=self._dbindex,
            runstate_dir=self._internal_runstate_dir,
            backend_runtime_params=runtime_params,
            std_schema=self._std_schema,
            refl_schema=self._refl_schema,
            schema_class_layout=self._schema_class_layout,
        )
        if self._compiler_pool_mode == srvargs.CompilerPoolMode.Remote:
            args['address'] = self._compiler_pool_addr
        self._compiler_pool = await compiler_pool.create_compiler_pool(**args)

    async def _destroy_compiler_pool(self):
        if self._compiler_pool is not None:
            await self._compiler_pool.stop()
            self._compiler_pool = None

    def _populate_sys_auth(self):
        cfg = self._dbindex.get_sys_config()
        auth = config.lookup('auth', cfg) or ()
        self._sys_auth = tuple(sorted(auth, key=lambda a: a.priority))

    def get_compiler_pool(self):
        return self._compiler_pool

    def get_db(self, *, dbname: str):
        assert self._dbindex is not None
        return self._dbindex.get_db(dbname)

    def maybe_get_db(self, *, dbname: str):
        assert self._dbindex is not None
        return self._dbindex.maybe_get_db(dbname)

    async def new_dbview(self, *, dbname, query_cache, protocol_version):
        db = self.get_db(dbname=dbname)
        await db.introspection()
        return self._dbindex.new_view(
            dbname, query_cache=query_cache, protocol_version=protocol_version
        )

    def remove_dbview(self, dbview):
        return self._dbindex.remove_view(dbview)

    def get_global_schema(self):
        return self._dbindex.get_global_schema()

    def get_compilation_system_config(self):
        return self._dbindex.get_compilation_system_config()

    async def reload_sys_config(self):
        cfg = await self._tenant._load_sys_config()
        self._dbindex.update_sys_config(cfg)
        self._reinit_idle_gc_collector()

    def schedule_reported_config_if_needed(self, setting_name):
        setting = self._config_settings[setting_name]
        if setting.report and self._accept_new_tasks:
            self.create_task(
                self._tenant._load_reported_config(), interruptable=True)

    async def introspect_global_schema(
        self, conn: pgcon.PGConnection
    ) -> s_schema.Schema:
        intro_query = self._global_intro_query
        json_data = await conn.sql_fetch_val(intro_query)
        return s_refl.parse_into(
            base_schema=self._std_schema,
            schema=s_schema.FlatSchema(),
            data=json_data,
            schema_class_layout=self._schema_class_layout,
        )

    async def introspect_user_schema(self, conn, global_schema=None):
        json_data = await conn.sql_fetch_val(self._local_intro_query)

        base_schema = s_schema.ChainedSchema(
            self._std_schema,
            s_schema.FlatSchema(),
            global_schema or self.get_global_schema(),
        )

        return s_refl.parse_into(
            base_schema=base_schema,
            schema=s_schema.FlatSchema(),
            data=json_data,
            schema_class_layout=self._schema_class_layout,
        )

    async def introspect_db(self, dbname):
        """Use this method to (re-)introspect a DB.

        If the DB is already registered in self._dbindex, its
        schema, config, etc. would simply be updated. If it's missing
        an entry for it would be created.

        All remote notifications of remote events should use this method
        to refresh the state. Even if the remote event was a simple config
        change, a lot of other events could happen before it was sent to us
        by a remote server and us receiving it. E.g. a DB could have been
        dropped and recreated again. It's safer to refresh the entire state
        than refreshing individual components of it. Besides, DDL and
        database-level config modifications are supposed to be rare events.
        """
        logger.info("introspecting database '%s'", dbname)

        conn = await self._tenant._acquire_intro_pgcon(dbname)
        if not conn:
            return

        try:
            user_schema = await self.introspect_user_schema(conn)

            reflection_cache_json = await conn.sql_fetch_val(
                b'''
                    SELECT json_agg(o.c)
                    FROM (
                        SELECT
                            json_build_object(
                                'eql_hash', t.eql_hash,
                                'argnames', array_to_json(t.argnames)
                            ) AS c
                        FROM
                            ROWS FROM(edgedb._get_cached_reflection())
                                AS t(eql_hash text, argnames text[])
                    ) AS o;
                ''',
            )

            reflection_cache = immutables.Map({
                r['eql_hash']: tuple(r['argnames'])
                for r in json.loads(reflection_cache_json)
            })

            backend_ids_json = await conn.sql_fetch_val(
                b'''
                SELECT
                    json_object_agg(
                        "id"::text,
                        "backend_id"
                    )::text
                FROM
                    edgedb."_SchemaType"
                ''',
            )
            backend_ids = json.loads(backend_ids_json)

            db_config = await self.introspect_db_config(conn)
            extensions = await self._tenant._introspect_extensions(conn)

            assert self._dbindex is not None
            self._dbindex.register_db(
                dbname,
                user_schema=user_schema,
                db_config=db_config,
                reflection_cache=reflection_cache,
                backend_ids=backend_ids,
                extensions=extensions,
            )
        finally:
            self._tenant.release_pgcon(dbname, conn)

    async def introspect_extensions(self, dbname):
        logger.info("introspecting extensions for database '%s'", dbname)
        conn = await self._tenant._acquire_intro_pgcon(dbname)
        if not conn:
            return

        try:
            extensions = await self._tenant._introspect_extensions(conn)
        finally:
            self._tenant.release_pgcon(dbname, conn)

        db = self._dbindex.maybe_get_db(dbname)
        if db is not None:
            db.extensions = extensions

    async def introspect_db_config(self, conn):
        result = await conn.sql_fetch_val(self.get_sys_query('dbconfig'))
        return config.from_json(config.get_settings(), result)

    async def get_dbnames(self, syscon):
        dbs_query = self.get_sys_query('listdbs')
        json_data = await syscon.sql_fetch_val(dbs_query)
        return json.loads(json_data)

    async def get_patch_count(self, conn):
        """Get the number of applied patches."""
        num_patches = await conn.sql_fetch_val(
            b'''
                SELECT json::json from edgedbinstdata.instdata
                WHERE key = 'num_patches';
            ''',
        )
        num_patches = json.loads(num_patches) if num_patches else 0
        return num_patches

    async def _get_patch_log(self, conn, idx):
        # We need to maintain a log in the system database of
        # patches that have been applied. This is so that if a
        # patch creates a new object, and then we succesfully
        # apply the patch to a user db but crash *before* applying
        # it to the system db, when we start up again and try
        # applying it to the system db, it is important that we
        # apply the same compiled version of the patch. If we
        # instead recompiled it, and it created new objects, those
        # objects might have a different id in the std schema and
        # in the actual user db.
        result = await conn.sql_fetch_val(f'''\
            SELECT bin FROM edgedbinstdata.instdata
            WHERE key = 'patch_log_{idx}';
        '''.encode('utf-8'))
        if result:
            return pickle.loads(result)
        else:
            return None

    async def _prepare_patches(self, conn):
        """Prepare all the patches"""
        num_patches = await self.get_patch_count(conn)

        if num_patches < len(pg_patches.PATCHES):
            logger.info("preparing patches for database upgrade")

        patches = {}
        patch_list = list(enumerate(pg_patches.PATCHES))
        for num, (kind, patch) in patch_list[num_patches:]:
            from . import bootstrap

            idx = num_patches + num
            if not (entry := await self._get_patch_log(conn, idx)):
                entry = bootstrap.prepare_patch(
                    num, kind, patch, self._std_schema, self._refl_schema,
                    self._schema_class_layout,
                    self._tenant.get_backend_runtime_params())

                await bootstrap._store_static_bin_cache_conn(
                    conn, f'patch_log_{idx}', pickle.dumps(entry))

            patches[num] = entry
            _, _, updates, _ = entry
            if 'stdschema' in updates:
                self._std_schema = updates['stdschema']
                # +config patches might modify config_spec, which requires
                # a reload of it from the schema.
                if '+config' in kind:
                    config_spec = config.load_spec_from_schema(self._std_schema)
                    config.set_settings(config_spec)

            if 'reflschema' in updates:
                self._refl_schema = updates['reflschema']
            if 'local_intro_query' in updates:
                self._local_intro_query = updates['local_intro_query']
            if 'global_intro_query' in updates:
                self._global_intro_query = updates['global_intro_query']
            if 'classlayout' in updates:
                self._schema_class_layout = updates['classlayout']
            if 'sysqueries' in updates:
                queries = json.loads(updates['sysqueries'])
                self._sys_queries = immutables.Map(
                    {k: q.encode() for k, q in queries.items()})
            if 'report_configs_typedesc' in updates:
                self._report_config_typedesc = (
                    updates['report_configs_typedesc'])

        return patches

    async def _maybe_apply_patches(self, dbname, conn, patches, sys=False):
        """Apply any un-applied patches to the database."""
        num_patches = await self.get_patch_count(conn)
        for num, (sql, syssql, _, repair) in patches.items():
            if num_patches <= num:
                if sys:
                    sql += syssql
                logger.info("applying patch %d to database '%s'", num, dbname)
                sql = tuple(x.encode('utf-8') for x in sql)

                # Only do repairs when they are the *last* pending
                # repair in the patch queue. We make sure that every
                # patch that changes the user schema is followed by a
                # repair, so this allows us to only ever have to do
                # repairs on up-to-date std schemas.
                last_repair = repair and not any(
                    patches[i][3] for i in range(num + 1, len(patches))
                )
                if last_repair:
                    from . import bootstrap

                    global_schema = (
                        await self._tenant.introspect_global_schema(conn)
                    )
                    user_schema = await self.introspect_user_schema(
                        conn, global_schema)
                    config = await self.introspect_db_config(conn)
                    try:
                        logger.info("repairing database '%s'", dbname)
                        sql += bootstrap.prepare_repair_patch(
                            self._std_schema,
                            self._refl_schema,
                            user_schema,
                            global_schema,
                            self._schema_class_layout,
                            self._tenant.get_backend_runtime_params(),
                            config,
                        )
                    except errors.EdgeDBError as e:
                        if isinstance(e, errors.InternalServerError):
                            raise
                        raise errors.SchemaError(
                            f'Could not repair schema inconsistencies in '
                            f'database "{dbname}". Probably the schema is '
                            f'no longer valid due to a bug fix.\n'
                            f'Downgrade to the last working version, fix '
                            f'the schema issue, and try again.'
                        ) from e

                if sql:
                    await conn.sql_fetch(sql)

    async def _maybe_patch_db(self, dbname, patches):
        logger.info("applying patches to database '%s'", dbname)

        try:
            async with self._direct_pgcon(dbname) as conn:
                await self._maybe_apply_patches(dbname, conn, patches)
        except Exception as e:
            if (
                isinstance(e, errors.EdgeDBError)
                and not isinstance(e, errors.InternalServerError)
            ):
                raise
            raise errors.InternalServerError(
                f'Could not apply patches for minor version upgrade to '
                f'database {dbname}'
            ) from e

    async def _maybe_patch(self):
        """Apply patches to all the databases"""

        async with self._tenant.use_sys_pgcon() as syscon:
            patches = await self._prepare_patches(syscon)
            if not patches:
                return

            dbnames = await self.get_dbnames(syscon)

        async with taskgroup.TaskGroup(name='apply patches') as g:
            # Patch all the databases
            for dbname in dbnames:
                if dbname != defines.EDGEDB_SYSTEM_DB:
                    g.create_task(self._maybe_patch_db(dbname, patches))

            # Patch the template db, so that any newly created databases
            # will have the patches.
            g.create_task(self._maybe_patch_db(
                defines.EDGEDB_TEMPLATE_DB, patches))

        await self._tenant.ensure_database_not_connected(
            defines.EDGEDB_TEMPLATE_DB
        )

        # Patch the system db last. The system db needs to go last so
        # that it only gets updated if all of the other databases have
        # been succesfully patched. This is important, since we don't check
        # other databases for patches unless the system db is patched.
        #
        # Driving everything from the system db like this lets us
        # always use the correct schema when compiling patches.
        async with self._tenant.use_sys_pgcon() as syscon:
            await self._maybe_apply_patches(
                defines.EDGEDB_SYSTEM_DB, syscon, patches, sys=True)

    def _load_schema(self, result, version_key):
        res = pickle.loads(result[2:])
        if version_key != pg_patches.get_version_key(len(pg_patches.PATCHES)):
            res = s_schema.upgrade_schema(res)
        return res

    async def _load_instance_data(self):
        async with self._tenant.use_sys_pgcon() as syscon:
            patch_count = await self.get_patch_count(syscon)
            version_key = pg_patches.get_version_key(patch_count)

            result = await syscon.sql_fetch_val(f'''\
                SELECT json::json FROM edgedbinstdata.instdata
                WHERE key = 'sysqueries{version_key}';
            '''.encode('utf-8'))
            queries = json.loads(result)
            self._sys_queries = immutables.Map(
                {k: q.encode() for k, q in queries.items()})

            self._local_intro_query = await syscon.sql_fetch_val(f'''\
                SELECT text FROM edgedbinstdata.instdata
                WHERE key = 'local_intro_query{version_key}';
            '''.encode('utf-8'))

            self._global_intro_query = await syscon.sql_fetch_val(f'''\
                SELECT text FROM edgedbinstdata.instdata
                WHERE key = 'global_intro_query{version_key}';
            '''.encode('utf-8'))

            result = await syscon.sql_fetch_val(f'''\
                SELECT bin FROM edgedbinstdata.instdata
                WHERE key = 'stdschema{version_key}';
            '''.encode('utf-8'))
            try:
                self._std_schema = self._load_schema(result, version_key)
            except Exception as e:
                raise RuntimeError(
                    'could not load std schema pickle') from e

            result = await syscon.sql_fetch_val(f'''\
                SELECT bin FROM edgedbinstdata.instdata
                WHERE key = 'reflschema{version_key}';
            '''.encode('utf-8'))
            try:
                self._refl_schema = self._load_schema(result, version_key)
            except Exception as e:
                raise RuntimeError(
                    'could not load refl schema pickle') from e

            result = await syscon.sql_fetch_val(f'''\
                SELECT bin FROM edgedbinstdata.instdata
                WHERE key = 'classlayout{version_key}';
            '''.encode('utf-8'))
            try:
                self._schema_class_layout = pickle.loads(result[2:])
            except Exception as e:
                raise RuntimeError(
                    'could not load schema class layout pickle') from e

            self._report_config_typedesc[(1, 0)] = await syscon.sql_fetch_val(
                f'''
                    SELECT bin FROM edgedbinstdata.instdata
                    WHERE key = 'report_configs_typedesc_1_0{version_key}';
                '''.encode('utf-8'),
            )

            self._report_config_typedesc[(2, 0)] = await syscon.sql_fetch_val(
                f'''
                    SELECT bin FROM edgedbinstdata.instdata
                    WHERE key = 'report_configs_typedesc_2_0{version_key}';
                '''.encode('utf-8'),
            )

    async def _restart_servers_new_addr(self, nethosts, netport):
        if not netport:
            raise RuntimeError('cannot restart without network port specified')
        nethosts, has_ipv4_wc, has_ipv6_wc = await _resolve_interfaces(
            nethosts
        )
        servers_to_stop = []
        servers_to_stop_early = []
        servers = {}
        if self._listen_port == netport:
            hosts_to_start = [
                host for host in nethosts if host not in self._servers
            ]
            for host, srv in self._servers.items():
                if host == ADMIN_PLACEHOLDER or host in nethosts:
                    servers[host] = srv
                elif host in ['::', '0.0.0.0']:
                    servers_to_stop_early.append(srv)
                else:
                    if has_ipv4_wc:
                        try:
                            ipaddress.IPv4Address(host)
                        except ValueError:
                            pass
                        else:
                            servers_to_stop_early.append(srv)
                            continue
                    if has_ipv6_wc:
                        try:
                            ipaddress.IPv6Address(host)
                        except ValueError:
                            pass
                        else:
                            servers_to_stop_early.append(srv)
                            continue
                    servers_to_stop.append(srv)
            admin = False
        else:
            hosts_to_start = nethosts
            servers_to_stop = self._servers.values()
            admin = True

        if servers_to_stop_early:
            await self._stop_servers_with_logging(servers_to_stop_early)

        if hosts_to_start:
            try:
                new_servers, *_ = await self._start_servers(
                    hosts_to_start,
                    netport,
                    admin=admin,
                )
                servers.update(new_servers)
            except StartupError:
                raise errors.ConfigurationError(
                    'Server updated its config but cannot serve on requested '
                    'address/port, please see server log for more information.'
                )
        self._servers = servers
        self._listen_hosts = [
            s.getsockname()[0]
            for host, tcp_srv in servers.items()
            if host != ADMIN_PLACEHOLDER
            for s in tcp_srv.sockets
        ]
        self._listen_port = netport

        await self._stop_servers_with_logging(servers_to_stop)

    async def _stop_servers_with_logging(self, servers_to_stop):
        addrs = []
        unix_addr = None
        port = None
        for srv in servers_to_stop:
            for s in srv.sockets:
                addr = s.getsockname()
                if isinstance(addr, tuple):
                    addrs.append(addr[:2])
                    if port is None:
                        port = addr[1]
                    elif port != addr[1]:
                        port = 0
                else:
                    unix_addr = addr
        if len(addrs) > 1:
            if port:
                addr_str = f"{{{', '.join(addr[0] for addr in addrs)}}}:{port}"
            else:
                addr_str = f"{{{', '.join('%s:%d' % addr for addr in addrs)}}}"
        elif addrs:
            addr_str = "%s:%d" % addrs[0]
        else:
            addr_str = None
        if addr_str:
            logger.info('Stopping to serve on %s', addr_str)
        if unix_addr:
            logger.info('Stopping to serve admin on %s', unix_addr)

        await self._stop_servers(servers_to_stop)

    async def _on_before_drop_db(
        self,
        dbname: str,
        current_dbname: str
    ) -> None:
        if current_dbname == dbname:
            raise errors.ExecutionError(
                f'cannot drop the currently open database {dbname!r}')

        await self._tenant.ensure_database_not_connected(dbname)

    async def _on_before_create_db_from_template(
        self,
        dbname: str,
        current_dbname: str
    ):
        if current_dbname == dbname:
            raise errors.ExecutionError(
                f'cannot create database using currently open database '
                f'{dbname!r} as a template database')

        await self._tenant.ensure_database_not_connected(dbname)

    def _on_after_drop_db(self, dbname: str):
        try:
            assert self._dbindex is not None
            if self._dbindex.has_db(dbname):
                self._dbindex.unregister_db(dbname)
            self._tenant._block_new_connections.discard(dbname)
        except Exception:
            metrics.background_errors.inc(1.0, 'on_after_drop_db')
            raise

    async def _on_system_config_add(self, setting_name, value):
        # CONFIGURE INSTANCE INSERT ConfigObject;
        pass

    async def _on_system_config_rem(self, setting_name, value):
        # CONFIGURE INSTANCE RESET ConfigObject;
        pass

    async def _on_system_config_set(self, setting_name, value):
        # CONFIGURE INSTANCE SET setting_name := value;
        try:
            if setting_name == 'listen_addresses':
                await self._restart_servers_new_addr(value, self._listen_port)

            elif setting_name == 'listen_port':
                await self._restart_servers_new_addr(self._listen_hosts, value)

            elif setting_name == 'session_idle_timeout':
                self._reinit_idle_gc_collector()

            elif setting_name == '_pg_prepared_statement_cache_size':
                self._reload_stmt_cache_size()

            self.schedule_reported_config_if_needed(setting_name)
        except Exception:
            metrics.background_errors.inc(1.0, 'on_system_config_set')
            raise

    async def _on_system_config_reset(self, setting_name):
        # CONFIGURE INSTANCE RESET setting_name;
        try:
            if setting_name == 'listen_addresses':
                cfg = self._dbindex.get_sys_config()
                await self._restart_servers_new_addr(
                    config.lookup('listen_addresses', cfg) or ('localhost',),
                    self._listen_port,
                )

            elif setting_name == 'listen_port':
                cfg = self._dbindex.get_sys_config()
                await self._restart_servers_new_addr(
                    self._listen_hosts,
                    config.lookup('listen_port', cfg) or defines.EDGEDB_PORT,
                )

            elif setting_name == 'session_idle_timeout':
                self._reinit_idle_gc_collector()

            elif setting_name == '_pg_prepared_statement_cache_size':
                self._reload_stmt_cache_size()

            self.schedule_reported_config_if_needed(setting_name)
        except Exception:
            metrics.background_errors.inc(1.0, 'on_system_config_reset')
            raise

    def before_alter_system_config(self):
        if self._disable_dynamic_system_config:
            raise errors.ConfigurationError(
                "cannot change this configuration value in this instance"
            )

    async def _after_system_config_add(self, setting_name, value):
        # CONFIGURE INSTANCE INSERT ConfigObject;
        try:
            if setting_name == 'auth':
                self._populate_sys_auth()
        except Exception:
            metrics.background_errors.inc(1.0, 'after_system_config_add')
            raise

    async def _after_system_config_rem(self, setting_name, value):
        # CONFIGURE INSTANCE RESET ConfigObject;
        try:
            if setting_name == 'auth':
                self._populate_sys_auth()
        except Exception:
            metrics.background_errors.inc(1.0, 'after_system_config_rem')
            raise

    async def _after_system_config_set(self, setting_name, value):
        # CONFIGURE INSTANCE SET setting_name := value;
        pass

    async def _after_system_config_reset(self, setting_name):
        # CONFIGURE INSTANCE RESET setting_name;
        pass

    @contextlib.asynccontextmanager
    async def _direct_pgcon(
        self,
        dbname: str,
    ) -> AsyncGenerator[pgcon.PGConnection, None]:
        conn = None
        try:
            conn = await self._tenant._pg_connect(dbname)
            yield conn
        finally:
            if conn is not None:
                await self._tenant._pg_disconnect(conn)

    async def _cancel_pgcon_operation(self, pgcon) -> bool:
        async with self._tenant.use_sys_pgcon() as syscon:
            if pgcon.idle:
                # pgcon could have received the query results while we
                # were acquiring a system connection to cancel it.
                return False

            if pgcon.is_cancelling():
                # Somehow the connection is already being cancelled and
                # we don't want to have to cancellations go in parallel.
                return False

            pgcon.start_pg_cancellation()
            try:
                # Returns True if the `pid` exists and it was able to send it a
                # SIGINT.  Will throw an exception if the privileges aren't
                # sufficient.
                result = await syscon.sql_fetch_val(
                    f'SELECT pg_cancel_backend({pgcon.backend_pid});'.encode(),
                )
            finally:
                pgcon.finish_pg_cancellation()

            return result == b'\x01'

    async def _cancel_and_discard_pgcon(self, pgcon, dbname) -> None:
        try:
            if self._serving:
                await self._cancel_pgcon_operation(pgcon)
        finally:
            self._tenant.release_pgcon(dbname, pgcon, discard=True)

    async def _signal_sysevent(self, event, **kwargs):
        try:
            if not self._initing and not self._serving:
                # This is very likely if we are doing
                # "run_startup_script_and_exit()", but is also possible if the
                # server was shut down with this coroutine as a background task
                # in flight.
                return

            async with self._tenant.use_sys_pgcon() as pgcon:
                await pgcon.signal_sysevent(event, **kwargs)
        except Exception:
            metrics.background_errors.inc(1.0, 'signal_sysevent')
            raise

    def _on_remote_database_quarantine(self, dbname):
        if not self._accept_new_tasks:
            return

        # Block new connections to the database.
        self._tenant._block_new_connections.add(dbname)

        async def task():
            try:
                await self._tenant._pg_pool.prune_inactive_connections(dbname)
            except Exception:
                metrics.background_errors.inc(1.0, 'remote_db_quarantine')
                raise

        self.create_task(task(), interruptable=True)

    def _on_remote_ddl(self, dbname):
        if not self._accept_new_tasks:
            return

        # Triggered by a postgres notification event 'schema-changes'
        # on the __edgedb_sysevent__ channel
        async def task():
            try:
                await self.introspect_db(dbname)
            except Exception:
                metrics.background_errors.inc(1.0, 'on_remote_ddl')
                raise

        self.create_task(task(), interruptable=True)

    def _on_remote_database_changes(self):
        if not self._accept_new_tasks:
            return

        # Triggered by a postgres notification event 'database-changes'
        # on the __edgedb_sysevent__ channel
        async def task():
            async with self._tenant.use_sys_pgcon() as syscon:
                dbnames = set(await self.get_dbnames(syscon))

            tg = taskgroup.TaskGroup(name='new database introspection')
            async with tg as g:
                for dbname in dbnames:
                    if not self._dbindex.has_db(dbname):
                        g.create_task(
                            self._tenant._early_introspect_db(dbname)
                        )

            dropped = []
            for db in self._dbindex.iter_dbs():
                if db.name not in dbnames:
                    dropped.append(db.name)
            for dbname in dropped:
                self._on_after_drop_db(dbname)

        self.create_task(task(), interruptable=True)

    def _on_remote_database_config_change(self, dbname):
        if not self._accept_new_tasks:
            return

        # Triggered by a postgres notification event 'database-config-changes'
        # on the __edgedb_sysevent__ channel
        async def task():
            try:
                await self.introspect_db(dbname)
            except Exception:
                metrics.background_errors.inc(
                    1.0, 'on_remote_database_config_change')
                raise

        self.create_task(task(), interruptable=True)

    def _on_database_extensions_changes(self, dbname):
        if not self._accept_new_tasks:
            return

        async def task():
            try:
                await self.introspect_extensions(dbname)
            except Exception:
                metrics.background_errors.inc(
                    1.0, 'on_database_extensions_change')
                raise

        self.create_task(task(), interruptable=True)

    def _on_local_database_config_change(self, dbname):
        if not self._accept_new_tasks:
            return

        # Triggered by DB Index.
        # It's easier and safer to just schedule full re-introspection
        # of the DB and update all components of it.
        async def task():
            try:
                await self.introspect_db(dbname)
            except Exception:
                metrics.background_errors.inc(
                    1.0, 'on_local_database_config_change')
                raise

        self.create_task(task(), interruptable=True)

    def _on_remote_system_config_change(self):
        if not self._accept_new_tasks:
            return

        # Triggered by a postgres notification event 'system-config-changes'
        # on the __edgedb_sysevent__ channel

        async def task():
            try:
                await self.reload_sys_config()
            except Exception:
                metrics.background_errors.inc(
                    1.0, 'on_remote_system_config_change')
                raise

        self.create_task(task(), interruptable=True)

    def _on_global_schema_change(self):
        if not self._accept_new_tasks:
            return

        async def task():
            try:
                await self._tenant._reintrospect_global_schema()
            except Exception:
                metrics.background_errors.inc(
                    1.0, 'on_global_schema_change')
                raise

        self.create_task(task(), interruptable=True)

    async def run_startup_script_and_exit(self):
        """Run the script specified in *startup_script* and exit immediately"""
        if self._startup_script is None:
            raise AssertionError('startup script is not defined')
        await self._create_compiler_pool()
        try:
            await binary.run_script(
                server=self,
                tenant=self._tenant,
                database=self._startup_script.database,
                user=self._startup_script.user,
                script=self._startup_script.text,
            )
        finally:
            await self._destroy_compiler_pool()

    async def _start_server(
        self,
        host: str,
        port: int,
        sock: Optional[socket.socket] = None,
    ) -> Optional[asyncio.base_events.Server]:
        proto_factory = lambda: protocol.HttpProtocol(
            self,
            self._sslctx,
            self._sslctx_pgext,
            binary_endpoint_security=self._binary_endpoint_security,
            http_endpoint_security=self._http_endpoint_security,
        )

        try:
            kwargs: dict[str, Any]
            if sock is not None:
                kwargs = {"sock": sock}
            else:
                kwargs = {"host": host, "port": port}
            return await self.__loop.create_server(proto_factory, **kwargs)
        except Exception as e:
            logger.warning(
                f"could not create listen socket for '{host}:{port}': {e}"
            )
            return None

    async def _start_admin_server(
        self,
        port: int,
    ) -> asyncio.base_events.Server:
        admin_unix_sock_path = os.path.join(
            self._runstate_dir, f'.s.EDGEDB.admin.{port}')
        assert len(admin_unix_sock_path) <= (
            defines.MAX_RUNSTATE_DIR_PATH
            + defines.MAX_UNIX_SOCKET_PATH_LENGTH
            + 1
        ), "admin Unix socket length exceeds maximum allowed"
        admin_unix_srv = await self.__loop.create_unix_server(
            lambda: binary.new_edge_connection(
                self, self.get_default_tenant(), external_auth=True
            ),
            admin_unix_sock_path
        )
        os.chmod(admin_unix_sock_path, stat.S_IRUSR | stat.S_IWUSR)
        logger.info('Serving admin on %s', admin_unix_sock_path)
        return admin_unix_srv

    async def _start_servers(
        self,
        hosts: tuple[str, ...],
        port: int,
        *,
        admin: bool = True,
        sockets: tuple[socket.socket, ...] = (),
    ):
        servers = {}
        if port == 0:
            # Automatic port selection requires us to start servers
            # sequentially until we get a working bound socket to ensure
            # consistent port value across all requested listen addresses.
            try:
                for host in hosts:
                    server = await self._start_server(host, port)
                    if server is not None:
                        if port == 0:
                            port = server.sockets[0].getsockname()[1]
                        servers[host] = server
            except Exception:
                await self._stop_servers(servers.values())
                raise
        else:
            start_tasks = {}
            try:
                async with taskgroup.TaskGroup() as g:
                    if sockets:
                        for host, sock in zip(hosts, sockets):
                            start_tasks[host] = g.create_task(
                                self._start_server(host, port, sock=sock)
                            )
                    else:
                        for host in hosts:
                            start_tasks[host] = g.create_task(
                                self._start_server(host, port)
                            )
            except Exception:
                await self._stop_servers([
                    fut.result() for fut in start_tasks.values()
                    if (
                        fut.done()
                        and fut.exception() is None
                        and fut.result() is not None
                    )
                ])
                raise

            servers.update({
                host: fut.result()
                for host, fut in start_tasks.items()
                if fut.result() is not None
            })

        # Fail if none of the servers can be started, except when the admin
        # server on a UNIX domain socket will be started.
        if not servers and (not admin or port == 0):
            raise StartupError("could not create any listen sockets")

        addrs = []
        for tcp_srv in servers.values():
            for s in tcp_srv.sockets:
                addrs.append(s.getsockname())

        if len(addrs) > 1:
            if port:
                addr_str = f"{{{', '.join(addr[0] for addr in addrs)}}}:{port}"
            else:
                addr_str = f"""{{{', '.join(
                    f'{addr[0]}:{addr[1]}' for addr in addrs)}}}"""
        elif addrs:
            addr_str = f'{addrs[0][0]}:{addrs[0][1]}'
            port = addrs[0][1]
        else:
            addr_str = None

        if addr_str:
            logger.info('Serving on %s', addr_str)

        if admin and port:
            try:
                admin_unix_srv = await self._start_admin_server(port)
            except Exception:
                await self._stop_servers(servers.values())
                raise
            servers[ADMIN_PLACEHOLDER] = admin_unix_srv

        return servers, port, addrs

    def init_readiness_state(self, state_file):
        def reload_state_file(_file_modified, _event):
            self.reload_readiness_state(state_file)

        self.reload_readiness_state(state_file)
        self._file_watch_handles.append(
            self.__loop._monitor_fs(str(state_file), reload_state_file)
        )

    def reload_readiness_state(self, state_file):
        try:
            with open(state_file, 'rt') as rt:
                line = rt.readline().strip()
                try:
                    state, _, reason = line.partition(":")
                    self._readiness = srvargs.ReadinessState(state)
                    self._readiness_reason = reason
                    logger.info(
                        "readiness state file changed, "
                        "setting server readiness to %r%s",
                        state,
                        f" ({reason})" if reason else "",
                    )
                except ValueError:
                    logger.warning(
                        "invalid state in readiness state file (%r): %r, "
                        "resetting server readiness to 'default'",
                        state_file,
                        state,
                    )
                    self._readiness = srvargs.ReadinessState.Default

        except FileNotFoundError:
            logger.info(
                "readiness state file (%s) removed, resetting "
                "server readiness to 'default'",
                state_file,
            )
            self._readiness = srvargs.ReadinessState.Default

        except Exception as e:
            logger.warning(
                "cannot read readiness state file (%s): %s, "
                "resetting server readiness to 'default'",
                state_file,
                e,
            )
            self._readiness = srvargs.ReadinessState.Default

        self._tenant._accepting_connections = self.is_online()

    def _sni_callback(self, sslobj, server_name, sslctx):
        pass

    def reload_tls(self, tls_cert_file, tls_key_file):
        logger.info("loading TLS certificates")
        tls_password_needed = False
        if self._tls_certs_reload_retry_handle is not None:
            self._tls_certs_reload_retry_handle.cancel()
            self._tls_certs_reload_retry_handle = None

        def _tls_private_key_password():
            nonlocal tls_password_needed
            tls_password_needed = True
            return os.environ.get('EDGEDB_SERVER_TLS_PRIVATE_KEY_PASSWORD', '')

        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx_pgext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            sslctx.load_cert_chain(
                tls_cert_file,
                tls_key_file,
                password=_tls_private_key_password,
            )
            sslctx_pgext.load_cert_chain(
                tls_cert_file,
                tls_key_file,
                password=_tls_private_key_password,
            )
        except ssl.SSLError as e:
            if e.library == "SSL" and e.errno == 9:  # ERR_LIB_PEM
                if tls_password_needed:
                    if _tls_private_key_password():
                        raise StartupError(
                            "Cannot load TLS certificates - it's likely that "
                            "the private key password is wrong."
                        ) from e
                    else:
                        raise StartupError(
                            "Cannot load TLS certificates - the private key "
                            "file is likely protected by a password. Specify "
                            "the password using environment variable: "
                            "EDGEDB_SERVER_TLS_PRIVATE_KEY_PASSWORD"
                        ) from e
                elif tls_key_file is None:
                    raise StartupError(
                        "Cannot load TLS certificates - have you specified "
                        "the private key file using the `--tls-key-file` "
                        "command-line argument?"
                    ) from e
                else:
                    raise StartupError(
                        "Cannot load TLS certificates - please double check "
                        "if the specified certificate files are valid."
                    )
            elif e.library == "X509" and e.errno == 116:
                # X509 Error 116: X509_R_KEY_VALUES_MISMATCH
                raise StartupError(
                    "Cannot load TLS certificates - the private key doesn't "
                    "match the certificate."
                )

            raise StartupError(f"Cannot load TLS certificates - {e}") from e

        sslctx.set_alpn_protocols(['edgedb-binary', 'http/1.1'])
        sslctx.sni_callback = self._sni_callback
        sslctx_pgext.sni_callback = self._sni_callback
        self._sslctx = sslctx
        self._sslctx_pgext = sslctx_pgext

    def init_tls(
        self,
        tls_cert_file,
        tls_key_file,
        tls_cert_newly_generated,
    ):
        assert self._sslctx is self._sslctx_pgext is None
        self.reload_tls(tls_cert_file, tls_key_file)

        self._tls_cert_file = str(tls_cert_file)
        self._tls_cert_newly_generated = tls_cert_newly_generated

        def reload_tls(_file_modified, _event, retry=0):
            try:
                self.reload_tls(tls_cert_file, tls_key_file)
            except (StartupError, FileNotFoundError) as e:
                if retry > defines._TLS_CERT_RELOAD_MAX_RETRIES:
                    logger.critical(str(e))
                    self.request_shutdown()
                else:
                    delay = defines._TLS_CERT_RELOAD_EXP_INTERVAL * 2 ** retry
                    logger.warning("%s; retrying in %.1f seconds.", e, delay)
                    self._tls_certs_reload_retry_handle = (
                        self.__loop.call_later(
                            delay,
                            reload_tls,
                            _file_modified,
                            _event,
                            retry + 1,
                        )
                    )
            except Exception:
                logger.critical(
                    "error while reloading TLS certificate and/or key, "
                    "shutting down.",
                    exc_info=True,
                )
                self.request_shutdown()

        self._file_watch_handles.append(
            self.__loop._monitor_fs(str(tls_cert_file), reload_tls)
        )
        if tls_cert_file != tls_key_file:
            self._file_watch_handles.append(
                self.__loop._monitor_fs(str(tls_key_file), reload_tls)
            )

    def load_jwcrypto(
        self,
        jws_key_file: pathlib.Path,
        jwt_sub_allowlist_file: Optional[pathlib.Path],
        jwt_revocation_list_file: Optional[pathlib.Path],
    ) -> None:
        try:
            self._jws_key = secretkey.load_secret_key(jws_key_file)
        except secretkey.SecretKeyReadError as e:
            raise StartupError(e.args[0]) from e

        if jwt_sub_allowlist_file is not None:
            logger.info("(re-)loading JWT subject allowlist from "
                        f"\"{jwt_sub_allowlist_file}\"")
            try:
                self._jwt_sub_allowlist = frozenset(
                    jwt_sub_allowlist_file.read_text().splitlines(),
                )
            except Exception as e:
                raise StartupError(
                    f"cannot load JWT sub allowlist: {e}") from e

        if jwt_revocation_list_file is not None:
            logger.info("(re-)loading JWT revocation list from "
                        f"\"{jwt_revocation_list_file}\"")
            try:
                self._jwt_revocation_list = frozenset(
                    jwt_revocation_list_file.read_text().splitlines(),
                )
            except Exception as e:
                raise StartupError(
                    f"cannot load JWT revocation list: {e}") from e

    def init_jwcrypto(
        self,
        jws_key_file: pathlib.Path,
        jwt_sub_allowlist_file: Optional[pathlib.Path],
        jwt_revocation_list_file: Optional[pathlib.Path],
        jws_keys_newly_generated: bool,
    ) -> None:
        self.load_jwcrypto(
            jws_key_file,
            jwt_sub_allowlist_file,
            jwt_revocation_list_file,
        )
        self._jws_keys_newly_generated = jws_keys_newly_generated

    def get_jws_key(self) -> jwk.JWK | None:
        return self._jws_key

    def check_jwt(self, claims: dict[str, Any]) -> None:
        """Check JWT for validity"""

        if self._jwt_sub_allowlist is not None:
            subject = claims.get("sub")
            if not subject:
                raise errors.AuthenticationError(
                    "authentication failed: "
                    "JWT does not contain a valid subject claim")
            if subject not in self._jwt_sub_allowlist:
                raise errors.AuthenticationError(
                    "authentication failed: unauthorized subject")

        if self._jwt_revocation_list is not None:
            key_id = claims.get("jti")
            if not key_id:
                raise errors.AuthenticationError(
                    "authentication failed: "
                    "JWT does not contain a valid key id")
            if key_id in self._jwt_revocation_list:
                raise errors.AuthenticationError(
                    "authentication failed: revoked key")

    async def _stop_servers(self, servers):
        async with taskgroup.TaskGroup() as g:
            for srv in servers:
                srv.close()
                g.create_task(srv.wait_closed())

    async def start(self):
        self._stop_evt.clear()

        await self._tenant.start_accepting_new_tasks()

        self._http_request_logger = self.__loop.create_task(
            self._request_stats_logger()
        )

        await self._create_compiler_pool()

        if self._startup_script and self._new_instance:
            await binary.run_script(
                server=self,
                tenant=self._tenant,
                database=self._startup_script.database,
                user=self._startup_script.user,
                script=self._startup_script.text,
            )

        self._servers, actual_port, listen_addrs = await self._start_servers(
            (await _resolve_interfaces(self._listen_hosts))[0],
            self._listen_port,
            sockets=self._listen_sockets,
        )
        self._listen_hosts = [addr[0] for addr in listen_addrs]
        self._listen_port = actual_port

        self._tenant.start_running()

        if self._echo_runtime_info:
            ri = {
                "port": self._listen_port,
                "runstate_dir": str(self._runstate_dir),
                "tls_cert_file": self._tls_cert_file,
            }
            print(f'\nEDGEDB_SERVER_DATA:{json.dumps(ri)}\n', flush=True)

        for status_sink in self._status_sinks:
            status = {
                "listen_addrs": listen_addrs,
                "port": self._listen_port,
                "socket_dir": str(self._runstate_dir),
                "main_pid": os.getpid(),
                "tenant_id": self._tenant.tenant_id,
                "tls_cert_file": self._tls_cert_file,
                "tls_cert_newly_generated": self._tls_cert_newly_generated,
                "jws_keys_newly_generated": self._jws_keys_newly_generated,
            }
            status_sink(f'READY={json.dumps(status)}')

        if self._auto_shutdown_after > 0:
            self._auto_shutdown_handler = self.__loop.call_later(
                self._auto_shutdown_after, self.request_auto_shutdown)

    def request_auto_shutdown(self):
        if self._auto_shutdown_after == 0:
            logger.info("shutting down server: all clients disconnected")
        else:
            logger.info(
                f"shutting down server: no clients connected in last"
                f" {self._auto_shutdown_after} seconds"
            )
        self.request_shutdown()

    def request_shutdown(self):
        self._tenant.stop_accepting_connections()
        self._stop_evt.set()

    async def stop(self):
        try:
            self._tenant.stop()

            if self._idle_gc_handler is not None:
                self._idle_gc_handler.cancel()
                self._idle_gc_handler = None

            if self._http_request_logger is not None:
                self._http_request_logger.cancel()

            for handle in self._file_watch_handles:
                handle.cancel()
            self._file_watch_handles.clear()

            await self._stop_servers(self._servers.values())
            self._servers = {}

            for conn in self._binary_conns:
                conn.stop()
            self._binary_conns.clear()

            for conn in self._pgext_conns.values():
                conn.stop()
            self._pgext_conns.clear()

            await self._tenant.wait_stopped()

            await self._destroy_compiler_pool()

        finally:
            self._tenant.terminate_sys_pgcon()

    def create_task(self, coro, *, interruptable):
        return self._tenant.create_task(coro, interruptable=interruptable)

    async def serve_forever(self):
        await self._stop_evt.wait()

    async def get_auth_method(
        self,
        user: str,
        transport: srvargs.ServerConnTransport,
    ) -> Any:
        authlist = self._sys_auth

        if authlist:
            for auth in authlist:
                match = (
                    (user in auth.user or '*' in auth.user)
                    and (
                        not auth.method.transports
                        or transport in auth.method.transports
                    )
                )

                if match:
                    return auth.method

        default_method = self._default_auth_method.get(transport)
        auth_type = config.get_settings().get_type_by_name(
            default_method.value)
        return auth_type()

    def get_sys_query(self, key):
        return self._sys_queries[key]

    def get_debug_info(self):
        """Used to render the /server-info endpoint in dev/test modes.

        Some tests depend on the exact layout of the returned structure.
        """

        def serialize_config(cfg):
            return {name: value.value for name, value in cfg.items()}

        tenant = self._tenant
        obj = dict(
            params=dict(
                max_backend_connections=tenant.max_backend_connections,
                suggested_client_pool_size=tenant.suggested_client_pool_size,
                tenant_id=tenant.tenant_id,
                dev_mode=self._devmode,
                test_mode=self._testmode,
                default_auth_method=str(self._default_auth_method),
                listen_hosts=self._listen_hosts,
                listen_port=self._listen_port,
            ),
            instance_config=serialize_config(self._dbindex.get_sys_config()),
            user_roles=self._tenant.get_roles(),
            pg_addr=tenant.get_pgaddr(),
            pg_pool=tenant._pg_pool._build_snapshot(now=time.monotonic()),
            compiler_pool=dict(
                worker_pids=list(self._compiler_pool._workers.keys()),
                template_pid=self._compiler_pool.get_template_pid(),
            ),
        )

        dbs = {}
        for db in self._dbindex.iter_dbs():
            if db.name in defines.EDGEDB_SPECIAL_DBS:
                continue

            dbs[db.name] = dict(
                name=db.name,
                dbver=db.dbver,
                config=serialize_config(db.db_config),
                extensions=sorted(db.extensions),
                query_cache_size=db.get_query_cache_size(),
                connections=[
                    dict(
                        in_tx=view.in_tx(),
                        in_tx_error=view.in_tx_error(),
                        config=serialize_config(view.get_session_config()),
                        module_aliases=view.get_modaliases(),
                    )
                    for view in db.iter_views()
                ],
            )

        obj['databases'] = dbs

        return obj

    def get_report_config_typedesc(
        self
    ) -> dict[defines.ProtocolVersion, bytes]:
        return self._report_config_typedesc

    def retrieve_tenant(self, sslobj) -> edbtenant.Tenant | None:
        return self.get_default_tenant()

    def get_default_tenant(self) -> edbtenant.Tenant:
        return self._tenant


def _cleanup_wildcard_addrs(
    hosts: Sequence[str]
) -> tuple[list[str], list[str], bool, bool]:
    """Filter out conflicting addresses in presence of INADDR_ANY wildcards.

    Attempting to bind to 0.0.0.0 (or ::) _and_ a non-wildcard address will
    usually result in EADDRINUSE.  To avoid this, filter out all specific
    addresses if a wildcard is present in the *hosts* sequence.

    Returns a tuple: first element is the new list of hosts, second
    element is a list of rejected host addrs/names.
    """

    ipv4_hosts = set()
    ipv6_hosts = set()
    named_hosts = set()

    ipv4_wc = ipaddress.ip_address('0.0.0.0')
    ipv6_wc = ipaddress.ip_address('::')

    for host in hosts:
        if host == "*":
            ipv4_hosts.add(ipv4_wc)
            ipv6_hosts.add(ipv6_wc)
            continue

        try:
            ip = ipaddress.IPv4Address(host)
        except ValueError:
            pass
        else:
            ipv4_hosts.add(ip)
            continue

        try:
            ip6 = ipaddress.IPv6Address(host)
        except ValueError:
            pass
        else:
            ipv6_hosts.add(ip6)
            continue

        named_hosts.add(host)

    if not ipv4_hosts and not ipv6_hosts:
        return (list(hosts), [], False, False)

    if ipv4_wc not in ipv4_hosts and ipv6_wc not in ipv6_hosts:
        return (list(hosts), [], False, False)

    if ipv4_wc in ipv4_hosts and ipv6_wc in ipv6_hosts:
        return (
            ['0.0.0.0', '::'],
            [
                str(a) for a in
                ((named_hosts | ipv4_hosts | ipv6_hosts) - {ipv4_wc, ipv6_wc})
            ],
            True,
            True,
        )

    if ipv4_wc in ipv4_hosts:
        return (
            [str(a) for a in ({ipv4_wc} | ipv6_hosts)],
            [str(a) for a in ((named_hosts | ipv4_hosts) - {ipv4_wc})],
            True,
            False,
        )

    if ipv6_wc in ipv6_hosts:
        return (
            [str(a) for a in ({ipv6_wc} | ipv4_hosts)],
            [str(a) for a in ((named_hosts | ipv6_hosts) - {ipv6_wc})],
            False,
            True,
        )

    raise AssertionError('unreachable')


async def _resolve_host(host: str) -> list[str] | Exception:
    loop = asyncio.get_running_loop()
    try:
        addrinfo = await loop.getaddrinfo(
            None if host == '*' else host,
            0,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            flags=socket.AI_PASSIVE,
        )
    except Exception as e:
        return e
    else:
        return [addr[4][0] for addr in addrinfo]


async def _resolve_interfaces(
    hosts: Sequence[str]
) -> Tuple[Sequence[str], bool, bool]:

    async with taskgroup.TaskGroup() as g:
        resolve_tasks = {
            host: g.create_task(_resolve_host(host))
            for host in hosts
        }

    addrs = []
    for host, fut in resolve_tasks.items():
        result = fut.result()
        if isinstance(result, Exception):
            logger.warning(
                f"could not translate host name {host!r} to address: {result}")
        else:
            addrs.extend(result)

    (
        clean_addrs, rejected_addrs, has_ipv4_wc, has_ipv6_wc
    ) = _cleanup_wildcard_addrs(addrs)

    if rejected_addrs:
        logger.warning(
            "wildcard addresses found in listen_addresses; " +
            "discarding the other addresses: " +
            ", ".join(repr(h) for h in rejected_addrs)
        )

    return clean_addrs, has_ipv4_wc, has_ipv6_wc
