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
from typing import Callable, cast, Generator, Optional

import asyncio
import os
import socket
import struct

OnPidCallback = Callable[["HubProtocol", asyncio.Transport, int, int], None]
OnConnectionLostCallback = Callable[[Optional[int]], None]


_uint64_unpacker = struct.Struct('!Q').unpack
_uint64_packer = struct.Struct('!Q').pack


class MessageStream:
    """Data stream that yields messages."""

    _buffer: bytes
    _curmsg_len: int

    def __init__(self) -> None:
        self._buffer = b''
        self._curmsg_len = -1

    def feed_data(self, data: bytes) -> Generator[bytes, None, None]:
        # TODO: rewrite to avoid buffer copies.
        self._buffer += data
        while self._buffer:
            if self._curmsg_len == -1:
                if len(self._buffer) >= 8:
                    self._curmsg_len = _uint64_unpacker(self._buffer[:8])[0]
                    self._buffer = self._buffer[8:]
                else:
                    return

            if self._curmsg_len > 0 and len(self._buffer) >= self._curmsg_len:
                msg = self._buffer[:self._curmsg_len]
                self._buffer = self._buffer[self._curmsg_len:]
                self._curmsg_len = -1
                yield msg
            else:
                return


class HubProtocol(asyncio.Protocol):
    """The Protocol used on the hub side connecting to workers."""

    _loop: asyncio.AbstractEventLoop
    _transport: Optional[asyncio.Transport]
    _closed: bool
    _stream: MessageStream
    _resp_waiters: dict[int, asyncio.Future[memoryview]]
    _on_pid: OnPidCallback
    _on_connection_lost: OnConnectionLostCallback
    _pid: Optional[int]

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        on_pid: OnPidCallback,
        on_connection_lost: OnConnectionLostCallback,
    ) -> None:
        self._loop = loop
        self._transport = None
        self._closed = False
        self._stream = MessageStream()
        self._resp_waiters = {}
        self._on_pid = on_pid
        self._on_connection_lost = on_connection_lost
        self._pid = None

    def connection_made(self, tr: asyncio.BaseTransport) -> None:
        self._transport = cast(asyncio.Transport, tr)

    def send(
        self,
        req_id: int,
        waiter: asyncio.Future[memoryview],
        payload: bytes,
    ) -> None:
        if req_id in self._resp_waiters:
            raise RuntimeError('FramedProtocol: duplicate request ID')
        assert self._transport is not None
        self._resp_waiters[req_id] = waiter
        self._transport.writelines(
            (_uint64_packer(len(payload) + 8), _uint64_packer(req_id), payload)
        )

    def process_message(self, msg: bytes) -> None:
        msgview = memoryview(msg)
        req_id = _uint64_unpacker(msgview[:8])[0]
        waiter = self._resp_waiters.pop(req_id, None)
        if waiter is None:
            # This could have happened if the previous request got cancelled.
            return
        if not waiter.done():
            waiter.set_result(msgview[8:])

    def data_received(self, data: bytes) -> None:
        if self._pid is None:
            assert self._transport is not None
            pid_data = data[:8]
            version = _uint64_unpacker(data[8:16])[0]
            data = data[16:]
            self._pid = _uint64_unpacker(pid_data)[0]
            self._on_pid(self, self._transport, self._pid, version)
        for msg in self._stream.feed_data(data):
            self.process_message(msg)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self._closed = True

        if self._resp_waiters:
            if exc is not None:
                for waiter in self._resp_waiters.values():
                    waiter.set_exception(exc)
            else:
                for waiter in self._resp_waiters.values():
                    waiter.set_exception(ConnectionError(
                        'lost connection to the worker during a call'))
            self._resp_waiters = {}

        self._on_connection_lost(self._pid)


class HubConnection:
    """An abstraction of the hub connections to the workers."""

    _transport: asyncio.Transport
    _protocol: HubProtocol
    _loop: asyncio.AbstractEventLoop
    _req_id_cnt: int
    _version: int
    _aborted: bool

    def __init__(
        self,
        transport: asyncio.Transport,
        protocol: HubProtocol,
        loop: asyncio.AbstractEventLoop,
        version: int,
    ) -> None:
        self._transport = transport
        self._protocol = protocol
        self._loop = loop
        self._req_id_cnt = 0
        self._version = version
        self._aborted = False

    def is_closed(self) -> bool:
        return self._protocol._closed

    async def request(self, data: bytes) -> memoryview:
        self._req_id_cnt += 1
        req_id = self._req_id_cnt

        waiter = self._loop.create_future()
        self._protocol.send(req_id, waiter, data)
        return await waiter

    def abort(self) -> None:
        self._aborted = True
        self._transport.abort()


class WorkerConnection:
    """Connection object used by the worker's process."""

    _sock: Optional[socket.socket]
    _stream: MessageStream

    def __init__(self, sockname: str, version: int) -> None:
        self._sock = socket.socket(socket.AF_UNIX)
        self._sock.connect(sockname)
        self._sock.sendall(
            _uint64_packer(os.getpid()) + _uint64_packer(version)
        )
        self._stream = MessageStream()

    def _on_message(self, msg: bytes) -> tuple[int, memoryview]:
        msgview = memoryview(msg)
        req_id = _uint64_unpacker(msgview[:8])[0]
        return req_id, msgview[8:]

    def reply(self, req_id: int, payload: bytes) -> None:
        assert self._sock is not None
        self._sock.sendall(
            b"".join(
                (
                    _uint64_packer(len(payload) + 8),
                    _uint64_packer(req_id),
                    payload,
                )
            )
        )

    def iter_request(self) -> Generator[tuple[int, memoryview], None, None]:
        while True:
            data = b'' if self._sock is None else self._sock.recv(4096)
            if not data:
                # EOF received - abort
                self.abort()
                return
            yield from map(self._on_message, self._stream.feed_data(data))

    def abort(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None


class ServerProtocol:
    def worker_connected(self, pid: int, version: int) -> None:
        pass

    def worker_disconnected(self, pid: int) -> None:
        pass


class Server:

    _sockname: str
    _loop: asyncio.AbstractEventLoop
    _srv: Optional[asyncio.AbstractServer]
    _pids: dict[int, HubConnection]
    _proto: ServerProtocol

    def __init__(
        self,
        sockname: str,
        loop: asyncio.AbstractEventLoop,
        server_protocol: ServerProtocol,
    ) -> None:
        self._sockname = sockname
        self._loop = loop
        self._srv = None
        self._pids = {}
        self._proto = server_protocol

    def _on_pid_connected(
        self,
        proto: HubProtocol,
        tr: asyncio.Transport,
        pid: int,
        version: int,
    ) -> None:
        assert pid not in self._pids
        self._pids[pid] = HubConnection(tr, proto, self._loop, version)
        self._proto.worker_connected(pid, version)

    def _on_pid_disconnected(self, pid: Optional[int]) -> None:
        if not pid:
            return
        if pid in self._pids:
            self._pids.pop(pid)
            self._proto.worker_disconnected(pid)

    def _proto_factory(self) -> HubProtocol:
        return HubProtocol(
            loop=self._loop,
            on_pid=self._on_pid_connected,
            on_connection_lost=self._on_pid_disconnected,
        )

    def get_by_pid(self, pid: int) -> HubConnection:
        return self._pids[pid]

    async def start(self) -> None:
        self._srv = await self._loop.create_unix_server(
            self._proto_factory,
            path=self._sockname)

    async def stop(self) -> None:
        if self._srv is None:
            return
        self._srv.close()
        for con in self._pids.values():
            con.abort()
        await self._srv.wait_closed()

    def kill_outdated_worker(self, current_version: int) -> None:
        for conn in self._pids.values():
            if conn._version < current_version and not conn._aborted:
                conn.abort()
                break
