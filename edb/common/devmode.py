#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2011-present MagicStack Inc. and the EdgeDB authors.
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

import logging
import os
import pathlib


logger = logging.getLogger('edb.devmode.cache')


def enable_dev_mode(enabled: bool = True):
    os.environ['__EDGEDB_DEVMODE'] = '1' if enabled else ''


def is_in_dev_mode() -> bool:
    devmode = os.environ.get('__EDGEDB_DEVMODE', '0')
    return devmode.lower() not in ('0', '', 'false')


def get_dev_mode_cache_dir() -> pathlib.Path:
    if is_in_dev_mode():
        root = pathlib.Path(__file__).parent.parent.parent
        cache_dir = (root / 'build' / 'cache')
        cache_dir.mkdir(exist_ok=True)
        return cache_dir
    else:
        raise RuntimeError('server is not running in dev mode')


def get_dev_mode_data_dir() -> pathlib.Path:
    data_dir_env = os.environ.get("EDGEDB_SERVER_DEV_DIR")
    if data_dir_env:
        data_dir = pathlib.Path(data_dir_env)
    else:
        root = pathlib.Path(__file__).parent.parent.parent
        data_dir = root / "tmp" / "devdatadir"

    return data_dir
