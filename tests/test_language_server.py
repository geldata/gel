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
import tempfile
import pathlib
import os

try:
    from edb.language_server import main as ls_main
except ImportError:
    ls_main = None  # type: ignore
    pass


class LspReader:
    def __init__(self, stream: io.BytesIO):
        self.stream = stream
        self.offset = 0

    def get_next(self, timeout_sec: float = 1.0) -> dict:
        started_at = time.monotonic()
        while True:
            val = self.try_get_next()
            if val:
                return val
            if time.monotonic() - started_at > timeout_sec:
                raise TimeoutError(
                    "timeout while waiting for server to respond"
                )
            time.sleep(0.1)

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
    logs: list[str]

    def __init__(self):
        self.logs = []
        self.project_dir = tempfile.TemporaryDirectory()

        stream_out = io.BytesIO()
        stream_in_r, stream_in_w = os.pipe()

        self.stream_in = io.FileIO(stream_in_w, "w")
        self.stream_reader = LspReader(stream_out)

        self.ls = ls_main.init(
            '{"project_dir": "' + str(self.project_dir.name) + '"}'
        )

        def run_server():
            try:
                stream_in = io.FileIO(stream_in_r, "r")
                self.ls.start_io(
                    stdin=stream_in,
                    stdout=stream_out,
                )
                stream_in.close()
            except ValueError as e:
                if str(e) != "I/O operation on closed file.":
                    raise

        self.runner_thread = threading.Thread(target=run_server)
        self.runner_thread.start()

    def send(self, request: typing.Any):
        body = json.dumps(request)
        self.stream_in.write(
            f"Content-Length: {len(body)}\r\n\r\n{body}".encode("utf-8")
        )
        self.stream_in.flush()

    def recv(self, timeout_sec=5) -> dict:
        while True:
            msg = self.stream_reader.get_next(timeout_sec)
            if msg.get("method", None) == "window/logMessage":
                self.logs.append(msg["params"]["message"])
                continue
            return msg

    def add_file(self, path: str | pathlib.Path, contents: str) -> typing.Any:
        if isinstance(path, str):
            path = pathlib.Path(path)
        assert not path.is_absolute()

        abs_path: pathlib.Path = self.project_dir.name / path

        if not abs_path.parent.exists():
            abs_path.parent.mkdir(parents=True)
        with open(abs_path, "w") as f:
            f.write(contents)

    def get_uri(self, path: str) -> str:
        return f"file://{self.project_dir.name}/{path}"

    def finish(self):
        # stop the server
        self.stream_in.close()
        self.runner_thread.join()

        # remove the tmp project dir
        self.project_dir.cleanup()

    def send_init(self):
        self.send(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1,
                "params": {
                    "processId": None,
                    "rootUri": None,
                    "capabilities": {},
                    "workspaceFolders": [
                        {
                            "uri": f"file://{self.project_dir.name}",
                            "name": "main workspace",
                        }
                    ],
                },
            }
        )
        self.recv()  # Init response


@unittest.skipIf(ls_main is None, "edgedb-ls dependencies are missing")
class TestLanguageServer(unittest.TestCase):
    maxDiff = None

    def test_language_server_01(self):
        runner = LspRunner()

        runner.send(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1,
                "params": {
                    "processId": None,
                    "rootUri": None,
                    "capabilities": {},
                },
            }
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

        runner.finish()

    def test_language_server_02(self):
        # syntax error
        runner = LspRunner()
        try:
            runner.send_init()

            runner.send(
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": "file://myquery.edgeql",
                            "languageId": "edgeql",
                            "version": 1,
                            "text": """
                                select Hello world }
                            """,
                        }
                    },
                }
            )
            self.assertEqual(
                runner.recv(),
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/publishDiagnostics",
                    "params": {
                        "uri": "file://myquery.edgeql",
                        "version": 1,
                        "diagnostics": [
                            {
                                "message": "Missing '{'",
                                "range": {
                                    "start": {"character": 44, "line": 1},
                                    "end": {"character": 45, "line": 1},
                                },
                                "severity": 1,
                            }
                        ],
                    },
                },
            )
        finally:
            runner.finish()

    def test_language_server_03(self):
        # name error
        runner = LspRunner()
        try:
            runner.add_file(
                "dbschema/default.gel",
                """
                type default::Hello {
                    property world: str;
                }
                """,
            )
            runner.add_file(
                "gel.toml",
                "",
            )
            runner.send_init()

            runner.send(
                {
                    "id": 2,
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": "file://myquery.edgeql",
                            "languageId": "edgeql",
                            "version": 1,
                            "text": """
                                select Hello { worl }
                            """,
                        }
                    },
                }
            )

            self.assertEqual(
                runner.recv(timeout_sec=50),
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/publishDiagnostics",
                    "params": {
                        "uri": runner.get_uri("dbschema/default.gel"),
                        "diagnostics": [],
                    },
                },
            )

            self.assertEqual(
                runner.recv(timeout_sec=5),
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/publishDiagnostics",
                    "params": {
                        "diagnostics": [
                            {
                                "message": (
                                    "object type 'default::Hello' "
                                    "has no link or property 'worl'"
                                ),
                                "range": {
                                    "start": {"character": 47, "line": 1},
                                    "end": {"character": 51, "line": 1},
                                },
                                "severity": 1,
                            }
                        ],
                        "uri": "file://myquery.edgeql",
                        "version": 1,
                    },
                },
            )
        finally:
            runner.finish()

    def test_language_server_04(self):
        # get definition
        runner = LspRunner()
        try:
            runner.add_file(
                "gel.toml",
                "",
            )
            runner.add_file(
                "dbschema/default.gel",
                """
                type default::Hello {
                    property world: str;
                }
                """,
            )
            runner.send_init()

            runner.send(
                {
                    "id": 2,
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": "file://myquery.edgeql",
                            "languageId": "edgeql",
                            "version": 1,
                            "text": """
                                select Hello { world }
                            """,
                        }
                    },
                }
            )
            self.assertEqual(
                runner.recv(timeout_sec=50),
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/publishDiagnostics",
                    "params": {
                        "uri": runner.get_uri("dbschema/default.gel"),
                        "diagnostics": [],
                    },
                },
            )
            self.assertEqual(
                runner.recv(timeout_sec=5),
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/publishDiagnostics",
                    "params": {
                        "diagnostics": [],
                        "uri": "file://myquery.edgeql",
                        "version": 1,
                    },
                },
            )

            runner.send(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "textDocument/definition",
                    "params": {
                        "textDocument": {"uri": "file://myquery.edgeql"},
                        "position": {
                            "line": 1,
                            "character": 50,  # falls on "world"
                        },
                    },
                }
            )
            self.assertEqual(
                runner.recv(timeout_sec=1),
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {
                        "uri": runner.get_uri("dbschema/default.gel"),
                        "range": {
                            "start": {
                                "line": 2,
                                "character": 20,
                            },
                            "end": {
                                "line": 2,
                                "character": 40,
                            },
                        },
                    },
                },
            )
        finally:
            runner.finish()
