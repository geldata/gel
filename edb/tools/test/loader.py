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
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from typing_extensions import TypeAliasType

import heapq
import pathlib
import re
import unittest


if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


Instance = TypeAliasType("Instance", Any)
Client = TypeAliasType("Client", Any)


@runtime_checkable
class DatabaseTestCaseProto(Protocol):
    @classmethod
    def get_setup_script(cls) -> str: ...

    @classmethod
    def get_database_name(cls) -> str: ...

    @classmethod
    async def make_test_instance(
        cls,
        *,
        backend_dsn: str | None = None,
        cleanup_atexit: bool = False,
        data_dir: str | None = None,
    ) -> Instance: ...

    @classmethod
    def shutdown_test_instance(
        cls,
        instance: Instance,
        *,
        destroy: bool = False,
    ) -> None: ...

    @classmethod
    def get_cache_dir(cls) -> pathlib.Path: ...

    @classmethod
    def make_async_test_client(cls, **kwargs: Any) -> Client: ...

    @classmethod
    async def execute_retrying(cls, dbconn: Client, script: str) -> None: ...


class TestLoader(unittest.TestLoader):
    include: Sequence[re.Pattern] | None
    exclude: Sequence[re.Pattern] | None

    def __init__(
        self,
        *,
        verbosity: int = 1,
        exclude: Sequence[str] = (),
        include: Sequence[str] = (),
        progress_cb: Callable[[int, int], None] | None = None,
    ):
        super().__init__()
        self.verbosity = verbosity

        if include:
            self.include = [re.compile(r) for r in include]
        else:
            self.include = None

        if exclude:
            self.exclude = [re.compile(r) for r in exclude]
        else:
            self.exclude = None

        self.progress_cb = progress_cb

    def getTestCaseNames(self, caseclass):
        names = super().getTestCaseNames(caseclass)
        unfiltered_len = len(names)
        cname = caseclass.__name__

        if self.include or self.exclude:
            if self.include:
                names = filter(
                    lambda n: (
                        any(r.search(n) for r in self.include)
                        or any(r.search(f'{cname}.{n}') for r in self.include)
                    ),
                    names,
                )

            if self.exclude:
                names = filter(
                    lambda n: (
                        not any(r.search(n) for r in self.exclude)
                        and not any(
                            r.search(f'{cname}.{n}') for r in self.exclude
                        )
                    ),
                    names,
                )

            names = list(names)

        if self.progress_cb:
            self.progress_cb(len(names), unfiltered_len)

        return names


def _add_test(result, test):
    # test is a tuple of the same test method that may zREPEAT
    cls = type(test[0])
    try:
        methods, repeat_methods = result[cls]
    except KeyError:
        # put zREPEAT tests in a separate list
        methods = []
        repeat_methods = []
        result[cls] = methods, repeat_methods

    methods.append(test[0])
    if len(test) > 1:
        repeat_methods.extend(test[1:])


def _merge_results(result):
    # make sure all the zREPEAT tests comes in the end
    return {k: v[0] + v[1] for k, v in result.items()}


def _get_test_cases(tests):
    result = {}

    for test in tests:
        if isinstance(test, unittest.TestSuite):
            result.update(_get_test_cases(test._tests))
        elif not getattr(test, '__unittest_skip__', False):
            _add_test(result, (test,))

    return result


def get_test_cases(tests):
    return _merge_results(_get_test_cases(tests))


def get_cases_by_shard(cases, selected_shard, total_shards, verbosity, stats):
    if total_shards <= 1:
        return cases

    selected_shard -= 1  # starting from 0
    new_test_est = 0.1  # default estimate if test is not found in stats
    new_setup_est = 1  # default estimate if setup is not found in stats

    # For logging
    total_tests = 0
    selected_tests = 0
    total_est = 0
    selected_est = 0

    # Priority queue of tests grouped by setup script ordered by estimated
    # running time of the groups. Order of tests within cases is preserved.
    tests_by_setup = []

    # Priority queue of individual tests ordered by estimated running time.
    tests_with_est = []

    # Prepare the source heaps
    setup_count = 0
    for case, tests in cases.items():
        # Extract zREPEAT tests and attach them to their first runs
        combined = {}
        for test in tests:
            test_name = str(test)
            orig_name = test_name.replace('test_zREPEAT', 'test')
            if orig_name == test_name:
                if test_name in combined:
                    combined[test_name] = (test, *combined[test_name])
                else:
                    combined[test_name] = (test,)
            else:
                if orig_name in combined:
                    combined[orig_name] = (*combined[orig_name], test)
                else:
                    combined[orig_name] = (test,)

        setup_script_getter = getattr(case, 'get_setup_script', None)
        if setup_script_getter and combined:
            tests_per_setup = []
            est_per_setup = setup_est = stats.get(
                'setup::' + case.get_database_name(),
                (new_setup_est, 0),
            )[0]
            for test_name, test in combined.items():
                total_tests += len(test)
                est = stats.get(test_name, (new_test_est, 0))[0] * len(test)
                est_per_setup += est
                tests_per_setup.append((est, test))
            heapq.heappush(
                tests_by_setup,
                (-est_per_setup, setup_count, setup_est, tests_per_setup),
            )
            setup_count += 1
            total_est += est_per_setup
        else:
            for test_name, test in combined.items():
                total_tests += len(test)
                est = stats.get(test_name, (new_test_est, 0))[0] * len(test)
                total_est += est
                heapq.heappush(tests_with_est, (-est, total_tests, test))

    target_est = total_est / total_shards  # target running time of one shard
    shards_est = [(0, shard, set()) for shard in range(total_shards)]
    cases = {}  # output
    setup_to_alloc = set(range(setup_count))  # tracks first run of each setup

    # Assign per-setup tests first
    while tests_by_setup:
        remaining_est, setup_id, setup_est, tests = heapq.heappop(
            tests_by_setup,
        )
        est_acc, current, setups = heapq.heappop(shards_est)

        # Add setup time
        if setup_id not in setups:
            setups.add(setup_id)
            est_acc += setup_est
            if current == selected_shard:
                selected_est += setup_est
            if setup_id in setup_to_alloc:
                setup_to_alloc.remove(setup_id)
            else:
                # This means one more setup for the overall test run
                target_est += setup_est / total_shards

        # Add as much tests from this group to current shard as possible
        while tests:
            est, test = tests.pop(0)
            est_acc += est  # est is a positive number
            remaining_est += est  # remaining_est is a negative number

            if current == selected_shard:
                # Add the test to the result
                _add_test(cases, test)
                selected_tests += len(test)
                selected_est += est

            if est_acc >= target_est and -remaining_est > setup_est * 2:
                # Current shard is full and the remaining tests would take more
                # time than their setup, then add the tests back to the heap so
                # that we could add them to another shard
                heapq.heappush(
                    tests_by_setup,
                    (remaining_est, setup_id, setup_est, tests),
                )
                break

        heapq.heappush(shards_est, (est_acc, current, setups))

    # Assign all non-setup tests, but leave the last shard for everything else
    setups = set()
    while tests_with_est and len(shards_est) > 1:
        est, _, test = heapq.heappop(tests_with_est)  # est is negative
        est_acc, current, setups = heapq.heappop(shards_est)
        est_acc -= est

        if current == selected_shard:
            # Add the test to the result
            _add_test(cases, test)
            selected_tests += len(test)
            selected_est -= est

        if est_acc >= target_est:
            # The current shard is full
            if current == selected_shard:
                # End early if the selected shard is full
                break
        else:
            # Only add the current shard back to the heap if it's not full
            heapq.heappush(shards_est, (est_acc, current, setups))

    else:
        # Add all the remaining tests to the first remaining shard if any
        while shards_est:
            est_acc, current, setups = heapq.heappop(shards_est)
            if current == selected_shard:
                for est, _, test in tests_with_est:
                    _add_test(cases, test)
                    selected_tests += len(test)
                    selected_est -= est
                break
            tests_with_est.clear()  # should always be empty already here

    if verbosity >= 1:
        print(
            f'Running {selected_tests}/{total_tests} tests for shard '
            f'#{selected_shard + 1} out of {total_shards} shards, '
            f'estimate: {int(selected_est / 60)}m {int(selected_est % 60)}s'
            f' / {int(total_est / 60)}m {int(total_est % 60)}s, '
            f'{len(setups)}/{setup_count} databases to setup.'
        )
    return _merge_results(cases)
