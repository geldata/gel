import collections
import typing
import dataclasses
import textwrap
import sys
from itertools import chain

from edb.edgeql import ast as qlast
from edb.edgeql import qltypes
from edb.edgeql import parser
from edb.common.ast import base as ast
from edb.common import enum as s_enum
from edb.common import typing_inspect
from edb.common import parsing as e_parsing
from edb.tools.edb import edbcommands
import edb._edgeql_parser as rust_parser


@dataclasses.dataclass()
class ASTClass:
    name: str
    typ: typing.Any
    children: list[type] = dataclasses.field(default_factory=list)


@dataclasses.dataclass()
class ASTUnion:
    name: str
    variants: typing.Sequence[type | str]
    for_composition: bool


@dataclasses.dataclass()
class ListNonTerm:
    item: str
    separator: str
    trailing_separator: bool


@dataclasses.dataclass()
class NonTerm:
    prod: type
    output_ty: typing.Optional[type]
    has_mapping_impl: bool = False
    is_list: typing.Optional[ListNonTerm] = None

    reductions: list[str] = dataclasses.field(default_factory=list)


# a queue for union types that are to be generated
union_types: list[ASTUnion] = []

# all discovered AST classes
ast_classes: dict[str, ASTClass] = {}


@edbcommands.command("gen-rust-ast")
def main() -> None:
    gen_rust_ast()
    gen_rust_from_id()
    gen_rust_grammar()


def gen_rust_ast() -> None:
    f = open('edb/edgeql-parser/src/ast.rs', 'w')

    f.write(
        textwrap.dedent(
            '''\
            // DO NOT EDIT. This file was generated with:
            //
            // $ edb gen-rust-ast

            //! Abstract Syntax Tree for EdgeQL
            #![allow(non_camel_case_types)]

            use indexmap::IndexMap;
            '''
        )
    )

    # discover all nodes
    for name, typ in qlast.__dict__.items():
        if not isinstance(typ, type):
            continue

        if not issubclass(typ, (qlast.Base, qlast.GrammarEntryPoint)):
            continue

        if hasattr(typ, '_direct_fields'):
            # re-run field collection to correctly handle forward-references
            typ = typ._collect_direct_fields()  # type: ignore

        if name in {'Base', 'DDL'}:
            continue

        ast_classes[typ.__name__] = ASTClass(name=name, typ=typ)

    # build inheritance graph
    for ast_class in ast_classes.values():
        for base in ast_class.typ.__bases__:
            if base.__name__ not in ast_classes:
                continue
            ast_classes[base.__name__].children.append(ast_class.typ)

    # generate structs
    for ast_class in ast_classes.values():
        print(ast_class.name)
        f.write(codegen_struct(ast_class))

        while len(union_types) > 0:
            f.write(codegen_union(union_types.pop(0)))

    # generate enums
    for name, typ in chain(qlast.__dict__.items(), qltypes.__dict__.items()):
        if not isinstance(typ, type) or not issubclass(typ, s_enum.StrEnum):
            continue

        f.write(codegen_enum(name, typ))


def gen_rust_from_id() -> None:
    f = open('edb/edgeql-parser/src/grammar/from_id.rs', 'w')

    f.write(
        textwrap.dedent(
            '''\
            // DO NOT EDIT. This file was generated with:
            //
            // $ edb gen-rust-ast
            '''
        )
    )

    parser.preload_spec()
    productions = rust_parser.get_productions()

    f.write(codegen_reduction_from_id_func(productions))


def gen_rust_grammar() -> None:
    mapping_source = open('edb/edgeql-parser/src/grammar/mapping.rs').read()

    f = open('edb/edgeql-parser/src/grammar/definitions.rs', 'w')

    f.write(
        textwrap.dedent(
            '''\
            // DO NOT EDIT. This file was generated with:
            //
            // $ edb gen-rust-ast
            '''
        )
    )

    f.write('\n')
    f.write('use super::*;\n')
    f.write('use crate::parser::CSTNode;\n')
    f.write('use crate::ast;\n')

    parser.preload_spec()
    productions = rust_parser.get_productions()

    prods: dict[str, NonTerm] = {}
    for prod, reduction_method in productions:
        if reduction_method.__doc__ is None:
            continue

        prod_name = prod.__name__
        if prod_name not in prods:
            has_mapping_impl = (
                f'impl From<d::{prod_name}Node>' in mapping_source
            )

            mod = sys.modules[prod.__module__]
            annotations = typing.get_type_hints(prod, localns=mod.__dict__)
            val_ty = annotations['val'] if 'val' in annotations else None

            prods[prod_name] = NonTerm(
                prod=prod,
                output_ty=val_ty,
                has_mapping_impl=has_mapping_impl,
                is_list=None,
            )

        reduction_name = get_reduction_name(reduction_method.__doc__)
        prods[prod_name].reductions.append(reduction_name)

    # handle lists
    for prod_name, non_term in prods.copy().items():
        if not (
            issubclass(non_term.prod, e_parsing.ListNonterm)
            and not prod_name.endswith('Inner')
        ):
            continue

        has_inner = False
        separator = "COMMA"
        item = ""

        if inner := prods.get(f'{prod_name}Inner', None):
            has_inner = True
            prods.pop(f'{prod_name}Inner')
            reductions = inner.reductions
        else:
            reductions = non_term.reductions

        for reduction in reductions:
            parts = reduction.split('_')
            if len(parts) == 3:
                item = parts[2]
                separator = parts[1]

        prods[prod_name].is_list = ListNonTerm(
            item=item,
            separator=separator,
            trailing_separator=has_inner,
        )

    for prod_name in sorted(prods.keys()):
        print(prod_name)
        f.write(codegen_grammar_non_term(prods[prod_name]))


def codegen_struct(cls: ASTClass) -> str:
    if cls.typ.__abstract_node__:
        return codegen_union(
            ASTUnion(name=cls.name, variants=cls.children, for_composition=True)
        )

    fields = collections.OrderedDict()
    for parent in reversed(cls.typ.__mro__):
        lst = getattr(parent, '_direct_fields', [])
        for field in lst:
            fields[field.name] = field

    field_names = set()
    fields_text = ''
    doc_comment = ''
    for f in typing.cast(list[ast._Field], fields.values()):
        if f.hidden:
            continue

        union_name = f'{cls.name}{title_case(f.name)}'

        # print(f'struct {cls.name}, field {f.name}, type: {f.type}')
        typ = translate_type(f.type, union_name, False)
        if hasattr(cls.typ, '__rust_box__') and f.name in cls.typ.__rust_box__:
            typ = f'Box<{typ}>'

        f_name = quote_rust_ident(f.name)
        field_names.add(f_name)

        fields_text += f'    pub {f_name}: {typ},\n'

    return (
        f'\n{doc_comment}'
        + f'#[derive(Debug, Clone)]\n'
        # + f'#[cfg_attr(feature = "python", derive(IntoPython))]\n'
        + f'pub struct {cls.name} {"{"}\n'
        + fields_text
        + '}\n'
    ).replace('{\n}', r'{}')


def codegen_enum(name: str, cls: typing.Any) -> str:
    fields = ''
    for member in cls._member_names_:
        fields += f'    {member},\n'

    # if cls.__module__ == 'edb.edgeql.ast':
    #     cls_path = f'qlast.{cls.__name__}'
    # elif cls.__module__ == 'edb.edgeql.qltypes':
    #     cls_path = f'qltypes.{cls.__name__}'
    # else:
    #     raise LookupError(
    #         'we only support generating AST from qlast and qltypes modules'
    #     )

    return (
        '\n#[derive(Debug, Clone)]\n'
        # + f'#[cfg_attr(feature = "python", derive(IntoPython))]\n'
        # + f'#[cfg_attr(feature = "python", py_enum({cls_path}))]\n'
        + f'pub enum {name} {"{"}\n'
        + fields
        + '}\n'
    )


def quote_rust_ident(name: str) -> str:
    if name in {'type', 'where', 'ref', 'final', 'abstract'}:
        return 'r#' + name
    return name


def title_case(name: str) -> str:
    return name[0].upper() + name[1:]


def codegen_union(union: ASTUnion) -> str:
    fields = ''
    for arg in union.variants:
        if isinstance(arg, str):
            fields += f'    {arg},\n'
        else:
            # print(f'union {union.name}, variant {arg}')
            typ = translate_type(arg, '???', union.for_composition)
            fields += f'    {arg.__name__}({typ}),\n'

    # attr = 'py_child' if union.for_composition else 'py_union'

    return (
        '\n#[derive(Debug, Clone)]\n'
        # f'#[cfg_attr(feature = "python", derive(IntoPython))]\n'
        # f'#[cfg_attr(feature = "python", {attr})]\n'
        f'pub enum {union.name} {"{"}\n{fields}{"}"}\n'
    )


def translate_type(
    typ: type,
    union_name: str,
    for_composition: bool,
    ast_path: str = '',
    box: bool = True,
) -> str:
    args = [
        translate_type(param, union_name, for_composition, ast_path, box)
        for param in typing_inspect.get_args(typ)
    ]

    if typing_inspect.is_union_type(typ):
        if hasattr(typ, '_name') and typ._name == 'Optional':
            return f'Option<{args[0]}>'

        union_types.append(
            ASTUnion(
                name=union_name,
                variants=typing_inspect.get_args(typ),
                for_composition=for_composition,
            )
        )
        return union_name

    if typing_inspect.is_generic_type(typ):
        if typ.__name__ in ('list', 'sequence'):
            return f'Vec<{args[0]}>'

        if typ.__name__ == 'dict':
            return f'IndexMap<{args[0]}, {args[1]}>'

    if not hasattr(typ, '__name__'):
        return str(typ)

    if typing_inspect.is_tuple_type(typ):
        if len(args) > 0 and args[1] == 'Ellipsis':
            return f'Vec<{args[0]}>'
        else:
            return '(' + ', '.join(args) + ')'

    if typ.__name__ == "AliasedExprSpec":
        return f'(Option<String>, {ast_path}Expr)'

    if issubclass(typ, tuple):
        return 'TodoAst'

    mappings = {
        'str': 'String',
        'bool': 'bool',
        'int': 'i64',
        'float': 'f64',
        'NoneType': '()',
        'bytes': 'Vec<u8>',
    }

    if typ.__name__ in mappings:
        return mappings[typ.__name__]

    if box and typ.__name__ == "Expr":
        return f'Box<{ast_path}{typ.__name__}>'

    if typ.__module__ not in ('edb.edgeql.ast', 'edb.edgeql.qltypes'):
        raise NotImplementedError(f'cannot translate: {typ}, {typ.__name__}')

    if for_composition or typ.__name__ not in ast_classes:
        return ast_path + typ.__name__

    return ast_path + typ.__name__


# Some non-terminals are redundant - they are not needed and don't have any
# productions, so they are removed from the grammar.
# Which means that we can (must) also skip them here.
SKIP_REDUCTIONS = {
    'CreateAccessPolicySDLCommandBlock',
    'CreateAliasSDLCommandBlock',
    'CreateConcreteIndexSDLCommandBlock',
    'CreateFunctionSDLCommandBlock',
    'CreateGlobalSDLCommandBlock',
    'CreateIndexSDLCommandBlock',
    'CreatePropertySDLCommandBlock',
    'CreateRewriteSDLCommandBlock',
    'CreateSDLCommandBlock',
    'CreateTriggerSDLCommandBlock',
    'CreatePermissionSDLCommandBlock',
}


def codegen_grammar_non_term(non_term: NonTerm) -> str:
    r = '\n'

    if non_term.output_ty is None:
        output_ty_str = 'TodoAst'
    else:
        output_ty_str = translate_type(
            non_term.output_ty, '???', False, ast_path='ast::', box=False
        )
    output_ty_str = output_ty_str.replace('<', '::<')

    if is_list := non_term.is_list:
        if 'TodoAst' in output_ty_str:
            output_ty_str = 'Vec::<TodoAst>'

        r += "edgeql_parser_derive::list! {\n"
        r += f"    enum {non_term.prod.__name__},\n"
        r += f"    {is_list.item},\n"
        r += f"    {output_ty_str},\n"
        r += f"    {is_list.separator},\n"
        r += f"    {'true' if is_list.trailing_separator else 'false'}\n"
        r += "}\n"
        return r

    r += '#[derive(edgeql_parser_derive::Reduce)]\n'
    r += f'#[output({output_ty_str})]\n'

    if not non_term.has_mapping_impl:
        # if there is not mapping impl yet, add a #[stub()]
        r += '#[stub()]\n'

    r += f'pub enum {non_term.prod.__name__} {"{"}\n'
    for reduction in non_term.reductions:
        if reduction in SKIP_REDUCTIONS:
            continue
        r += f'    {reduction},\n'
    r += '}\n'

    return r


def codegen_reduction_from_id_func(
    productions: list[tuple[type, typing.Callable]],
) -> str:
    non_terminals = collections.defaultdict(list)
    for id, (prod, reduction_method) in enumerate(productions):
        if reduction_method.__doc__ is not None:
            non_term_name = prod.__name__
            reduction_name = get_reduction_name(reduction_method.__doc__)

            non_terminals[non_term_name].append((id, reduction_name))

    res = ''
    for non_term_name, reductions in sorted(non_terminals.items()):
        res += '\n'
        res += f'impl super::FromId for super::{non_term_name} {'{'}\n'
        res += '    fn from_id(id: usize) -> Self {\n'
        res += '        match id {\n'

        for id, reduction_name in reductions:
            if reduction_name in SKIP_REDUCTIONS:
                continue
            res += f'            {id} => Self::{reduction_name},\n'

        res += f'            _ => unreachable!("reduction {"{"}id{"}"}"),\n'
        res += '        }\n'
        res += '    }\n'
        res += '}\n'

    return res


def get_reduction_name(docstring: str) -> str:
    prepared_name = docstring.replace(r'%reduce', '')
    prepared_name = prepared_name.replace('<e>', 'epsilon')
    prepared_name = prepared_name.replace('[', '').replace(']', '')
    prepared_name = prepared_name.replace('\\', '')
    return '_'.join(prepared_name.split())
