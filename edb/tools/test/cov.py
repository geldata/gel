from __future__ import annotations
from typing import TYPE_CHECKING, Any, NamedTuple

import contextlib
import json
import os
import os.path

if TYPE_CHECKING:
    import coverage
    from collections.abc import Iterator


class CoverageConfig(NamedTuple):
    config: str
    datadir: str
    paths: list[str]

    def to_json(self) -> str:
        return json.dumps(self._asdict())

    @classmethod
    def from_json(cls, js: str) -> CoverageConfig:
        dct = json.loads(js)
        return cls(**dct)

    def save_to_environ(self) -> None:
        os.environ.update({"EDGEDB_TEST_COVERAGE": self.to_json()})

    @classmethod
    def from_environ(cls) -> CoverageConfig | None:
        config = os.environ.get("EDGEDB_TEST_COVERAGE")
        if config is None:
            return None
        else:
            return cls.from_json(config)

    @classmethod
    def new_custom_coverage_object(cls, **conf: Any) -> coverage.Coverage:
        import coverage  # noqa: PLC0415

        cov = coverage.Coverage(**conf)

        cov._warn_no_data = False
        cov._warn_unimported_source = False
        cov._warn_preimported_source = False

        return cov

    def new_coverage_object(self) -> coverage.Coverage:
        return self.new_custom_coverage_object(
            config_file=self.config,
            source=self.paths,
            data_file=os.path.join(self.datadir, f"cov-{os.getpid()}"),
        )

    @classmethod
    def start_coverage_if_requested(cls) -> coverage.Coverage | None:
        cov_config = cls.from_environ()
        if cov_config is not None:
            cov = cov_config.new_coverage_object()
            cov.start()
            return cov
        else:
            return None

    @classmethod
    @contextlib.contextmanager
    def enable_coverage_if_requested(cls) -> Iterator[None]:
        cov_config = cls.from_environ()
        if cov_config is None:
            yield
        else:
            cov = cov_config.new_coverage_object()
            cov.start()
            try:
                yield
            finally:
                cov.stop()
                cov.save()
