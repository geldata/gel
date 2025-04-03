#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2019-present MagicStack Inc. and the EdgeDB authors.
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


import threading
import io
import unittest
import time
import typing
import json

try:
    from edb.language_server import main as ls_main
except ImportError:
    ls_main = None  # type: ignore
    pass


class LspReader:
    def __init__(self, stream: io.BytesIO):
        self.stream = stream
        self.offset = 0

    def get_next(self) -> dict:
        val = self.try_get_next()
        while val is None:
            time.sleep(1)
            val = self.try_get_next()
        return val

    def try_get_next(self) -> dict | None:
        headers = {}
        buf = self.stream.getvalue()
        while True:
            end = buf.find(b"\r\n", self.offset)
            if end < 0:
                return None
            line = str(buf[self.offset : end], encoding="ascii")
            self.offset = end + 2

            parts = line.split(": ", maxsplit=1)
            if len(parts) <= 1:
                break
            else:
                headers[parts[0].lower()] = parts[1]

        assert (
            headers["content-type"]
            == "application/vscode-jsonrpc; charset=utf-8"
        )

        content_length = int(headers["content-length"])
        end = self.offset + content_length
        body = buf[self.offset : (self.offset + content_length)]
        self.offset = end

        return json.loads(body)


class LspRunner:
    def __init__(
        self,
    ):
        stream_in = io.BytesIO()
        stream_out = io.BytesIO()

        self.stream_in = stream_in
        self.stream_reader = LspReader(stream_out)
        self.ls = ls_main.init(None)

        def run_server():
            try:
                print(len(self.stream_in.getvalue()) - self.stream_in.tell())
                self.ls.start_io(stdin=stream_in, stdout=stream_out)
            except ValueError as e:
                if str(e) != "I/O operation on closed file.":
                    raise

        self.runner_thread = threading.Thread(target=run_server)
        self.send({
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "processId": None,
                "rootUri": None,
                "capabilities": {}
            }
        })

        self.runner_thread.start()

    def send(self, request: typing.Any):
        body = json.dumps(request).encode('utf-8')
        head = bytes(f"Content-Length: {len(body)}\r\n\r\n", encoding="ascii")

        current_pos = self.stream_in.tell()
        self.stream_in.write(head + body)
        self.stream_in.seek(current_pos)

    def recv(self) -> typing.Any:
        return self.stream_reader.get_next()

    def stop(self):
        self.stream_in.close()
        self.runner_thread.join()


@unittest.skipIf(ls_main is None, "edgedb-ls dependencies are missing")
class TestLanguageServer(unittest.TestCase):
    maxDiff = None

    def test_language_server_01(self):
        runner = LspRunner()

        self.assertEqual(
            runner.recv(),
            {
                "params": {"type": 4, "message": "Starting"},
                "method": "window/logMessage",
                "jsonrpc": "2.0",
            },
        )

        self.assertEqual(
            runner.recv(),
            {
                "params": {"type": 4, "message": "Started"},
                "method": "window/logMessage",
                "jsonrpc": "2.0",
            },
        )

        self.assertEqual(
            runner.recv(),
            {
                "id": 1,
                "jsonrpc": "2.0",
                "result": {
                    "capabilities": {
                        "positionEncoding": "utf-16",
                        "textDocumentSync": {
                            "openClose": True,
                            "change": 2,
                            "save": False,
                        },
                        "completionProvider": {"triggerCharacters": [","]},
                        "definitionProvider": True,
                        "executeCommandProvider": {"commands": []},
                        "workspace": {
                            "workspaceFolders": {
                                "supported": True,
                                "changeNotifications": True,
                            },
                            "fileOperations": {},
                        },
                    },
                    "serverInfo": {
                        "name": "Gel Language Server",
                        "version": "v0.1",
                    },
                },
            },
        )

        runner.stop()
