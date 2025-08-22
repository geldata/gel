#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2012-present MagicStack Inc. and the EdgeDB authors.
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

'''
You can use this to set up the gel-python orm database:

edb inittestdb -k test_orm --update --tests-dir misc/fake-tests/
'''

import os.path
import pathlib

from edb.testbase import server as tb


TEST_DIR = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / 'gel-python'
    / 'tests'
    / 'dbsetup'
)


class TestORM(tb.QueryTestCase):
    FULL_SCHEMA = TEST_DIR / 'orm.gel'
    SETUP = TEST_DIR / 'orm.edgeql'

    async def test_orm_dummy(self):
        pass
