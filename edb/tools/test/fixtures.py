from __future__ import annotations
from typing import TYPE_CHECKING, Protocol
from typing_extensions import TypeAliasType, TypedDict
from typing import Required

import asyncio
import time
import unittest

import gel

from . import loader

if TYPE_CHECKING:
    from collections.abc import Iterable


StatsEntry = TypedDict(
    "StatsEntry",
    {"running-time": Required[float], "cached": bool},
    total=False,
)


Stats = TypeAliasType("Stats", list[tuple[str, StatsEntry]])


def _quote_ident(string: str) -> str:
    return "`" + string.replace("`", "``") + "`"


def get_test_cases_setup(
    cases: Iterable[type[unittest.TestCase | loader.DatabaseTestCaseProto]],
) -> list[tuple[type[loader.DatabaseTestCaseProto], str, str]]:
    result: list[tuple[type[loader.DatabaseTestCaseProto], str, str]] = []

    for case in cases:
        if issubclass(case, loader.DatabaseTestCaseProto):
            try:
                setup_script = case.get_setup_script()
            except unittest.SkipTest:
                continue

            dbname = case.get_database_name()
            result.append((case, dbname, setup_script))

    return result


class _DBSetup(Protocol):
    @staticmethod
    async def __call__(
        *,
        instance: loader.Instance,
        test_case: loader.DatabaseTestCaseProto,
        dbname: str,
        setup_script: str,
        stats: Stats,
        try_cached_db: bool,
    ) -> None: ...


async def setup_test_cases(
    cases: Iterable[type[unittest.TestCase | loader.DatabaseTestCaseProto]],
    instance: loader.Instance,
    *,
    num_jobs: int = 1,
    try_cached_db: bool = False,
    skip_empty_databases: bool = False,
    verbose: bool = False,
) -> Stats:
    setup = get_test_cases_setup(cases)

    stats: Stats = []
    if num_jobs == 1:
        # Special case for --jobs=1
        for case, dbname, setup_script in setup:
            if skip_empty_databases and not setup_script:
                continue
            await _setup_database(
                instance=instance,
                test_case=case,
                dbname=dbname,
                setup_script=setup_script,
                stats=stats,
                try_cached_db=try_cached_db,
            )
            if verbose:
                pass
    else:
        async with asyncio.TaskGroup() as g:
            # Use a semaphore to limit the concurrency of bootstrap
            # tasks to the number of jobs (bootstrap is heavy, having
            # more tasks than `--jobs` won't necessarily make
            # things faster.)
            sem = asyncio.BoundedSemaphore(num_jobs)

            async def controller(
                coro: _DBSetup,
                *,
                instance: loader.Instance,
                dbname: str,
                test_case: loader.DatabaseTestCaseProto,
                setup_script: str,
                stats: Stats,
                try_cached_db: bool,
            ) -> None:
                async with sem:
                    await coro(
                        instance=instance,
                        dbname=dbname,
                        test_case=test_case,
                        setup_script=setup_script,
                        stats=stats,
                        try_cached_db=try_cached_db,
                    )
                    if verbose:
                        pass

            for case, dbname, setup_script in setup:
                if skip_empty_databases and not setup_script:
                    continue

                g.create_task(
                    controller(
                        _setup_database,
                        instance=instance,
                        dbname=dbname,
                        test_case=case,
                        setup_script=setup_script,
                        stats=stats,
                        try_cached_db=try_cached_db,
                    )
                )
    return stats


async def _setup_database(
    *,
    instance: loader.Instance,
    test_case: loader.DatabaseTestCaseProto,
    dbname: str,
    setup_script: str,
    stats: Stats,
    try_cached_db: bool,
) -> None:
    start_time = time.monotonic()

    args = {**instance.get_connect_args()}

    try:
        admin_conn = test_case.make_async_test_client(
            instance=instance, **args
        )
        await admin_conn.ensure_connected()
    except Exception as ex:
        raise RuntimeError(
            f"exception during creation of {dbname!r} test DB; "
            f"could not connect to test instance: {type(ex).__name__}({ex})"
        ) from ex

    try:
        await admin_conn.execute(f"CREATE DATABASE {_quote_ident(dbname)};")
    except gel.DuplicateDatabaseDefinitionError:
        # Eh, that's fine
        # And, if we are trying to use a cache of the database, assume
        # the db is populated and return.
        if try_cached_db:
            elapsed = time.monotonic() - start_time
            stats.append(
                ("setup::" + dbname, {"running-time": elapsed, "cached": True})
            )
            return
    except Exception as ex:
        raise RuntimeError(
            f"exception during creation of {dbname!r} test DB: "
            f"{type(ex).__name__}({ex})"
        ) from ex
    finally:
        await admin_conn.aclose()

    args["database"] = dbname
    dbconn = test_case.make_async_test_client(instance=instance, **args)
    try:
        if setup_script:
            await test_case.execute_retrying(dbconn, setup_script)
    except Exception as ex:
        raise RuntimeError(
            f"exception during initialization of {dbname!r} test DB: "
            f"{type(ex).__name__}({ex})"
        ) from ex
    finally:
        await dbconn.aclose()

    elapsed = time.monotonic() - start_time
    stats.append(
        ("setup::" + dbname, {"running-time": elapsed, "cached": False})
    )
