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
from typing import TYPE_CHECKING, TextIO

import contextlib
import importlib.util
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

import click

if TYPE_CHECKING:
    import coverage
else:
    try:
        import coverage
    except ImportError:
        coverage = None

from .decorators import async_timeout
from .decorators import not_implemented
from .decorators import _xfail
from .decorators import xfail
from .decorators import xerror
from .decorators import skip

from . import cov
from . import loader
from . import mproc_fixes
from . import runner
from . import styles
from . import results

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


__all__ = (
    "_xfail",
    "async_timeout",
    "not_implemented",
    "skip",
    "xerror",
    "xfail",
)


@click.argument("files", nargs=-1, metavar="[file or directory]...")
@click.option("-v", "--verbose", is_flag=True, help="increase verbosity")
@click.option("-q", "--quiet", is_flag=True, help="decrease verbosity")
@click.option("--debug", is_flag=True, help="output internal debug logs")
@click.option(
    "--output-format",
    type=click.Choice(runner.OutputFormat),
    help="test progress output style",
    default=runner.OutputFormat.auto,
)
@click.option(
    "--warnings/--no-warnings",
    help="enable or disable warnings (enabled by default)",
    default=True,
)
@click.option(
    "-j",
    "--jobs",
    type=int,
    default=0,
    help="number of parallel processes to use, default is 0, which "
    "means choose automatically based on the number of "
    "available CPU cores",
)
@click.option(
    "-s",
    "--shard",
    type=str,
    default="1/1",
    help="run tests in shards (current/total)",
)
@click.option(
    "-k",
    "--include",
    type=str,
    multiple=True,
    metavar="REGEXP",
    help="only run tests which match the given regular expression",
)
@click.option(
    "-e",
    "--exclude",
    type=str,
    multiple=True,
    metavar="REGEXP",
    help="do not run tests which match the given regular expression",
)
@click.option(
    "-x",
    "--failfast",
    is_flag=True,
    help="stop tests after a first failure/error",
)
@click.option(
    "--shuffle", is_flag=True, help="shuffle the order in which tests are run"
)
@click.option(
    "--repeat",
    type=int,
    default=1,
    help="repeat tests N times or until first unsuccessful run",
)
@click.option(
    "--cov",
    type=str,
    multiple=True,
    help="package name to measure code coverage for, "
    "can be specified multiple times "
    "(e.g --cov edb.common --cov edb.server)",
)
@click.option(
    "--running-times-log",
    "running_times_log_file",
    type=click.File("a+"),
    metavar="FILEPATH",
    help="maintain a running time log file at FILEPATH",
)
@click.option(
    "--result-log",
    type=str,
    metavar="FILEPATH",
    help=(
        "write the test result to a log file. If the path contains "
        "%TIMESTAMP%, it will be replaced by ISO8601 date and time. "
        "Empty string means not to write the log at all."
    ),
    default="build/test-results/%TIMESTAMP%.json",
)
@click.option(
    "--include-unsuccessful",
    is_flag=True,
    help="include the tests that were not successful in the last run",
)
@click.option(
    "--list", "list_tests", is_flag=True, help="list all the tests and exit"
)
@click.option(
    "--backend-dsn",
    type=str,
    help="use the specified backend cluster instead of starting a "
    "temporary local one.",
)
@click.option(
    "--use-db-cache",
    is_flag=True,
    help="attempt to use a cache of the test databases (unsound!)",
)
@click.option("--data-dir", type=str, help="use a specified data dir")
@click.option(
    "--use-data-dir-dbs",
    is_flag=True,
    help="attempt to use setup databases in the data-dir",
)
def test(
    *,
    files: list[str],
    jobs: int,
    shard: str,
    include: list[str],
    exclude: list[str],
    verbose: bool,
    quiet: bool,
    debug: bool,
    output_format: runner.OutputFormat,
    warnings: bool,
    failfast: bool,
    shuffle: bool,
    cov: list[str],
    repeat: int,
    running_times_log_file: TextIO | None,
    list_tests: bool,
    backend_dsn: str | None,
    use_db_cache: bool,
    data_dir: str | None,
    use_data_dir_dbs: bool,
    result_log: str,
    include_unsuccessful: bool,
) -> None:
    """Run Gel test suite.

    Discovers and runs tests in the specified files or directories.
    If no files or directories are specified, current directory is assumed.
    """
    if quiet:
        if verbose:
            click.secho(
                "Warning: both --quiet and --verbose are "
                "specified, assuming --quiet.",
                fg="yellow",
            )
        verbosity = 0
    elif verbose:
        verbosity = 2
    else:
        verbosity = 1

    if jobs == 0:
        jobs = os.cpu_count() or 1

    mproc_fixes.patch_multiprocessing(debug=debug)

    if verbosity > 1 and output_format is runner.OutputFormat.stacked:
        click.secho(
            "Error: cannot use stacked output format in verbose mode.",
            fg="red",
        )
        sys.exit(1)

    if repeat < 1:
        click.secho(
            "Error: --repeat must be a positive non-zero number.", fg="red"
        )
        sys.exit(1)

    if not files:
        cwd = os.path.abspath(os.getcwd())
        if os.path.exists(os.path.join(cwd, "tests")):
            files = ["tests"]
        else:
            click.secho(
                'Error: no test path specified and no "tests" directory found',
                fg="red",
            )
            sys.exit(1)

    for file in files:
        if not os.path.exists(file):
            click.secho(f"Error: test path {file!r} does not exist", fg="red")
            sys.exit(1)

    try:
        selected_shard, total_shards = map(int, shard.split("/"))
    except Exception:
        click.secho(f"Error: --shard {shard} must match format e.g. 2/5")
        sys.exit(1)

    if selected_shard < 1 or selected_shard > total_shards:
        click.secho(f"Error: --shard {shard} is out of bound")
        sys.exit(1)

    def run() -> int:
        return _run(
            include=include,
            exclude=exclude,
            verbosity=verbosity,
            files=files,
            jobs=jobs,
            output_format=output_format,
            warnings=warnings,
            failfast=failfast,
            shuffle=shuffle,
            repeat=repeat,
            selected_shard=selected_shard,
            total_shards=total_shards,
            running_times_log_file=running_times_log_file,
            list_tests=list_tests,
            backend_dsn=backend_dsn,
            try_cached_db=use_db_cache,
            data_dir=data_dir,
            use_data_dir_dbs=use_data_dir_dbs,
            result_log=result_log,
            include_unsuccessful=include_unsuccessful,
        )

    if cov:
        for pkg in cov:
            if "\\" in pkg or "/" in pkg or pkg.endswith(".py"):
                click.secho(
                    f"Error: --cov argument {pkg!r} looks like a path, "
                    f"expected a Python package name",
                    fg="red",
                )
                sys.exit(1)

        with _coverage_wrapper(cov):
            result = run()
    else:
        result = run()

    sys.exit(result)


def _modules_parent_path(modnames: list[str]) -> pathlib.Path:
    origins: set[str] = set()
    for modname in modnames:
        spec = importlib.util.find_spec(modname)
        if spec is not None and spec.origin and spec.has_location:
            origins.add(spec.origin)

    return pathlib.Path(os.path.commonpath(origins))


def _find_pyproject_toml(path: pathlib.Path) -> pathlib.Path:
    for modpath in [path, *path.parents]:
        cov_rc = modpath / "pyproject.toml"
        if cov_rc.exists():
            return cov_rc

    raise RuntimeError("cannot locate the pyproject.toml file")


@contextlib.contextmanager
def _coverage_wrapper(paths: list[str]) -> Iterator[None]:
    if coverage is None:
        click.secho(
            'Error: "coverage" package is missing, cannot run tests with --cov'
        )
        sys.exit(1)

    cov_rc = _find_pyproject_toml(_modules_parent_path(paths))

    with tempfile.TemporaryDirectory() as td:
        cov_config = cov.CoverageConfig(
            paths=list(paths), config=str(cov_rc), datadir=td
        )
        cov_config.save_to_environ()

        main_cov = cov_config.new_coverage_object()
        main_cov.start()

        try:
            yield
        finally:
            main_cov.stop()
            main_cov.save()

            covfile = str(pathlib.Path(td) / ".coverage")
            data = coverage.CoverageData(covfile)

            with os.scandir(td) as it:
                for entry in it:
                    new_data = coverage.CoverageData(entry.path)
                    new_data.read()
                    data.update(new_data)

            data.write()
            report_cov = cov_config.new_custom_coverage_object(
                config_file=str(cov_rc),
                data_file=covfile,
            )
            report_cov.load()
            click.secho("Coverage:")
            report_cov.report()
            # store the coverage file in cwd, so it can be used to produce
            # additional reports with coverage cli
            shutil.copy(covfile, ".")


def _run(
    *,
    include: list[str],
    exclude: list[str],
    verbosity: int,
    files: list[str],
    jobs: int,
    output_format: runner.OutputFormat,
    warnings: bool,
    failfast: bool,
    shuffle: bool,
    repeat: int,
    selected_shard: int,
    total_shards: int,
    running_times_log_file: TextIO | None,
    list_tests: bool,
    backend_dsn: str | None,
    try_cached_db: bool,
    data_dir: str | None,
    use_data_dir_dbs: bool,
    result_log: str,
    include_unsuccessful: bool,
) -> int:
    suite = unittest.TestSuite()

    total = 0
    total_unfiltered = 0

    if verbosity > 0:

        def progress_callback(n: int, unfiltered_n: int) -> None:
            nonlocal total, total_unfiltered
            total += n
            total_unfiltered += unfiltered_n
            click.echo(
                styles.status(
                    f"Collected {total}/{total_unfiltered} tests.\r"
                ),
                nl=False,
                err=list_tests,
            )

        update_progress: Callable[[int, int], None] | None = progress_callback
    else:
        update_progress = None

    if include_unsuccessful and result_log:
        unsuccessful = results.read_unsuccessful(result_log)
        include = list(include) + unsuccessful + ["a_non_existing_test"]

    test_loader = loader.TestLoader(
        verbosity=verbosity,
        exclude=exclude,
        include=include,
        progress_cb=update_progress,
    )

    for file in files:
        if not os.path.exists(file) and verbosity > 0:
            click.echo(
                styles.warning(f"Warning: {file}: no such file or directory.")
            )

        if os.path.isdir(file):
            tests = test_loader.discover(file)
        else:
            tests = test_loader.discover(
                os.path.dirname(file), pattern=os.path.basename(file)
            )

        suite.addTest(tests)

    if list_tests:
        click.echo(err=True)
        cases = loader.get_test_cases([suite])
        for test_group in cases.values():
            for test in test_group:
                click.echo(str(test))
        return 0

    jobs = max(min(total, jobs), 1)

    if verbosity > 0:
        click.echo()
        if jobs > 1:
            click.echo(
                styles.status(f"Using up to {jobs} processes to run tests.")
            )

    result = None
    for rnum in range(repeat):
        if repeat > 1:
            click.echo(styles.status(f"Repeat #{rnum + 1} out of {repeat}."))

        test_runner = runner.ParallelTextTestRunner(
            verbosity=verbosity,
            output_format=runner.OutputFormat(output_format),
            warnings=warnings,
            num_workers=jobs,
            failfast=failfast,
            shuffle=shuffle,
            backend_dsn=backend_dsn,
            try_cached_db=try_cached_db,
            data_dir=data_dir,
            use_data_dir_dbs=use_data_dir_dbs,
        )

        result = test_runner.run(
            suite,
            selected_shard,
            total_shards,
            running_times_log_file,
        )

        if verbosity > 0:
            results.render_result(test_runner.stream, result)

        if not result.was_successful:
            break

    assert result is not None
    if result_log:
        results.write_result(result_log, result)

    return 0 if result.was_successful else 1
