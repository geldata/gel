#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2020-present MagicStack Inc. and the EdgeDB authors.
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


from edb.edgeql import ast as qlast
from edb.edgeql import tokenizer
from edb.edgeql import parser as qlparser
from edb.edgeql.parser.grammar import tokens as qltokens

import edb._edgeql_parser as rust_parser

from edb.tools.edb import edbcommands


@edbcommands.command("parser-demo")
def main():
    qlparser.preload_spec()

    for q in QUERIES[-8:]:
        sdl = q.startswith('sdl')
        if sdl:
            q = q[3:]

        try:
            source = tokenizer.NormalizedSource.from_string(q)
            # source = tokenizer.Source.from_string(q)
        except Exception as e:
            print('Error during tokenization:')
            print(e)
            continue

        start_t = qltokens.T_STARTSDLDOCUMENT if sdl else qltokens.T_STARTBLOCK
        start_t_name = start_t.__name__[2:]
        tokens = source.tokens()
        result, productions = rust_parser.parse(start_t_name, tokens)

        print('-' * 30)
        print()

        for index, error in enumerate(result.errors):
            message, span, hint, details = error
            (start, end) = tokenizer.inflate_span(source.text(), span)

            print(f'Error [{index + 1}/{len(result.errors)}]:')
            print(
                '\n'.join(
                    source.text().splitlines()[(start.line - 1) : end.line]
                )
            )
            print(
                ' ' * (start.column - 1)
                + '^' * (max(1, end.column - start.column))
                + ' '
                + message
            )
            if details:
                print(f'  Details: {details}')
            if hint:
                print(f'  Hint: {hint}')
            print()

        if result.out:
            try:
                ast = qlparser._cst_to_ast(
                    result.out, productions, source=source, filename=''
                ).val
            except Exception as e:
                print(e)
                ast = None
            if ast:
                print('Recovered AST:')
                if isinstance(ast, list):
                    for x in ast:
                        assert isinstance(x, qlast.Base)
                        x.dump_edgeql()
                        x.dump()
                        print(x.span.start, x.span.end)
                elif isinstance(ast, qlast.Base):
                    ast.dump_edgeql()
                    ast.dump()
                    print(ast.span.start, ast.span.end)
                else:
                    print(ast)


QUERIES = [
    '''sdl
    module y {
        type X {
            property z:
        }
    }
    ''',
    '''
    CREATE MIGRATION
    {
        set global foo := "test";
        alter type Foo {
            create required property name -> str {
            set default := (global foo);
        }
    }; }
    '''
]
