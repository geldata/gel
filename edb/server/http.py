#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2024-present MagicStack Inc. and the EdgeDB authors.
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
    Tuple,
    Any,
    Mapping,
    Optional,
    Union,
    Self,
    Callable,
)

import asyncio
import dataclasses
import logging
import os
import json as json_lib
import urllib.parse
import time
from http import HTTPStatus as HTTPStatus

from edb.server._http import Http

logger = logging.getLogger("edb.server")
HeaderType = Optional[Union[list[tuple[str, str]], dict[str, str]]]


@dataclasses.dataclass(frozen=True)
class HttpStat:
    response_time_ms: int
    error_code: int
    response_body_size: int
    response_content_type: str
    request_body_size: int
    request_content_type: str
    method: str
    streaming: bool


StatCallback = Callable[[HttpStat], None]


class HttpClient:
    def __init__(
        self,
        limit: int,
        user_agent: str = "EdgeDB",
        stat_callback: Optional[StatCallback] = None,
    ):
        self._client = Http(limit)
        self._fd = self._client._fd
        self._task = None
        self._skip_reads = 0
        self._loop: Optional[asyncio.AbstractEventLoop] = asyncio.get_running_loop()
        self._task = None
        self._streaming: dict[int, asyncio.Queue[Any]] = {}
        self._next_id = 0
        self._requests: dict[int, asyncio.Future] = {}
        self._user_agent = user_agent
        self._stat_callback = stat_callback

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
            self._loop = None

    def _ensure_task(self):
        if self._loop is None:
            raise Exception("HttpClient was closed")
        if self._task is None:
            self._task = self._loop.create_task(self._boot(self._loop))

    def _update_limit(self, limit: int):
        self._client._update_limit(limit)

    def _process_headers(self, headers: HeaderType) -> list[tuple[str, str]]:
        if headers is None:
            return []
        if isinstance(headers, Mapping):
            return [(k, v) for k, v in headers.items()]
        if isinstance(headers, list):
            return headers
        print(headers)
        raise ValueError(f"Invalid headers type: {type(headers)}")

    def _process_content(
        self,
        headers: list[tuple[str, str]],
        data: bytes | str | dict[str, str] | None = None,
        json: Any | None = None,
    ) -> bytes:
        if json is not None:
            data = json_lib.dumps(json).encode('utf-8')
            headers.append(('Content-Type', 'application/json'))
        elif isinstance(data, str):
            data = data.encode('utf-8')
        elif isinstance(data, dict):
            data = urllib.parse.urlencode(data).encode('utf-8')
            headers.append(
                ('Content-Type', 'application/x-www-form-urlencoded')
            )
        elif data is None:
            data = bytes()
        elif isinstance(data, bytes):
            pass
        else:
            raise ValueError(f"Invalid content type: {type(data)}")
        return data

    def _process_path(self, path: str) -> str:
        return path

    def with_context(
        self,
        *,
        base_url: Optional[str] = None,
        headers: HeaderType = None,
        url_munger: Optional[Callable[[str], str]] = None,
    ) -> Self:
        """Create an HttpClient with common optional base URL and headers that
        will be applied to all requests."""
        return HttpClientContext(
            http_client=self,
            base_url=base_url,
            headers=headers,
            url_munger=url_munger,
        )  # type: ignore

    async def request(
        self,
        *,
        method: str,
        path: str,
        headers: HeaderType = None,
        data: bytes | str | dict[str, str] | None = None,
        json: Any | None = None,
    ) -> tuple[int, bytearray, dict[str, str]]:
        self._ensure_task()
        path = self._process_path(path)
        headers_list = self._process_headers(headers)
        headers_list.append(("User-Agent", self._user_agent))
        data = self._process_content(headers_list, data, json)
        id = self._next_id
        self._next_id += 1
        self._requests[id] = asyncio.Future()
        start_time = time.time()
        try:
            self._client._request(id, path, method, data, headers_list)
            resp = await self._requests[id]
            if self._stat_callback:
                status_code, body, headers = resp
                self._stat_callback(
                    HttpStat(
                        response_time_ms=int((time.time() - start_time) * 1000),
                        error_code=status_code,
                        response_body_size=len(body),
                        response_content_type=dict(headers_list).get(
                            'content-type', ''
                        ),
                        request_body_size=len(data),
                        request_content_type=dict(headers_list).get(
                            'content-type', ''
                        ),
                        method=method,
                        streaming=False,
                    )
                )
            return resp
        finally:
            del self._requests[id]

    async def get(self, path: str, *, headers: HeaderType = None) -> Response:
        result = await self.request(
            method="GET", path=path, data=None, headers=headers
        )
        return Response.from_tuple(result)

    async def post(
        self,
        path: str,
        *,
        headers: HeaderType = None,
        data: bytes | str | dict[str, str] | None = None,
        json: Any | None = None,
    ) -> Response:
        result = await self.request(
            method="POST", path=path, data=data, json=json, headers=headers
        )
        return Response.from_tuple(result)

    async def stream_sse(
        self,
        path: str,
        *,
        method: str = "POST",
        headers: HeaderType = None,
        data: bytes | str | dict[str, str] | None = None,
        json: Any | None = None,
    ) -> Response | ResponseSSE:
        """Create a streaming request. Note that there is no backpressure on the
        SSE events, so the called must continuously iterate on the response to
        avoid excessive memory use."""
        self._ensure_task()
        path = self._process_path(path)
        headers_list = self._process_headers(headers)
        headers_list.append(("User-Agent", self._user_agent))
        data = self._process_content(headers_list, data, json)

        id = self._next_id
        self._next_id += 1
        self._requests[id] = asyncio.Future()
        start_time = time.time()
        try:
            self._client._request_sse(id, path, method, data, headers_list)
            resp = await self._requests[id]
            if self._stat_callback:
                if id in self._streaming:
                    status_code, headers = resp
                    body = b''
                else:
                    status_code, body, headers = resp
                self._stat_callback(
                    HttpStat(
                        response_time_ms=int((time.time() - start_time) * 1000),
                        error_code=status_code,
                        response_body_size=len(body),
                        response_content_type=dict(headers_list).get(
                            'content-type', ''
                        ),
                        request_body_size=len(data),
                        request_content_type=dict(headers_list).get(
                            'content-type', ''
                        ),
                        method=method,
                        streaming=id in self._streaming,
                    )
                )
            if id in self._streaming:
                # Valid to call multiple times
                cancel = lambda: self._client._close(id)
                # Acknowledge SSE message (for backpressure)
                ack = lambda: self._client._ack_sse(id)
                return ResponseSSE.from_tuple(
                    resp, self._streaming[id], cancel, ack
                )
            return Response.from_tuple(resp)
        finally:
            del self._requests[id]

    async def _boot(self, loop: asyncio.AbstractEventLoop) -> None:
        logger.info(f"HTTP client initialized, user_agent={self._user_agent}")
        reader = asyncio.StreamReader(loop=loop)
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        fd = os.fdopen(self._client._fd, 'rb')
        transport, _ = await loop.connect_read_pipe(lambda: reader_protocol, fd)
        try:
            while len(await reader.read(1)) == 1:
                if not self._client or not self._task:
                    break
                if self._skip_reads > 0:
                    self._skip_reads -= 1
                    continue
                msg = self._client._read()
                if not msg:
                    break
                self._process_message(msg)
        finally:
            transport.close()

    def _process_message(self, msg):
        try:
            msg_type, id, data = msg
            if msg_type == 0:  # Error
                if id in self._requests:
                    self._requests[id].set_exception(Exception(data[0]))
                if id in self._streaming:
                    self._streaming[id].put_nowait(None)
                    del self._streaming[id]
            elif msg_type == 1:  # Response
                if id in self._requests:
                    self._requests[id].set_result(data)
            elif msg_type == 2:  # SSEStart
                if id in self._requests:
                    self._streaming[id] = asyncio.Queue()
                    self._requests[id].set_result(data)
            elif msg_type == 3:  # SSEEvent
                if id in self._streaming:
                    self._streaming[id].put_nowait(data)
            elif msg_type == 4:  # SSEEnd
                if id in self._streaming:
                    self._streaming[id].put_nowait(None)
                    del self._streaming[id]
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore
        pass


class HttpClientContext(HttpClient):
    def __init__(
        self,
        http_client: HttpClient,
        url_munger: Callable[[str], str] | None = None,
        headers: HeaderType = None,
        base_url: str | None = None,
    ):
        self._task = None
        self.url_munger = url_munger
        self.http_client = http_client
        self.base_url = base_url
        self.headers = super()._process_headers(headers)

    def _process_headers(self, headers):
        headers = super()._process_headers(headers)
        headers += self.headers
        return headers

    def _process_path(self, path):
        path = super()._process_path(path)
        if self.base_url is not None:
            path = self.base_url + path
        if self.url_munger is not None:
            path = self.url_munger(path)
        return path

    async def request(
        self, *, method, path, headers=None, data=None, json=None
    ):
        path = self._process_path(path)
        headers = self._process_headers(headers)
        return await self.http_client.request(
            method=method, path=path, headers=headers, data=data, json=json
        )

    async def stream_sse(
        self, path, *, method="POST", headers=None, data=None, json=None
    ):
        path = self._process_path(path)
        headers = self._process_headers(headers)
        return await self.http_client.stream_sse(
            path, method=method, headers=headers, data=data, json=json
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore
        pass


class CaseInsensitiveDict(dict):
    def __init__(self, data: Optional[list[Tuple[str, str]]] = None):
        super().__init__()
        if data:
            for k, v in data:
                self[k.lower()] = v

    def __setitem__(self, key: str, value: str):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key: str):
        return super().__getitem__(key.lower())

    def get(self, key: str, default=None):
        return super().get(key.lower(), default)

    def update(self, *args, **kwargs: str) -> None:
        if args:
            data = args[0]
            if isinstance(data, Mapping):
                for key, value in data.items():
                    self[key] = value
            else:
                for key, value in data:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value


@dataclasses.dataclass(frozen=True)
class Response:
    status_code: int
    body: bytearray
    headers: CaseInsensitiveDict
    is_streaming: bool = False

    @classmethod
    def from_tuple(cls, data: Tuple[int, bytearray, dict[str, str]]):
        status_code, body, headers_list = data
        headers = CaseInsensitiveDict([(k, v) for k, v in headers_list.items()])
        return cls(status_code, body, headers)

    def json(self):
        return json_lib.loads(self.body.decode('utf-8'))

    def bytes(self):
        return bytes(self.body)

    @property
    def text(self) -> str:
        return self.body.decode('utf-8')

    def __aenter__(self) -> Self:
        return self

    def __aexit__(self, exc_type, exc_value, traceback):
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


@dataclasses.dataclass(frozen=True)
class ResponseSSE:
    status_code: int
    headers: CaseInsensitiveDict
    _stream: asyncio.Queue = dataclasses.field(repr=False)
    _cancel: Callable[[], None] = dataclasses.field(repr=False)
    _ack: Callable[[], None] = dataclasses.field(repr=False)
    is_streaming: bool = True

    @classmethod
    def from_tuple(
        cls,
        data: Tuple[int, dict[str, str]],
        stream: asyncio.Queue,
        cancel: Callable[[], None],
        ack: Callable[[], None],
    ):
        status_code, headers = data
        headers = CaseInsensitiveDict([(k, v) for k, v in headers.items()])
        return cls(status_code, headers, stream, cancel, ack)

    @dataclasses.dataclass(frozen=True)
    class SSEEvent:
        event: str
        data: str
        id: Optional[str] = None

    def close(self):
        self._cancel()

    def __del__(self):
        self.close()

    def __aiter__(self):
        return self

    async def __anext__(self):
        next = await self._stream.get()
        try:
            if next is None:
                raise StopAsyncIteration
            id, data, event = next
            return self.SSEEvent(event, data, id)
        finally:
            self._ack()

    def __aenter__(self) -> Self:
        return self

    def __aexit__(self, exc_type, exc_value, traceback):
        self.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
