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


class TestORMORM(tb.QueryTestCase):
    FULL_SCHEMA = TEST_DIR / 'orm.gel'
    SETUP = TEST_DIR / 'orm.edgeql'

    async def test_orm_orm_dummy(self):
        pass


class TestORMLinkTest(tb.QueryTestCase):
    FULL_SCHEMA = TEST_DIR / 'link_set.gel'
    SETUP = """
        INSERT House { name := 'Griffindor' };
        INSERT House { name := 'Hufflepuff' };
        INSERT House { name := 'Ravenclaw' };
        INSERT House { name := 'Slytherin' };

        INSERT Class { name := 'Charms' };
        INSERT Class { name := 'Potions' };
        INSERT Class { name := 'Divination' };

        CREATE ALIAS Griffindor := assert_exists((
            select House
            filter .name = 'Griffindor'
            limit 1
        ));

        INSERT Person {
            name := 'Harry Potter',
            house := Griffindor {
                @rank := 'seeker'
            },
            pet := (
                INSERT Pet {
                    name := 'Hedwig',
                }
            ),
            classes := (
                select Class
                filter .name in {'Charms', 'Potions'}
            ),
        };
        INSERT Person {
            name := 'Hermione Granger',
            house := Griffindor,
            pet := (
                INSERT Pet {
                    name := 'Crookshanks',
                }
            ),
        };
        INSERT Person {
            name := 'Ron Weasley',
            house := Griffindor,
            pet := (
                INSERT Pet {
                    name := 'Scabbers',
                }
            ),
        };
        INSERT Person {
            name := 'Neville Longbottom',
            house := Griffindor,
            pet := (
                INSERT Pet {
                    name := 'Trevor',
                }
            ),
        };
        UPDATE Person
        filter .name = 'Harry Potter'
        set {
            friends := assert_distinct((
                with friend_data := {
                    ('Hermione Granger', 'smart'),
                    ('Ron Weasley', 'reliable'),
                }
                for data in friend_data union (
                    select detached Person {
                        @opinion := data.1
                    }
                    filter .name = data.0
                )
            ))
        };
    """

    async def test_orm_link_set_dummy(self):
        pass
