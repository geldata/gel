#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2008-present MagicStack Inc. and the EdgeDB authors.
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
from typing import (
    Any,
    Callable,
    Optional,
    AbstractSet,
    Iterable,
    Mapping,
    Sequence,
    TYPE_CHECKING,
)

import copy
import uuid

from edb.common import checked
from edb.common import struct

from edb.edgeql import ast as qlast_
from edb.edgeql import codegen as qlcodegen
from edb.edgeql import compiler as qlcompiler
from edb.edgeql import parser as qlparser
from edb.edgeql import qltypes

from . import abc as s_abc
from . import objects as so
from . import name as sn
from . import delta as sd


if TYPE_CHECKING:
    from edb.schema import schema as s_schema
    from edb.schema import types as s_types

    from edb.ir import ast as irast_


class Expression(struct.MixedRTStruct, so.ObjectContainer, s_abc.Expression):

    text = struct.Field(str, frozen=True)
    # mypy wants an argument to the ObjectSet generic, but
    # that wouldn't work for struct.Field, since subscripted
    # generics are not types.
    refs = struct.Field(
        so.ObjectSet,  # type: ignore
        coerce=True,
        default=None,
        frozen=True,
    )

    # A string describing the provenance of the expression, used to
    # help annotate the parser contexts. We don't store it explicitly
    # in the database or explicitly populate it when creating
    # Expressions, but instead populate it in resolve_attribute_value
    # and when reading in the schema.
    origin = struct.Field(str, default=None)

    def __init__(
        self,
        *args: Any,
        _qlast: Optional[qlast_.Expr] = None,
        _irast: Optional[irast_.Statement] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._qlast = _qlast
        self._irast = _irast

    def __getstate__(self) -> dict[str, Any]:
        return {
            'text': self.text,
            'refs': self.refs,
            '_qlast': None,
            '_irast': None,
        }

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        # Since `origin` is omitted from the pickled schema, it needs to be
        # explicitly set to `None` when loading pickles.
        super().__setstate__({"origin": None, **state})

    def __eq__(self, rhs: object) -> bool:
        if not isinstance(rhs, Expression):
            return NotImplemented
        return (
            self.text == rhs.text
            and self.refs == rhs.refs
            and self.origin == rhs.origin
        )

    def parse(self) -> qlast_.Expr:
        """Parse the expression text into an AST. Cached."""

        if self._qlast is None:
            self._qlast = qlparser.parse_fragment(
                self.text, filename=f'<{self.origin}>' if self.origin else "")
        return self._qlast

    @property
    def irast(self) -> Optional[irast_.Statement]:
        return self._irast

    def set_origin(self, id: uuid.UUID, field: str) -> None:
        """
        Set the origin of the expression based on field and enclosing object.

        We base the origin on the id of the object, not on its name, because
        these strings should be useful to a client, which can't do a lookup
        based on the mangled internal names.
        """
        self.origin = f'{id} {field}'

    def is_compiled(self) -> bool:
        return self.refs is not None

    def _refs_keys(
        self, schema: s_schema.Schema
    ) -> set[tuple[type[so.Object], sn.Name]]:
        return {
            (type(x), x.get_name(schema))
            for x in (self.refs.objects(schema) if self.refs else ())
        }

    @classmethod
    def compare_values(
        cls: type[Expression],
        ours: Expression,
        theirs: Expression,
        *,
        our_schema: s_schema.Schema,
        their_schema: s_schema.Schema,
        context: so.ComparisonContext,
        compcoef: float,
    ) -> float:
        if not ours and not theirs:
            return 1.0
        elif not ours or not theirs:
            return compcoef

        # If the new and old versions share a reference to an object
        # that is being deleted, then we must delete this object as well.
        our_refs = ours._refs_keys(our_schema)
        their_refs = theirs._refs_keys(their_schema)
        if (our_refs & their_refs) & context.deletions.keys():
            return 0.0

        if ours.text == theirs.text:
            return 1.0
        else:
            return compcoef

    @classmethod
    def from_ast(
        cls: type[Expression],
        qltree: qlast_.Expr,
        schema: s_schema.Schema,
        modaliases: Optional[Mapping[Optional[str], str]] = None,
        localnames: AbstractSet[str] = frozenset(),
        *,
        as_fragment: bool = False,
    ) -> Expression:
        if modaliases is None:
            modaliases = {}
        if not as_fragment:
            qlcompiler.normalize(
                qltree,
                schema=schema,
                modaliases=modaliases,
                localnames=localnames
            )

        norm_text = qlcodegen.generate_source(qltree, pretty=False)

        return Expression(
            text=norm_text,
            _qlast=qltree,
        )

    def not_compiled(self) -> Expression:
        return Expression(text=self.text, origin=self.origin)

    def compiled(
        self,
        schema: s_schema.Schema,
        *,
        options: Optional[qlcompiler.CompilerOptions] = None,
        as_fragment: bool = False,
        detached: bool = False,
        find_extra_refs: Optional[
            Callable[[irast_.Set], set[so.Object]]
        ] = None,
        context: Optional[sd.CommandContext],
    ) -> CompiledExpression:

        from edb.ir import ast as irast_
        from edb.edgeql import ast as qlast

        if as_fragment:
            ir: irast_.Command = qlcompiler.compile_ast_fragment_to_ir(
                self.parse(),
                schema=schema,
                options=options,
            )
        else:
            ql_expr = self.parse()
            if detached:
                ql_expr = qlast.DetachedExpr(
                    expr=ql_expr,
                    preserve_path_prefix=True,
                )

            ir = qlcompiler.compile_ast_to_ir(
                ql_expr,
                schema=schema,
                options=options,
            )

        assert isinstance(ir, irast_.Statement)

        if context and ir.warnings:
            delta_root = context.top().op
            if isinstance(delta_root, sd.DeltaRoot):
                delta_root.warnings.extend(ir.warnings)

        # XXX: ref stuff - why doesn't it go into the delta tree? - temporary??
        srefs: set[so.Object] = {
            ref for ref in ir.schema_refs if schema.has_object(ref.id)
        }

        if find_extra_refs is not None:
            srefs |= find_extra_refs(ir.expr)

        return CompiledExpression(
            text=self.text,
            refs=so.ObjectSet.create(schema, srefs),
            _qlast=self.parse(),
            _irast=ir,
            origin=self.origin,
        )

    def ensure_compiled(
        self,
        schema: s_schema.Schema,
        *,
        options: Optional[qlcompiler.CompilerOptions] = None,
        as_fragment: bool = False,
        context: Optional[sd.CommandContext],
    ) -> CompiledExpression:
        if self._irast:
            return self  # type: ignore
        else:
            return self.compiled(
                schema, options=options, as_fragment=as_fragment,
                context=context)

    def assert_compiled(self) -> CompiledExpression:
        if self._irast:
            return self  # type: ignore
        else:
            raise AssertionError(
                f"uncompiled expression {self.text!r} (origin: {self.origin})")

    @classmethod
    def from_ir(
        cls: type[Expression],
        expr: Expression,
        ir: irast_.Statement,
        schema: s_schema.Schema,
    ) -> CompiledExpression:
        return CompiledExpression(
            text=expr.text,
            refs=so.ObjectSet.create(schema, ir.schema_refs),
            _qlast=expr.parse(),
            _irast=ir,
            origin=expr.origin,
        )

    def as_shell(self, schema: s_schema.Schema) -> ExpressionShell:
        return ExpressionShell(
            text=self.text,
            refs=(
                r.as_shell(schema) for r in self.refs.objects(schema)
            ) if self.refs is not None else None,
            _qlast=self._qlast,
        )

    def schema_reduce(
        self,
    ) -> tuple[
        str,
        tuple[
            str,
            Optional[tuple[type, ...] | type],
            tuple[uuid.UUID, ...],
            tuple[tuple[str, Any], ...],
        ],
        Optional[str],
    ]:
        assert self.refs is not None, 'expected expression to be compiled'
        return (
            self.text,
            self.refs.schema_reduce(),
            self.origin,
        )

    @classmethod
    def schema_restore(
        cls,
        data: tuple[
            str,
            tuple[
                str,
                Optional[tuple[type, ...] | type],
                tuple[uuid.UUID, ...],
                tuple[tuple[str, Any], ...],
            ],
            Optional[str],
        ],
    ) -> Expression:
        text, refs_data, origin = data
        return Expression(
            text=text,
            refs=so.ObjectCollection.schema_restore(refs_data),
            origin=origin,
        )

    @classmethod
    def schema_refs_from_data(
        cls,
        data: tuple[
            str,
            tuple[
                str,
                Optional[tuple[type, ...] | type],
                tuple[uuid.UUID, ...],
                tuple[tuple[str, Any], ...],
            ],
        ],
    ) -> frozenset[uuid.UUID]:
        return so.ObjectCollection.schema_refs_from_data(data[1])

    @property
    def ir_statement(self) -> irast_.Statement:
        """Assert this expr is a compiled EdgeQL statement and return its IR"""
        from edb.ir import ast as irast_

        if not self.is_compiled():
            raise AssertionError('expected a compiled expression')
        ir = self.irast
        if not isinstance(ir, irast_.Statement):
            raise AssertionError(
                'expected the result of an expression to be a Statement')
        return ir

    @property
    def stype(self) -> s_types.Type:
        return self.ir_statement.stype

    @property
    def cardinality(self) -> qltypes.Cardinality:
        return self.ir_statement.cardinality

    @property
    def schema(self) -> s_schema.Schema:
        return self.ir_statement.schema


class CompiledExpression(Expression):
    refs = struct.Field(
        so.ObjectSet,  # type: ignore
        coerce=True,
        frozen=True,
    )

    def __init__(
        self,
        *args: Any,
        _qlast: Optional[qlast_.Expr] = None,
        _irast: irast_.Statement,
        **kwargs: Any
    ) -> None:
        super().__init__(*args, _qlast=_qlast, _irast=_irast, **kwargs)

    @property
    def irast(self) -> irast_.Statement:
        assert self._irast
        return self._irast

    def as_python_value(self) -> Any:
        return qlcompiler.evaluate_ir_statement_to_python_val(self.irast)


class ExpressionShell(so.Shell):

    def __init__(
        self,
        *,
        text: str,
        refs: Optional[Iterable[so.ObjectShell[so.Object]]],
        _qlast: Optional[qlast_.Expr] = None,
        _irast: Optional[irast_.Statement] = None,
    ) -> None:
        self.text = text
        self.refs = tuple(refs) if refs is not None else None
        self._qlast = _qlast
        self._irast = _irast

    def resolve(self, schema: s_schema.Schema) -> Expression:
        cls = CompiledExpression if self._irast else Expression
        return cls(
            text=self.text,
            refs=so.ObjectSet.create(
                schema,
                [s.resolve(schema) for s in self.refs],
            ) if self.refs is not None else None,
            _qlast=self._qlast,
            _irast=self._irast,  # type: ignore[arg-type]
        )

    def parse(self) -> qlast_.Expr:
        if self._qlast is None:
            self._qlast = qlparser.parse_fragment(self.text)
        return self._qlast

    def __repr__(self) -> str:
        if self.refs is None:
            refs = 'N/A'
        else:
            refs = ', '.join(repr(obj) for obj in self.refs)
        return f'<ExpressionShell {self.text} refs=({refs})>'


class ExpressionList(checked.FrozenCheckedList[Expression]):

    @staticmethod
    def merge_values(
        target: so.Object,
        sources: Sequence[so.Object],
        field_name: str,
        *,
        ignore_local: bool = False,
        schema: s_schema.Schema,
    ) -> Any:
        if not ignore_local:
            result = target.get_explicit_field_value(schema, field_name, None)
        else:
            result = None
        for source in sources:
            theirs = source.get_explicit_field_value(schema, field_name, None)
            if theirs:
                if result is None:
                    result = theirs[:]
                else:
                    result.extend(theirs)

        return result

    @classmethod
    def compare_values(
        cls: type[ExpressionList],
        ours: Optional[ExpressionList],
        theirs: Optional[ExpressionList],
        *,
        our_schema: s_schema.Schema,
        their_schema: s_schema.Schema,
        context: so.ComparisonContext,
        compcoef: float,
    ) -> float:
        """See the comment in Object.compare_values"""
        if not ours and not theirs:
            basecoef = 1.0
        elif (not ours or not theirs) or (len(ours) != len(theirs)):
            basecoef = 0.2
        else:
            similarity = []

            for expr1, expr2 in zip(ours, theirs):
                similarity.append(
                    Expression.compare_values(
                        expr1, expr2, our_schema=our_schema,
                        their_schema=their_schema, context=context,
                        compcoef=compcoef))

            basecoef = sum(similarity) / len(similarity)

        return basecoef + (1 - basecoef) * compcoef


class ExpressionDict(checked.CheckedDict[str, Expression]):

    @staticmethod
    def merge_values(
        target: so.Object,
        sources: Sequence[so.Object],
        field_name: str,
        *,
        ignore_local: bool = False,
        schema: s_schema.Schema,
    ) -> Any:
        result = None
        # Assume that sources are given in MRO order, so we need to reverse
        # them to figure out the merged vaue.
        for source in reversed(sources):
            theirs = source.get_explicit_field_value(schema, field_name, None)
            if theirs:
                if result is None:
                    result = dict(theirs)
                else:
                    result.update(theirs)

        # Finally merge the most relevant data.
        if not ignore_local:
            ours = target.get_explicit_field_value(schema, field_name, None)
            if result is None:
                result = ours
            elif ours:
                result.update(ours)

        return result

    @classmethod
    def compare_values(
        cls: type[ExpressionDict],
        ours: Optional[ExpressionDict],
        theirs: Optional[ExpressionDict],
        *,
        our_schema: s_schema.Schema,
        their_schema: s_schema.Schema,
        context: so.ComparisonContext,
        compcoef: float,
    ) -> float:
        """See the comment in Object.compare_values"""
        if not ours and not theirs:
            basecoef = 1.0
        elif (not ours or not theirs) or (len(ours) != len(theirs)):
            basecoef = 0.2
        elif set(ours.keys()) != set(theirs.keys()):
            # Same length dicts can still have different keys, which is
            # similar to having mismatched length.
            basecoef = 0.2
        else:
            # We have the same keys, so just compare the values.
            similarity = []

            for ((_, expr1), (_, expr2)) in zip(
                sorted(ours.items()), sorted(theirs.items())
            ):
                similarity.append(
                    Expression.compare_values(
                        expr1, expr2, our_schema=our_schema,
                        their_schema=their_schema, context=context,
                        compcoef=compcoef))

            basecoef = sum(similarity) / len(similarity)

        return basecoef + (1 - basecoef) * compcoef


EXPRESSION_TYPES = (
    Expression, ExpressionList, ExpressionDict
)


def imprint_expr_context(
    qltree: qlast_.Base,
    modaliases: Mapping[Optional[str], str],
) -> qlast_.Base:
    # Imprint current module aliases as explicit
    # alias declarations in the expression.

    if (isinstance(qltree, qlast_.BaseConstant)
            or qltree is None
            or (isinstance(qltree, qlast_.Set)
                and not qltree.elements)
            or (isinstance(qltree, qlast_.Array)
                and all(isinstance(el, qlast_.BaseConstant)
                        for el in qltree.elements))):
        # Leave constants alone.
        return qltree

    if isinstance(qltree, qlast_.Expr):
        qltree = qlast_.SelectQuery(result=qltree, implicit=True)
    else:
        assert isinstance(qltree, (qlast_.Command, qlast_.DDLCommand))
        qltree = copy.copy(qltree)
        qltree.aliases = (
            list(qltree.aliases) if qltree.aliases is not None else None)
    assert isinstance(qltree, (qlast_.Query, qlast_.Command))

    existing_aliases: dict[Optional[str], str] = {}
    for alias in (qltree.aliases or ()):
        if isinstance(alias, qlast_.ModuleAliasDecl):
            existing_aliases[alias.alias] = alias.module

    aliases_to_add = set(modaliases) - set(existing_aliases)
    for alias_name in aliases_to_add:
        if qltree.aliases is None:
            qltree.aliases = []
        qltree.aliases.append(
            qlast_.ModuleAliasDecl(
                alias=alias_name,
                module=modaliases[alias_name],
            )
        )

    return qltree


def get_expr_referrers(
    schema: s_schema.Schema, obj: so.Object
) -> dict[so.Object, list[str]]:
    """Return schema referrers with refs in expressions."""

    refs: dict[tuple[type[so.Object], str], frozenset[so.Object]] = (
        schema.get_referrers_ex(obj))
    result: dict[so.Object, list[str]] = {}

    for (mcls, fn), referrers in refs.items():
        field = mcls.get_field(fn)
        if issubclass(field.type, (Expression, ExpressionList)):
            for ref in referrers:
                result.setdefault(ref, []).append(fn)

    return result
