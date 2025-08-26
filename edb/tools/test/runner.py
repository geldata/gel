#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2017-present MagicStack Inc. and the EdgeDB authors.
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

# ruff: noqa: PLW0603

from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NamedTuple,
    Optional,
    TextIO,
    TypeGuard,
)
from collections.abc import Callable
from typing_extensions import TypeAliasType

import asyncio
import collections
import csv
import dataclasses
import enum
import faulthandler
import io
import itertools
import json
import multiprocessing
import multiprocessing.reduction
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest.case
import unittest.result
import unittest.signals
import warnings

import click


from . import cov
from . import cpython_state
from . import fixtures
from . import loader
from . import mproc_fixes
from . import styles
from . import results

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator
    from collections.abc import Callable, Mapping, Sequence

_ConnArgs = TypeAliasType("_ConnArgs", dict[str, Any])

_WorkerParam = TypeAliasType(
    "_WorkerParam", tuple[_ConnArgs | None, str | None, str | None]
)

_ResultCall = TypeAliasType(
    "_ResultCall", tuple[str, tuple[Any, ...], dict[str, Any]]
)

result: ParallelTextTestResult | ChannelingTestResult | None = None
coverage_run: Optional[Any] = None
py_hash_secret: bytes = cpython_state.get_py_hash_secret()
py_random_seed: bytes = random.SystemRandom().randbytes(8)

faulthandler.enable(file=sys.stderr, all_threads=True)


def teardown_suite() -> None:
    # The TestSuite methods are mutating the *result* object,
    # and the suite itself does not hold any state whatsoever,
    # and, in our case specifically, it doesn't even hold
    # references to tests being run, so we can think of
    # its methods as static.
    suite = StreamingTestSuite()
    suite._tearDownPreviousClass(None, result)  # type: ignore[attr-defined]
    suite._handleModuleTearDown(result)  # type: ignore[attr-defined]


def _populate_gel_instance_env(
    instance: loader.Instance,
    backend_dsn: str | None,
) -> None:
    server_addr = instance.get_connect_args()
    server_addr_data = json.dumps(server_addr)
    for key in ("EDGEDB_TEST_CLUSTER_ADDR", "GEL_TEST_INSTANCE_ADDR"):
        os.environ[key] = server_addr_data

    server_ver = str(instance.get_server_version())
    for key in ("EDGEDB_TEST_SERVER_VERSION", "GEL_TEST_SERVER_VERSION"):
        os.environ[key] = server_ver

    if backend_dsn is not None:
        for key in ("EDGEDB_TEST_BACKEND_DSN", "GEL_TEST_BACKEND_DSN"):
            os.environ[key] = backend_dsn

    has_create_db = instance.has_create_database()
    for key in ("EDGEDB_TEST_CASES_SET_UP", "GEL_TEST_CASES_SET_UP"):
        os.environ[key] = "skip" if has_create_db else "inplace"

    has_create_role = str(instance.has_create_role())
    for key in ("EDGEDB_TEST_HAS_CREATE_ROLE", "GEL_TEST_HAS_CREATE_ROLE"):
        os.environ[key] = has_create_role


def init_worker(
    status_queue: multiprocessing.SimpleQueue[bool],
    param_queue: multiprocessing.SimpleQueue[_WorkerParam],
    result_queue: multiprocessing.SimpleQueue[_ResultCall],
    additional_init: Callable[[], None] | None,
) -> None:
    global result, coverage_run, py_hash_secret, py_random_seed

    faulthandler.enable(file=sys.stderr, all_threads=True)

    if additional_init:
        additional_init()

    # Make sure the generator is re-seeded, as we have inherited
    # the seed from the parent process.
    py_random_seed = random.SystemRandom().randbytes(8)
    random.seed(py_random_seed)

    result = ChannelingTestResult(result_queue)

    os.environ["EDGEDB_TEST_PARALLEL"] = "1"
    os.environ["GEL_TEST_PARALLEL"] = "1"

    coverage_run = cov.CoverageConfig.start_coverage_if_requested()
    py_hash_secret = cpython_state.get_py_hash_secret()
    status_queue.put(True)  # noqa: FBT003


def shutdown_worker() -> None:
    global coverage_run  # noqa: PLW0602

    teardown_suite()
    if coverage_run is not None:
        coverage_run.stop()
        coverage_run.save()


class StreamingTestSuite(unittest.TestSuite):
    _cleanup = False

    def run(  # type: ignore [override]
        self,
        test: unittest.TestCase,
        result: ParallelTextTestResult | ChannelingTestResult,
    ) -> ParallelTextTestResult | ChannelingTestResult:
        with warnings.catch_warnings(record=True) as ww:
            warnings.resetwarnings()
            warnings.simplefilter("default")

            # This is temporary, until we implement `subtransaction`
            # functionality of RFC1004
            warnings.filterwarnings(
                "ignore",
                message=r'The "transaction\(\)" method is deprecated'
                r" and is scheduled to be removed",
                category=DeprecationWarning,
            )

            result = self._run(test, result)

            if ww:
                for wmsg in ww:
                    if wmsg.source is not None:
                        wmsg.source = str(wmsg.source)
                    result.addWarning(test, wmsg)

        return result

    def _run(
        self,
        test: unittest.TestCase,
        result: ParallelTextTestResult | ChannelingTestResult,
    ) -> ParallelTextTestResult | ChannelingTestResult:
        result._testRunEntered = True  # type: ignore [union-attr]
        self._tearDownPreviousClass(test, result)  # type: ignore [attr-defined]
        self._handleModuleFixture(test, result)  # type: ignore [attr-defined]
        self._handleClassSetUp(test, result)  # type: ignore [attr-defined]
        result._previousTestClass = test.__class__  # type: ignore [union-attr]

        if getattr(test.__class__, "_classSetupFailed", False) or getattr(
            result, "_moduleSetUpFailed", False
        ):
            return result

        result.annotate_test(
            test,
            {
                "py-hash-secret": py_hash_secret,
                "py-random-seed": py_random_seed,
                "runner-pid": os.getpid(),
            },
        )

        start = time.monotonic()
        test.run(result)
        elapsed = time.monotonic() - start

        result.record_test_stats(test, {"running-time": elapsed})

        result._testRunEntered = False  # type: ignore [union-attr]
        return result


def _unroll_suite(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from _unroll_suite(test)
        else:
            yield test


def _run_test(
    workload: unittest.TestSuite | unittest.TestCase,
) -> None:
    suite = StreamingTestSuite()
    assert result is not None
    if isinstance(workload, unittest.TestSuite):
        for test in _unroll_suite(workload):
            suite.run(test, result)
    else:
        suite.run(workload, result)


def _is_exc_info(args: Any) -> TypeGuard[results.ExcInfo]:
    return (
        isinstance(args, tuple)
        and len(args) == 3
        and issubclass(args[0], BaseException)
    )


def _is_assert_failure(args: Any) -> bool:
    if _is_exc_info(args):
        return issubclass(args[0], AssertionError)
    elif isinstance(args, str):
        # HACK: If we serialized the error on the client side... just
        # detect it in the string.
        return "\nAssertionError" in args
    else:
        return False


class _ExpectedFailure(NamedTuple):
    reason: str | None
    not_implemented: bool
    expect_failure: bool
    expect_error: bool


def _is_expecting_failure(test: object) -> _ExpectedFailure | None:
    reason = getattr(test, "__et_xfail_reason__", None)
    is_geltest_xfail = hasattr(test, "__et_xfail_reason__")
    geltest_not_impl = getattr(test, "__et_xfail_not_implemented__", False)
    geltest_xfail = getattr(test, "__et_xfail_allow_failure__", False)
    geltest_xerror = getattr(test, "__et_xfail_allow_error__", False)

    unittest_xfail = getattr(test, "__unittest_expecting_failure__", False)

    if unittest_xfail or geltest_not_impl or geltest_xfail or geltest_xerror:
        return _ExpectedFailure(
            reason=reason,
            not_implemented=geltest_not_impl,
            expect_failure=geltest_xfail or unittest_xfail,
            expect_error=geltest_xerror or not is_geltest_xfail,
        )
    else:
        return None


@dataclasses.dataclass
class SerializedServerError:
    test_error: str
    server_error: str


class ChannelingTestResultMeta(type):
    @staticmethod
    def get_wrapper(meth: str) -> Callable[..., None]:
        def _wrapper(
            self: ChannelingTestResult,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            try:
                self._queue.put((meth, args, kwargs))
            except Exception:
                raise

        return _wrapper

    def __new__(
        mcls,
        name: str,
        bases: tuple[type[Any]],
        dct: dict[str, Any],
    ) -> ChannelingTestResultMeta:
        for meth in (
            "startTest",
            "addSuccess",
            "addError",
            "addFailure",
            "addSkip",
            "addExpectedFailure",
            "addUnexpectedSuccess",
            "addSubTest",
            "addWarning",
            "record_test_stats",
            "annotate_test",
        ):
            dct[meth] = mcls.get_wrapper(meth)

        return super().__new__(mcls, name, bases, dct)


class ChannelingTestResult(
    unittest.result.TestResult,
    metaclass=ChannelingTestResultMeta,
):
    def __init__(
        self, queue: multiprocessing.SimpleQueue[_ResultCall]
    ) -> None:
        super().__init__(io.StringIO(), False, 1)  # noqa: FBT003
        self._queue = queue

    def _setupStdout(self) -> None:
        pass

    def _restoreStdout(self) -> None:
        pass

    def printErrors(self) -> None:
        pass

    def printErrorList(self, flavour: Any, errors: Any) -> None:
        pass

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state.pop("_queue")
        state.pop("_original_stdout")
        state.pop("_original_stderr")
        return state

    if TYPE_CHECKING:

        def record_test_stats(
            self, test: unittest.TestCase, stats: fixtures.StatsEntry
        ) -> None: ...

        def annotate_test(
            self, test: unittest.TestCase, annotations: dict[str, Any]
        ) -> None: ...

        def addWarning(
            self,
            test: unittest.TestCase,
            wmsg: warnings.WarningMessage,
        ) -> None: ...


def _monitor_thread(
    queue: multiprocessing.Queue[_ResultCall | None],
    result: ParallelTextTestResult,
) -> None:
    while True:
        entry = queue.get()
        if entry is None:
            # This must be the last message in the queue, injected
            # when all tests are completed and the pool is about
            # to be closed.
            break

        methname, args, kwargs = entry
        method = result
        for part in methname.split("."):
            method = getattr(method, part)
        assert callable(method)
        method(*args, **kwargs)


def status_thread_func(
    result: ParallelTextTestResult,
    stop_event: threading.Event,
) -> None:
    while True:
        result.report_still_running()
        time.sleep(1)
        if stop_event.is_set():
            break


class ParallelTestSuite(unittest.TestSuite):
    def __init__(
        self,
        tests: Iterable[unittest.TestCase | unittest.TestSuite],
        *,
        server_conn_args: dict[str, Any] | None = None,
        server_ver: str | None = None,
        num_workers: int = 1,
        backend_dsn: str | None = None,
        worker_init: Callable[[], None] | None = None,
    ) -> None:
        self.tests = tests
        self.server_conn_args = server_conn_args
        self.server_ver = server_ver
        self.backend_dsn = backend_dsn
        self.num_workers = num_workers
        self.stop_requested = False
        self.worker_init = worker_init

    def run(self, result: ParallelTextTestResult) -> ParallelTextTestResult:  # type: ignore [override]
        # We use SimpleQueues because they are more predictable.
        # They do the necessary IO directly, without using a
        # helper thread.
        result_queue: multiprocessing.SimpleQueue[_ResultCall | None] = (
            multiprocessing.SimpleQueue()
        )
        status_queue: multiprocessing.SimpleQueue[bool] = (
            multiprocessing.SimpleQueue()
        )
        worker_param_queue: multiprocessing.SimpleQueue[_WorkerParam] = (
            multiprocessing.SimpleQueue()
        )

        # Prepopulate the worker param queue with server connection
        # information.
        for _ in range(self.num_workers):
            worker_param_queue.put(
                (self.server_conn_args, self.server_ver, self.backend_dsn)
            )

        result_thread = threading.Thread(
            name="test-monitor",
            target=_monitor_thread,
            args=(result_queue, result),
            daemon=True,
        )
        result_thread.start()

        status_thread_stop_event = threading.Event()
        status_thread = threading.Thread(
            name="test-status",
            target=status_thread_func,
            args=(result, status_thread_stop_event),
            daemon=True,
        )
        status_thread.start()

        initargs = (
            status_queue,
            worker_param_queue,
            result_queue,
            self.worker_init,
        )

        pool = multiprocessing.Pool(
            self.num_workers,
            initializer=mproc_fixes.WorkerScope(init_worker, shutdown_worker),
            initargs=initargs,
        )

        # Wait for all workers to initialize.
        for _ in range(self.num_workers):
            status_queue.get()

        with pool:
            for is_repeat in (False, True):
                if self.stop_requested:
                    break
                ar = pool.map_async(
                    _run_test,
                    filter(
                        lambda t: ("test_zREPEAT" in str(t)) == is_repeat,
                        self.tests,
                    ),
                    chunksize=1,
                )

                while True:
                    try:
                        ar.get(timeout=0.1)
                    except multiprocessing.TimeoutError:
                        # multiprocessing doesn't handle processes
                        # crashing very well, so we check ourselves
                        # (having disabled its own child pruning in
                        # mproc_fixes)
                        #
                        # TODO: Should we look into using
                        # concurrent.futures.ProcessPoolExecutor
                        # instead?
                        for p in pool._pool:  # type: ignore [attr-defined]
                            if p.exitcode:
                                if isinstance(result, ParallelTextTestResult):
                                    result.current_pids.get(p.pid)
                                sys.stderr.flush()
                                os._exit(1)

                        if self.stop_requested:
                            break
                        else:
                            continue
                    else:
                        break

        # Wait for pool to shutdown, this includes test teardowns.
        pool.join()

        # Post the terminal message to the queue so that
        # test-monitor can stop.
        result_queue.put(None)
        status_thread_stop_event.set()

        # Give the test-monitor and test-status threads some time to process
        # the
        # queue messages.  If something goes wrong, the thread will be forcibly
        # joined by a timeout.
        result_thread.join(timeout=3)
        status_thread.join(timeout=3)

        return result


class SequentialTestSuite(unittest.TestSuite):
    def __init__(
        self,
        tests: Sequence[unittest.TestCase | unittest.TestSuite],
        *,
        worker_init: Callable[[], None] | None,
    ) -> None:
        self.tests = tests
        self.stop_requested = False
        self.worker_init = worker_init

    def run(self, result_: ParallelTextTestResult) -> ParallelTextTestResult:  # type: ignore [override]
        global result
        result = result_

        if self.worker_init:
            self.worker_init()

        random.seed(py_random_seed)

        for test in self.tests:
            _run_test(test)
            if self.stop_requested:
                break

        # Make sure the class and the module teardown methods are
        # executed for the trailing test, _run_test() does not do
        # this for us.
        teardown_suite()

        return result


class Markers(enum.Enum):
    passed = "."
    errored = "E"
    skipped = "s"
    failed = "F"
    xfailed = "x"  # expected fail
    not_implemented = "-"
    upassed = "U"  # unexpected success


class OutputFormat(enum.Enum):
    auto = "auto"
    simple = "simple"
    stacked = "stacked"
    verbose = "verbose"


class BaseRenderer:
    def __init__(
        self,
        *,
        tests: Sequence[unittest.TestCase | unittest.TestSuite],
        stream: TextIO,
    ) -> None:
        self.stream = stream
        self.styles_map: dict[str, styles.Style] = {
            marker.value: getattr(styles, f"marker_{marker.name}")
            for marker in Markers
        }

    def format_test(self, test: unittest.TestCase) -> str:
        if isinstance(test, unittest.case._SubTest):  # type: ignore [attr-defined]
            if hasattr(test, "params") and getattr(test, "params", None):
                params = ", ".join(
                    f"{k}={v!r}"
                    for k, v in getattr(test, "params", {}).items()
                )
            else:
                params = "<subtest>"
            return f"{getattr(test, 'test_case', test)} {{{params}}}"
        else:
            if hasattr(test, "fail_notes") and getattr(
                test, "fail_notes", None
            ):
                fail_notes = ", ".join(
                    f"{k}={v!r}"
                    for k, v in getattr(test, "fail_notes", {}).items()
                )
                return f"{test} {{{fail_notes}}}"
            else:
                return str(test)

    def report(
        self,
        test: unittest.TestCase,
        marker: Markers,
        description: str | None = None,
        *,
        currently_running: Sequence[unittest.TestCase],
    ) -> None:
        raise NotImplementedError

    def report_start(
        self,
        test: unittest.TestCase,
        *,
        currently_running: Sequence[unittest.TestCase],
    ) -> None:
        return

    def report_still_running(self, still_running: dict[str, float]) -> None:
        return


class SimpleRenderer(BaseRenderer):
    def report(
        self,
        test: unittest.TestCase,
        marker: Markers,
        description: str | None = None,
        *,
        currently_running: Sequence[unittest.TestCase],
    ) -> None:
        click.echo(
            self.styles_map[marker.value](marker.value),
            nl=False,
            file=self.stream,
        )


class VerboseRenderer(BaseRenderer):
    fullnames: ClassVar[dict[Markers, str]] = {
        Markers.passed: "OK",
        Markers.errored: "ERROR",
        Markers.skipped: "SKIPPED",
        Markers.failed: "FAILED",
        Markers.xfailed: "expected failure",
        Markers.not_implemented: "not implemented",
        Markers.upassed: "unexpected success",
    }

    def _render_test(
        self, test: unittest.TestCase, marker: Markers, description: str | None
    ) -> str:
        test_title = self.format_test(test)
        if description:
            return f"{test_title}: {self.fullnames[marker]}: {description}"
        else:
            return f"{test_title}: {self.fullnames[marker]}"

    def report(
        self,
        test: unittest.TestCase,
        marker: Markers,
        description: str | None = None,
        *,
        currently_running: Sequence[unittest.TestCase],
    ) -> None:
        style = self.styles_map[marker.value]
        click.echo(
            style(self._render_test(test, marker, description)),
            file=self.stream,
        )

    def report_still_running(self, still_running: dict[str, float]) -> None:
        items = [f"{t} for {d:.02f}s" for t, d in still_running.items()]
        newline_join = "\n   "
        click.echo(f"still running:\n  {newline_join.join(items)}")


class MultiLineRenderer(BaseRenderer):
    FT_LABEL = "First few failed: "
    FT_MAX_LINES = 6

    R_LABEL = "Running: "
    R_MAX_LINES = 6

    def __init__(
        self,
        *,
        tests: Sequence[unittest.TestSuite | unittest.TestCase],
        stream: TextIO,
    ) -> None:
        super().__init__(tests=tests, stream=stream)

        self.total_tests = len(tests)
        self.completed_tests = 0

        test_modules = {test.__class__.__module__ for test in tests}
        max_test_module_len = max(
            (len(self._render_modname(name)) for name in test_modules),
            default=0,
        )
        self.first_col_width = max_test_module_len + 1  # 1 == len(' ')

        self.failed_tests: set[str] = set()

        self.buffer: collections.defaultdict[str, str] = (
            collections.defaultdict(str)
        )
        self.last_lines = -1
        self.max_lines = 0
        self.max_label_lines_rendered: collections.defaultdict[str, int] = (
            collections.defaultdict(int)
        )

    def report(
        self,
        test: unittest.TestCase,
        marker: Markers,
        description: str | None = None,
        *,
        currently_running: Sequence[unittest.TestCase],
    ) -> None:
        if marker in {Markers.failed, Markers.errored}:
            test_name = test.id().rpartition(".")[2]
            if " " in test_name:
                test_name = test_name.split(" ")[0]
            self.failed_tests.add(test_name)

        self.buffer[test.__class__.__module__] += marker.value
        self.completed_tests += 1
        self._render(currently_running)

    def report_start(
        self,
        test: unittest.TestCase,
        *,
        currently_running: Sequence[unittest.TestCase],
    ) -> None:
        self._render(currently_running)

    def report_still_running(self, still_running: dict[str, float]) -> None:
        # Still-running tests are already reported in normal repert
        return

    def _render_modname(self, name: str) -> str:
        return name.replace(".", "/") + ".py"

    def _color_second_column(
        self, line: str, style: Callable[[str], str]
    ) -> str:
        return line[: self.first_col_width] + style(
            line[self.first_col_width :]
        )

    def _render(self, currently_running: Sequence[unittest.TestCase]) -> None:
        def print_line(line: str) -> None:
            if len(line) < cols:
                line += " " * (cols - len(line))
            lines.append(line)

        def print_empty_line() -> None:
            print_line(" ")

        last_render = self.completed_tests == self.total_tests
        cols, rows = shutil.get_terminal_size()
        second_col_width = cols - self.first_col_width

        def _render_test_list(
            label: str,
            max_lines: int,
            tests: Collection[str],
            style: styles.Style,
        ) -> None:
            if (
                len(label) > self.first_col_width
                or cols - self.first_col_width <= 40
            ):
                return

            print_empty_line()

            line = f"{label}{' ' * (self.first_col_width - len(label))}"
            tests_lines = 1
            for testi, test in enumerate(tests, 1):
                last = testi == len(tests)
                test_str = test
                if not last:
                    test_str += ", "

                test_name_len = len(test_str)

                if len(line) + test_name_len < cols:
                    line += test_str

                else:
                    if tests_lines == max_lines:
                        if len(line) + 3 < cols:
                            line += "..."
                        break

                    else:
                        line += (cols - len(line)) * " "
                        line = self._color_second_column(line, style)
                        lines.append(line)

                        tests_lines += 1
                        line = self.first_col_width * " "

                        if len(line) + test_name_len > cols:
                            continue

                        line += test

            line += (cols - len(line)) * " "
            line = self._color_second_column(line, style)
            lines.append(line)

            # Prevent the rendered output from "jumping" up/down when we
            # render 2 lines worth of running tests just after we rendered
            # 3 lines.
            lkey = label.split(":", maxsplit=1)[0]
            # ^- We can't just use `label`, as we append extra information
            # to the "Running: (..)" label, so strip that
            for _ in range(self.max_label_lines_rendered[lkey] - tests_lines):
                lines.append(" " * cols)
            self.max_label_lines_rendered[lkey] = max(
                self.max_label_lines_rendered[lkey], tests_lines
            )

        clear_cmd = ""
        if self.last_lines > 0:
            # Move cursor up `last_lines` times.
            clear_cmd = f"\r\033[{self.last_lines}A"

        lines = []
        for mod, progress in self.buffer.items():
            line = self._render_modname(mod).ljust(self.first_col_width, " ")
            progress_str = progress
            while progress_str:
                second_col = progress_str[:second_col_width]
                second_col = second_col.ljust(second_col_width, " ")

                progress_str = progress_str[second_col_width:]

                # Apply styles *after* slicing and padding the string
                # (otherwise ANSI codes could be sliced in half).
                def style_char(match: re.Match[str]) -> str:
                    char = match.group(0)
                    return self.styles_map[char](char)

                second_col = re.sub(r"\S", style_char, second_col)

                lines.append(f"{line}{second_col}")

                if line[0] != " ":
                    line = " " * self.first_col_width

        if not last_render:
            if self.failed_tests:
                _render_test_list(
                    self.FT_LABEL,
                    self.FT_MAX_LINES,
                    self.failed_tests,
                    styles.marker_errored,
                )

            running_tests = []
            for test in currently_running:
                test_name = test.id().rpartition(".")[2]
                if " " in test_name:
                    test_name = test_name.split(" ")[0]
                running_tests.append(test_name)

            if not running_tests:
                running_tests.append("...")

            _render_test_list(
                self.R_LABEL + f"({len(currently_running)})",
                self.R_MAX_LINES,
                running_tests,
                styles.marker_passed,
            )

        print_empty_line()
        print_line(
            f"Progress: {self.completed_tests}/{self.total_tests} tests."
        )

        if self.max_lines > len(lines):
            for _ in range(self.max_lines - len(lines)):
                lines.insert(0, " " * cols)

        if not last_render:
            # If it's not the last test, check if our render buffer
            # requires more rows than currently visible.
            if len(lines) + 1 > rows:
                # Scroll the render buffer to the bottom and
                # cut the lines from the beginning, so that it
                # will fit the screen.
                #
                # We need to do this because we can't move the
                # cursor past the visible screen area, so if we
                # render more data than the screen can fit, we
                # will have lot's of garbage output.
                lines = lines[len(lines) + 1 - rows :]
                lines[0] = "^" * cols

        # Hide cursor.
        print("\033[?25l", end="", flush=True, file=self.stream)
        try:
            # Use `print` (not `click.echo`) because we want to
            # precisely control when the output is flushed.
            print(clear_cmd + "\n".join(lines), flush=False, file=self.stream)
        finally:
            # Show cursor.
            print("\033[?25h", end="", flush=True, file=self.stream)

        self.last_lines = len(lines)
        self.max_lines = max(self.last_lines, self.max_lines)


class ParallelTextTestResult(unittest.result.TestResult):
    def __init__(
        self,
        *,
        stream: TextIO,
        verbosity: int,
        catch_warnings: bool,
        tests: Sequence[unittest.TestCase],
        output_format: OutputFormat = OutputFormat.auto,
        failfast: bool = False,
        suite: ParallelTestSuite | SequentialTestSuite,
    ) -> None:
        super().__init__(stream, descriptions=False, verbosity=verbosity)
        self.verbosity = verbosity
        self.catch_warnings = catch_warnings
        self.failfast = failfast
        self.test_stats: list[
            tuple[unittest.TestCase, fixtures.StatsEntry]
        ] = []
        self.test_annotations: collections.defaultdict[
            unittest.TestCase, dict[str, Any]
        ] = collections.defaultdict(dict)
        self.errors: list[tuple[unittest.TestCase, results.OptExcInfo]] = []  # type: ignore [assignment]
        self.warnings: list[tuple[unittest.TestCase, str]] = []
        self.notImplemented: list[
            tuple[unittest.TestCase, results.OptExcInfo]
        ] = []
        self.currently_running: dict[unittest.TestCase, float] = {}
        self.current_pids: dict[int, unittest.TestCase] = {}
        # An index of all seen warnings to keep track
        # of repeated warnings.
        self._warnings: dict[
            tuple[str, str, int], warnings.WarningMessage
        ] = {}
        self.suite = suite
        self.ren: BaseRenderer

        if output_format is OutputFormat.verbose or (
            output_format is OutputFormat.auto and self.verbosity > 1
        ):
            self.ren = VerboseRenderer(tests=tests, stream=stream)
        elif output_format is OutputFormat.stacked or (
            output_format is OutputFormat.auto
            and stream.isatty()
            and shutil.get_terminal_size()[0] > 60
            and os.name != "nt"
        ):
            self.ren = MultiLineRenderer(tests=tests, stream=stream)
        else:
            self.ren = SimpleRenderer(tests=tests, stream=stream)

    def report_progress(
        self,
        test: unittest.TestCase,
        marker: Markers,
        description: str | None = None,
    ) -> None:
        self.currently_running.pop(test, None)
        self.ren.report(
            test,
            marker,
            description,
            currently_running=list(self.currently_running),
        )

    def report_still_running(self) -> None:
        now = time.monotonic()
        still_running = {}
        for test, start in self.currently_running.items():
            running_for = now - start
            if running_for > 5.0:
                key = str(test)
                if test in self.test_annotations and (
                    pid := self.test_annotations[test].get("runner-pid")
                ):
                    key = f"{key} (pid={pid})"

                still_running[key] = running_for
        if still_running:
            self.ren.report_still_running(still_running)

    def record_test_stats(
        self, test: unittest.TestCase, stats: fixtures.StatsEntry
    ) -> None:
        self.test_stats.append((test, stats))

    def annotate_test(
        self, test: unittest.TestCase, annotations: dict[str, Any]
    ) -> None:
        self.test_annotations[test].update(annotations)

    def get_test_annotations(
        self, test: unittest.TestCase
    ) -> dict[str, Any] | None:
        return self.test_annotations.get(test)

    def _exc_info_to_string(
        self, err: results.OptExcInfo, test: unittest.TestCase
    ) -> results.OptExcInfo:
        # Errors are serialized in the worker.
        return err

    def getDescription(self, test: unittest.TestCase) -> str:
        return self.ren.format_test(test)

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self.currently_running[test] = time.monotonic()
        self.ren.report_start(
            test, currently_running=list(self.currently_running)
        )
        if test in self.test_annotations and (
            pid := self.test_annotations[test].get("runner-pid")
        ):
            self.current_pids[pid] = test

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self.report_progress(test, Markers.passed)

    def addError(
        self, test: unittest.TestCase, err: results.OptExcInfo
    ) -> None:
        super().addError(test, err)
        self.report_progress(test, Markers.errored)
        if self.failfast:
            self.suite.stop_requested = True

    def addFailure(
        self, test: unittest.TestCase, err: results.OptExcInfo
    ) -> None:
        super().addFailure(test, err)
        self.report_progress(test, Markers.failed)
        if self.failfast:
            self.suite.stop_requested = True

    def addSubTest(
        self,
        test: unittest.TestCase,
        subtest: unittest.TestCase,
        err: results.OptExcInfo | None,
    ) -> None:
        if err is not None:
            self.errors.append((subtest, self._exc_info_to_string(err, test)))
            self._mirrorOutput = True

            self.ren.report(
                subtest,
                Markers.errored,
                currently_running=list(self.currently_running),
            )
            if self.failfast:
                self.suite.stop_requested = True

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self.report_progress(test, Markers.skipped)

    def addExpectedFailure(
        self,
        test: unittest.TestCase,
        err: results.OptExcInfo,
    ) -> None:
        method = getattr(test, test._testMethodName)
        xfail = _is_expecting_failure(method) or _is_expecting_failure(test)
        if xfail is None:
            # This should not happen, at the very least
            # __unittest_expecting_failure__ should have been set
            # report it as error
            super().addError(test, err)
            marker = Markers.errored
            reason = None
        elif xfail.not_implemented:
            marker = Markers.not_implemented
            reason = xfail.reason
            self.notImplemented.append(
                (test, self._exc_info_to_string(err, test))
            )
        else:
            marker = Markers.xfailed
            reason = xfail.reason
            is_fail = _is_assert_failure(err)
            if (xfail.expect_failure and is_fail) or (
                xfail.expect_error and not is_fail
            ):
                super().addExpectedFailure(test, err)
            elif is_fail:
                super().addFailure(test, err)
            else:
                super().addError(test, err)

        self.report_progress(test, marker, reason)

    def addUnexpectedSuccess(self, test: unittest.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        self.report_progress(test, Markers.upassed)

    def addWarning(
        self,
        test: unittest.TestCase,
        wmsg: warnings.WarningMessage,
    ) -> None:
        if not self.catch_warnings:
            return

        key = str(wmsg.message), wmsg.filename, wmsg.lineno

        if key not in self._warnings:
            self._warnings[key] = wmsg
            self.warnings.append(
                (
                    test,
                    warnings.formatwarning(
                        wmsg.message,
                        wmsg.category,
                        wmsg.filename,
                        wmsg.lineno,
                        wmsg.line,
                    ),
                )
            )

    def wasSuccessful(self) -> bool:
        # Overload TestResult.wasSuccessful to ignore unexpected successes
        return len(self.failures) == len(self.errors) == 0


class ParallelTextTestRunner:
    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        num_workers: int = 1,
        verbosity: int = 1,
        output_format: OutputFormat = OutputFormat.auto,
        warnings: bool = True,
        failfast: bool = False,
        shuffle: bool = False,
        backend_dsn: str | None = None,
        data_dir: str | None = None,
        try_cached_db: bool = False,
        use_data_dir_dbs: bool = False,
    ) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.num_workers = num_workers
        self.verbosity = verbosity
        self.warnings = warnings
        self.failfast = failfast
        self.shuffle = shuffle
        self.output_format = output_format
        self.backend_dsn = backend_dsn
        self.data_dir = data_dir
        self.use_data_dir_dbs = use_data_dir_dbs
        self.try_cached_db = try_cached_db

    def run(
        self,
        test: Any,
        selected_shard: int,
        total_shards: int,
        running_times_log_file: TextIO | None,
    ) -> results.TestResult:
        session_start = time.monotonic()
        cases = loader.get_test_cases([test])
        stats = {}
        if running_times_log_file:
            running_times_log_file.seek(0)
            stats = {
                k: (float(v), int(c))
                for k, v, c in csv.reader(running_times_log_file)
            }
        cases = loader.get_cases_by_shard(
            cases,
            selected_shard,
            total_shards,
            self.verbosity,
            stats,
        )
        setup = fixtures.get_test_cases_setup(list(cases.keys()))
        worker_init = None
        bootstrap_time_taken = 0.0
        tests_time_taken = 0.0
        result: ParallelTextTestResult | None = None
        cluster: loader.Instance | None = None
        tempdir = None
        setup_stats = []

        try:
            if setup:
                if self.verbosity >= 1:
                    self._echo(
                        "Populating test databases... ",
                        fg="white",
                        nl=False,
                    )

                if self.verbosity > 1:
                    self._echo(
                        "\n -> Bootstrapping Gel instance...",
                        fg="white",
                        nl=False,
                    )

                test_case, _, _ = next(iter(setup))

                data_dir = self.data_dir
                cluster = test_case.make_test_instance(
                    backend_dsn=self.backend_dsn,
                    cleanup_atexit=False,
                    data_dir=data_dir,
                )

                async def _setup() -> fixtures.Stats:
                    cache_info = test_case.get_cache_info(cluster)
                    cache_path = None
                    if cache_info is not None:
                        fname = f"{cache_info[1]}-test-dbs.tar"
                        cache_path = cache_info[0] / fname

                    if (
                        self.try_cached_db
                        and cache_path is not None
                        and cache_path.is_file()
                    ):
                        if self.verbosity >= 1:
                            self._echo(
                                f"(using DB cache from {cache_path}) ",
                                fg="white",
                                nl=False,
                            )

                        data_dir = tempfile.mkdtemp(prefix="edb-test-c-")

                        # We shell out to tar with subprocess instead of using
                        # tarfile because it is quite a bit faster.
                        subprocess.check_call(
                            ("tar", "xf", cache_path, "--strip-components=1"),
                            cwd=data_dir,
                        )

                        cluster.set_data_dir(pathlib.Path(data_dir))

                    await cluster.start()

                    if self.verbosity > 1:
                        self._echo(" OK")

                    conn = cluster.get_connect_args()

                    if not cluster.has_create_database():
                        return []

                    if not cluster.has_create_role():
                        for case in cases:
                            case.is_superuser = False  # type: ignore [attr-defined]

                    stats = await fixtures.setup_test_cases(
                        cases,
                        cluster,
                        num_jobs=self.num_workers,
                        verbose=self.verbosity > 1,
                        try_cached_db=(
                            self.try_cached_db or self.use_data_dir_dbs
                        ),
                    )
                    if self.try_cached_db and any(
                        not x[1].get("cached", False) for x in stats
                    ):
                        # We stop the cluster before making a cache of
                        # the data directory. This isn't strictly
                        # necessary, but it speeds up startup when
                        # restoring a cached directory, since postgres
                        # needs to go through recovery if the shutdown
                        # wasn't clean.
                        cluster.stop()
                        if self.verbosity > 1 and cache_path is not None:
                            self._echo(
                                f"\n -> Writing DB cache to {cache_path} ...",
                                fg="white",
                                nl=False,
                            )
                        if cache_path is not None:
                            subprocess.check_output(
                                ("tar", "cf", cache_path, "."),
                                cwd=cluster.get_data_dir(),
                                stderr=subprocess.STDOUT,
                            )
                        await cluster.start(port=conn["port"])

                    return stats

                setup_stats = asyncio.run(_setup())
                bootstrap_time_taken = time.monotonic() - session_start

                if self.verbosity >= 1:
                    self._echo("OK")

                _populate_gel_instance_env(cluster, self.backend_dsn)

            start = time.monotonic()

            all_tests = list(
                itertools.chain.from_iterable(
                    tests for tests in cases.values()
                )
            )

            suite: ParallelTestSuite | SequentialTestSuite

            if self.num_workers > 1:
                suite = ParallelTestSuite(
                    self._sort_tests(cases),
                    num_workers=self.num_workers,
                    worker_init=worker_init,
                )
            else:
                suite = SequentialTestSuite(
                    self._sort_tests(cases),
                    worker_init=worker_init,
                )

            result = ParallelTextTestResult(
                stream=self.stream,
                verbosity=self.verbosity,
                catch_warnings=self.warnings,
                failfast=self.failfast,
                output_format=self.output_format,
                tests=all_tests,
                suite=suite,
            )
            unittest.signals.registerResult(result)

            self._echo()
            suite.run(result)

            if running_times_log_file:
                for test_obj, stat in result.test_stats + setup_stats:
                    name = str(test_obj)
                    t = stat["running-time"]
                    at, c = stats.get(name, (0, 0))
                    stats[name] = (at + (t - at) / (c + 1), c + 1)
                running_times_log_file.seek(0)
                running_times_log_file.truncate()
                writer = csv.writer(running_times_log_file)
                for k, v in stats.items():
                    writer.writerow((k, *v))
            tests_time_taken = time.monotonic() - start

        except KeyboardInterrupt:
            raise

        finally:
            if self.verbosity == 1:
                self._echo()

            if tempdir is not None:
                tempdir.cleanup()

            if setup and cluster is not None:
                test_case, _, _ = next(iter(setup))
                self._echo()
                self._echo("Shutting down test cluster... ", nl=False)
                test_case.shutdown_test_instance(
                    cluster,
                    destroy=self.data_dir is None,
                )
                self._echo("OK.")

        return results.collect_result_data(
            result, bootstrap_time_taken, tests_time_taken
        )

    def _echo(self, s: str = "", **kwargs: Any) -> None:
        if self.verbosity > 0:
            click.secho(s, file=self.stream, **kwargs)

    def _sort_tests(
        self,
        cases: Mapping[type[unittest.TestCase], Sequence[unittest.TestCase]],
    ) -> list[unittest.TestCase | unittest.TestSuite]:
        serialized_suites: dict[
            type[unittest.TestCase], unittest.TestSuite
        ] = {}
        exclusive_suites: set[type[unittest.TestCase]] = set()
        exclusive_tests: list[unittest.TestCase] = []

        for casecls, tests in cases.items():
            gg = getattr(casecls, "get_parallelism_granularity", None)
            granularity = gg() if gg is not None else "default"

            if granularity == "suite":
                serialized_suites[casecls] = unittest.TestSuite(tests)
            elif granularity == "system":
                exclusive_tests.extend(tests)
                exclusive_suites.add(casecls)

        test_list: list[unittest.TestCase | unittest.TestSuite] = list(
            itertools.chain(
                serialized_suites.values(),
                itertools.chain.from_iterable(
                    tests
                    for casecls, tests in cases.items()
                    if (
                        casecls not in serialized_suites
                        and casecls not in exclusive_suites
                    )
                ),
                [unittest.TestSuite(exclusive_tests)],
            )
        )

        if self.shuffle:
            random.shuffle(test_list)

        return test_list


# Disable pickling of traceback objects in multiprocessing.
# Test errors' tracebacks are serialized manually by
# `TestReesult._exc_info_to_string()`.  Therefore we need
# to make sure that some random __traceback__ attribute
# doesn't crash the test results queue.
multiprocessing.reduction.ForkingPickler.register(
    types.TracebackType, lambda o: (_restore_Traceback, ())
)


def _restore_Traceback() -> None:
    return None
