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
# Do not import "from typing *"; this module contains
# AST classes that name-clash with classes from the typing module.

import typing

from edb.common import enum as s_enum
from edb.common import ast, parsing

from . import qltypes


DDLCommand_T = typing.TypeVar(
    'DDLCommand_T',
    bound='DDLCommand',
    covariant=True,
)

ObjectDDL_T = typing.TypeVar(
    'ObjectDDL_T',
    bound='ObjectDDL',
    covariant=True,
)


class SortOrder(s_enum.StrEnum):
    Asc = 'ASC'
    Desc = 'DESC'


SortAsc = SortOrder.Asc
SortDesc = SortOrder.Desc
SortDefault = SortAsc


class NonesOrder(s_enum.StrEnum):
    First = 'first'
    Last = 'last'


NonesFirst = NonesOrder.First
NonesLast = NonesOrder.Last


class CardinalityModifier(s_enum.StrEnum):
    Optional = 'OPTIONAL'
    Required = 'REQUIRED'


class DescribeGlobal(s_enum.StrEnum):
    Schema = 'SCHEMA'
    DatabaseConfig = 'DATABASE CONFIG'
    SystemConfig = 'SYSTEM CONFIG'
    Roles = 'ROLES'

    def to_edgeql(self) -> str:
        return self.value


class Base(ast.AST):
    __abstract_node__ = True
    __ast_hidden__ = {'context'}
    context: parsing.ParserContext
    # System-generated comment.
    system_comment: str

    # parent: typing.Optional[Base]


class OffsetLimitMixin(Base):
    __abstract_node__ = True
    offset: typing.Optional[Expr]
    limit: typing.Optional[Expr]


class OrderByMixin(Base):
    __abstract_node__ = True
    orderby: typing.Optional[typing.List[SortExpr]]


class FilterMixin(Base):
    __abstract_node__ = True
    where: typing.Optional[Expr]


class OptionValue(Base):
    """An option value resulting from a syntax."""

    name: str
    val: typing.Any


class Flag(OptionValue):

    val: bool


class Options(Base):

    options: typing.Dict[str, OptionValue]

    def get_flag(self, k: str) -> Flag:
        try:
            flag = self[k]
        except KeyError:
            return Flag(name=k, val=False)
        else:
            assert isinstance(flag, Flag)
            return flag

    def __getitem__(self, k: str) -> OptionValue:
        return self.options[k]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self.options)

    def __len__(self) -> int:
        return len(self.options)


class Expr(Base):
    """Abstract parent for all query expressions."""
    __abstract_node__ = True


class SubExpr(Base):
    """A subexpression (used for anchors)."""

    expr: Expr
    anchors: typing.Dict[str, typing.Any]


class Clause(Base):
    """Abstract parent for all query clauses."""
    __abstract_node__ = True


class SortExpr(Clause):
    path: Expr
    direction: typing.Optional[SortOrder]
    nones_order: typing.Optional[str]


class BaseAlias(Clause):
    __abstract_node__ = True
    alias: typing.Optional[str]


class AliasedExpr(BaseAlias):
    expr: Expr
    alias: str


class ModuleAliasDecl(BaseAlias):
    module: str


class BaseSessionCommand(Base):
    __abstract_node__ = True


class BaseSessionSet(BaseSessionCommand):
    __abstract_node__ = True


class BaseSessionConfigSet(BaseSessionSet):
    __abstract_node__ = True
    system: bool = False


class SessionSetAliasDecl(ModuleAliasDecl, BaseSessionSet):
    pass


class BaseSessionReset(BaseSessionCommand):
    __abstract_node__ = True


class SessionResetAliasDecl(BaseAlias, BaseSessionReset):
    alias: str


class SessionResetModule(BaseSessionReset):
    pass


class SessionResetAllAliases(BaseSessionReset):
    pass


class BaseObjectRef(Base):
    __abstract_node__ = True


class ObjectRef(BaseObjectRef):
    name: str
    module: typing.Optional[str]
    itemclass: typing.Optional[qltypes.SchemaObjectClass]


class PseudoObjectRef(BaseObjectRef):
    __abstract_node__ = True


class AnyType(PseudoObjectRef):
    pass


class AnyTuple(PseudoObjectRef):
    pass


class Anchor(Expr):
    __abstract_node__ = True
    name: str


class SpecialAnchor(Anchor):
    __abstract_node__ = True


class Source(SpecialAnchor):  # __source__
    name: str = '__source__'


class Subject(SpecialAnchor):  # __subject__
    name: str = '__subject__'


class DetachedExpr(Expr):  # DETACHED Expr
    expr: Expr


class Index(Base):
    index: Expr


class Slice(Base):
    start: typing.Optional[Expr]
    stop: typing.Optional[Expr]


class Indirection(Expr):
    arg: Expr
    indirection: typing.List[typing.Union[Index, Slice]]


class BinOp(Expr):
    left: Expr
    op: str
    right: Expr


class WindowSpec(Clause, OrderByMixin):
    orderby: typing.List[SortExpr]
    partition: typing.List[Expr]


class FunctionCall(Expr):
    func: typing.Union[tuple, str]
    args: typing.List[Expr]
    kwargs: typing.Dict[str, Expr]
    window: typing.Optional[WindowSpec]


class BaseConstant(Expr):
    __abstract_node__ = True
    value: str

    @classmethod
    def from_python(cls, val: typing.Any) -> BaseConstant:
        raise NotImplementedError


class StringConstant(BaseConstant):

    @classmethod
    def from_python(cls, s: str) -> StringConstant:
        return cls(value=s)


class BaseRealConstant(BaseConstant):
    __abstract_node__ = True
    is_negative: bool = False


class IntegerConstant(BaseRealConstant):
    pass


class FloatConstant(BaseRealConstant):
    pass


class BigintConstant(BaseRealConstant):
    pass


class DecimalConstant(BaseRealConstant):
    pass


class BooleanConstant(BaseConstant):

    @classmethod
    def from_python(cls, b: bool) -> BooleanConstant:
        return cls(value=str(b).lower())


class BytesConstant(BaseConstant):
    # This should really just be str to match, though
    value: bytes  # type: ignore[assignment]

    @classmethod
    def from_python(cls, s: bytes) -> BytesConstant:
        return cls(value=s)


class Parameter(Expr):
    name: str
    optional: bool


class UnaryOp(Expr):
    op: str
    operand: Expr


class TypeExpr(Base):
    name: str  # name is used for types in named tuples


class TypeOf(TypeExpr):
    expr: Expr


class TypeExprLiteral(TypeExpr):
    # Literal type exprs are used in enum declarations.
    val: StringConstant


class TypeName(TypeExpr):
    maintype: BaseObjectRef
    subtypes: typing.Optional[typing.List[TypeExpr]]
    dimensions: typing.Optional[typing.List[int]]


class TypeOp(TypeExpr):
    left: TypeExpr
    op: str
    right: TypeExpr


class FuncParam(Base):
    name: str
    type: TypeExpr
    typemod: qltypes.TypeModifier = qltypes.TypeModifier.SingletonType
    kind: qltypes.ParameterKind
    default: typing.Optional[Expr]


class IsOp(Expr):
    left: Expr
    op: str
    right: TypeExpr


class TypeIntersection(Base):
    type: TypeExpr


class Ptr(Base):
    ptr: ObjectRef
    direction: typing.Optional[str]
    type: typing.Optional[str]


class Path(Expr):
    steps: typing.List[typing.Union[Expr, Ptr, TypeIntersection, ObjectRef]]
    partial: bool = False


class TypeCast(Expr):
    expr: Expr
    type: TypeExpr
    cardinality_mod: typing.Optional[CardinalityModifier]


class Introspect(Expr):
    type: TypeExpr


class IfElse(Expr):
    condition: Expr
    if_expr: Expr
    else_expr: Expr


class TupleElement(Base):
    name: ObjectRef
    val: Expr


class NamedTuple(Expr):
    elements: typing.List[TupleElement]


class Tuple(Expr):
    elements: typing.List[Expr]


class Array(Expr):
    elements: typing.List[Expr]


class Set(Expr):
    elements: typing.List[Expr]


# Expressions used only in statements
#

class ByExprBase(Base):
    '''Abstract parent of all grouping sets.'''
    __abstract_node__ = True


class ByExpr(ByExprBase):
    each: bool
    expr: Expr


class GroupBuiltin(ByExprBase):
    name: str
    elements: typing.List[ByExpr]


# Statements
#

class Command(Base):
    __abstract_node__ = True
    aliases: typing.List[typing.Union[AliasedExpr, ModuleAliasDecl]]


class Statement(Command, Expr):
    __abstract_node__ = True


class SubjectMixin(Base):
    __abstract_node__ = True
    subject: Expr
    subject_alias: typing.Optional[str]


class ReturningMixin(Base):
    __abstract_node__ = True
    result: Expr
    result_alias: typing.Optional[str]


class SelectClauseMixin(OrderByMixin, OffsetLimitMixin, FilterMixin):
    __abstract_node__ = True
    implicit: bool = False


class ShapeOp(s_enum.StrEnum):

    APPEND = 'APPEND'
    SUBTRACT = 'SUBTRACT'
    ASSIGN = 'ASSIGN'


# Need indirection over ShapeOp to preserve the source context.
class ShapeOperation(Base):

    op: ShapeOp


class ShapeElement(OffsetLimitMixin, OrderByMixin, FilterMixin, Expr):
    expr: Path
    elements: typing.List[ShapeElement]
    compexpr: typing.Optional[Expr]
    cardinality: typing.Optional[qltypes.SchemaCardinality]
    required: bool = False
    operation: ShapeOperation = ShapeOperation(op=ShapeOp.ASSIGN)


class Shape(Expr):
    expr: Expr
    elements: typing.List[ShapeElement]


class SelectQuery(Statement, ReturningMixin, SelectClauseMixin):
    pass


class GroupQuery(SelectQuery, SubjectMixin):
    using: typing.List[AliasedExpr]
    by: typing.List[Expr]
    into: str


class InsertQuery(Statement, SubjectMixin):
    subject: Path
    shape: typing.List[ShapeElement]
    unless_conflict: typing.Optional[
        typing.Tuple[typing.Optional[Expr], typing.Optional[Expr]]]


class UpdateQuery(Statement, SubjectMixin, FilterMixin):
    shape: typing.List[ShapeElement]


class DeleteQuery(Statement, SubjectMixin, SelectClauseMixin):
    pass


class ForQuery(Statement, ReturningMixin):
    iterator: Expr
    iterator_alias: str


# Transactions
#

class Transaction(Base):
    '''Abstract parent for all transaction operations.'''
    __abstract_node__ = True


class StartTransaction(Transaction):
    isolation: typing.Optional[qltypes.TransactionIsolationLevel] = None
    access: typing.Optional[qltypes.TransactionAccessMode] = None
    deferrable: typing.Optional[qltypes.TransactionDeferMode] = None


class CommitTransaction(Transaction):
    pass


class RollbackTransaction(Transaction):
    pass


class DeclareSavepoint(Transaction):

    name: str


class RollbackToSavepoint(Transaction):

    name: str


class ReleaseSavepoint(Transaction):

    name: str


# DDL
#

class DDL(Base):
    '''Abstract parent for all DDL statements.'''
    __abstract_node__ = True


class BasesMixin(DDL):
    __abstract_node__ = True
    bases: typing.List[TypeName]


class Position(DDL):
    ref: typing.Optional[ObjectRef]
    position: str


class DDLOperation(DDL):
    __abstract_node__ = True
    commands: typing.List[DDLOperation]


class DDLCommand(Command, DDLOperation):
    __abstract_node__ = True


class AlterAddInherit(DDLOperation, BasesMixin):
    position: typing.Optional[Position]


class AlterDropInherit(DDLOperation, BasesMixin):
    pass


class OnTargetDelete(DDLOperation):
    cascade: qltypes.LinkTargetDeleteAction


class SetField(DDLOperation):
    name: str
    value: typing.Union[Expr, TypeExpr, None]
    #: Indicates that this AST originated from a special DDL syntax
    #: rather than from a generic `SET field := value` statement, and
    #: so must not be subject to the "allow_ddl_set" constraint.
    #: This attribute is also considered by the codegen to emit appropriate
    #: syntax.
    special_syntax: bool = False


class SetPointerType(SetField):
    name: str = 'target'
    special_syntax: bool = True
    value: TypeExpr
    cast_expr: typing.Optional[Expr]


class NamedDDL(DDLCommand):
    __abstract_node__ = True
    name: ObjectRef


class ObjectDDL(NamedDDL):
    __abstract_node__ = True


class CreateObject(ObjectDDL):
    is_abstract: bool = False
    sdl_alter_if_exists: bool = False
    create_if_not_exists: bool = False


class AlterObject(ObjectDDL):
    pass


class DropObject(ObjectDDL):
    pass


class CreateExtendingObject(CreateObject, BasesMixin):
    is_final: bool = False


class Rename(NamedDDL):
    new_name: ObjectRef

    @property
    def name(self) -> ObjectRef:  # type: ignore[override]  # mypy bug?
        return self.new_name


class Migration:
    __abstract_node__ = True


class MigrationBody(DDL):

    commands: typing.List[DDLOperation]


class CreateMigration(CreateObject, Migration):

    body: MigrationBody
    script: typing.Optional[str] = None
    parent: typing.Optional[ObjectRef] = None
    message: typing.Optional[str] = None
    metadata_only: bool = False


class StartMigration(DDLCommand, Migration):

    target: Schema


class AbortMigration(DDLCommand, Migration):
    pass


class PopulateMigration(DDLCommand, Migration):
    pass


class AlterCurrentMigrationRejectProposed(DDLCommand, Migration):
    pass


class DescribeCurrentMigration(DDLCommand, Migration):

    language: qltypes.DescribeLanguage


class CommitMigration(DDLCommand, Migration):
    pass


class AlterMigration(AlterObject, Migration):
    pass


class DropMigration(DropObject, Migration):
    pass


class Database:
    __abstract_node__ = True


class CreateDatabase(CreateObject, Database):

    template: typing.Optional[ObjectRef] = None


class AlterDatabase(AlterObject, Database):
    pass


class DropDatabase(DropObject, Database):
    pass


class CreateModule(CreateObject):
    pass


class AlterModule(AlterObject):
    pass


class DropModule(DropObject):
    pass


class Role:
    __abstract_node__ = True


class CreateRole(CreateObject, BasesMixin, Role):
    superuser: bool = False


class AlterRole(AlterObject, Role):
    pass


class DropRole(DropObject, Role):
    pass


class CreateAnnotation(CreateExtendingObject):
    type: typing.Optional[TypeExpr]
    inheritable: bool


class AlterAnnotation(AlterObject):
    pass


class DropAnnotation(DropObject):
    pass


class CreatePseudoType(CreateObject):
    pass


class CreateScalarType(CreateExtendingObject):
    pass


class AlterScalarType(AlterObject):
    pass


class DropScalarType(DropObject):
    pass


class CreateProperty(CreateExtendingObject):
    pass


class AlterProperty(AlterObject):
    pass


class DropProperty(DropObject):
    pass


class CreateConcretePointer(CreateObject, BasesMixin):
    is_required: typing.Optional[bool] = None
    declared_overloaded: bool = False
    target: typing.Optional[typing.Union[Expr, TypeExpr]]
    cardinality: qltypes.SchemaCardinality


class CreateConcreteProperty(CreateConcretePointer):
    pass


class AlterConcreteProperty(AlterObject):
    pass


class DropConcreteProperty(DropObject):
    pass


class CreateObjectType(CreateExtendingObject):
    pass


class AlterObjectType(AlterObject):
    pass


class DropObjectType(DropObject):
    pass


class CreateAlias(CreateObject):
    pass


class AlterAlias(AlterObject):
    pass


class DropAlias(DropObject):
    pass


class CreateLink(CreateExtendingObject):
    pass


class AlterLink(AlterObject):
    pass


class DropLink(DropObject):
    pass


class CreateConcreteLink(CreateExtendingObject, CreateConcretePointer):
    pass


class AlterConcreteLink(AlterObject):
    pass


class DropConcreteLink(DropObject):
    pass


class CallableObject(ObjectDDL):
    __abstract_node__ = True
    params: typing.List[FuncParam]


class CreateConstraint(CreateExtendingObject, CallableObject):
    subjectexpr: typing.Optional[Expr]
    is_abstract: bool = True


class AlterConstraint(AlterObject):
    pass


class DropConstraint(DropObject):
    pass


class ConstraintOp(ObjectDDL):
    __abstract_node__ = True
    args: typing.List[Expr]
    subjectexpr: typing.Optional[Expr]


class CreateConcreteConstraint(CreateObject, ConstraintOp):
    delegated: bool = False


class AlterConcreteConstraint(AlterObject, ConstraintOp):
    pass


class DropConcreteConstraint(DropObject, ConstraintOp):
    pass


class IndexOp(ObjectDDL):
    __abstract_node__ = True
    expr: Expr


class CreateIndex(CreateObject, IndexOp):
    pass


class AlterIndex(AlterObject, IndexOp):
    pass


class DropIndex(DropObject, IndexOp):
    pass


class CreateAnnotationValue(CreateObject):
    value: Expr


class AlterAnnotationValue(AlterObject):
    value: Expr


class DropAnnotationValue(DropObject):
    pass


class Language(s_enum.StrEnum):
    SQL = 'SQL'
    EdgeQL = 'EDGEQL'


class FunctionCode(Clause):
    language: Language
    code: typing.Optional[str]
    nativecode: typing.Optional[Expr]
    from_function: typing.Optional[str]
    from_expr: bool


class CreateFunction(CreateObject, CallableObject):
    returning: TypeExpr
    code: FunctionCode
    nativecode: typing.Optional[Expr]
    returning_typemod: qltypes.TypeModifier = \
        qltypes.TypeModifier.SingletonType


class AlterFunction(AlterObject, CallableObject):
    code: FunctionCode
    nativecode: typing.Optional[Expr]


class DropFunction(DropObject, CallableObject):
    pass


class OperatorCode(Clause):
    language: Language
    from_operator: typing.Optional[typing.Tuple[str, ...]]
    from_function: str
    from_expr: bool
    code: str


class OperatorCommand(CallableObject):
    __abstract_node__ = True
    kind: qltypes.OperatorKind


class CreateOperator(CreateObject, OperatorCommand):
    returning: TypeExpr
    returning_typemod: qltypes.TypeModifier = \
        qltypes.TypeModifier.SingletonType
    code: OperatorCode


class AlterOperator(AlterObject, OperatorCommand):
    pass


class DropOperator(DropObject, OperatorCommand):
    pass


class CastCode(Clause):
    language: Language
    from_function: str
    from_expr: bool
    from_cast: bool
    code: str


class CastCommand(ObjectDDL):
    __abstract_node__ = True
    from_type: TypeName
    to_type: TypeName


class CreateCast(CreateObject, CastCommand):
    code: CastCode
    allow_implicit: bool
    allow_assignment: bool


class AlterCast(AlterObject, CastCommand):
    pass


class DropCast(DropObject, CastCommand):
    pass


class _Optional(Expr):
    expr: Expr


#
# Config
#


class ConfigOp(Expr):
    __abstract_node__ = True
    name: ObjectRef
    scope: qltypes.ConfigScope
    backend_setting: str


class ConfigSet(ConfigOp):

    expr: Expr


class ConfigInsert(ConfigOp):

    shape: typing.List[ShapeElement]


class ConfigReset(ConfigOp, FilterMixin):
    pass


#
# Describe
#

class DescribeStmt(Statement):

    language: qltypes.DescribeLanguage
    object: typing.Union[ObjectRef, DescribeGlobal]
    options: Options


#
# SDL
#


class SDL(Base):
    '''Abstract parent for all SDL statements.'''
    __abstract_node__ = True


class ModuleDeclaration(SDL):
    # The 'name' is treated same as in CreateModule, for consistency,
    # since this declaration also implies creating a module.
    name: ObjectRef
    declarations: typing.List[DDL]


class Schema(SDL):
    declarations: typing.List[typing.Union[NamedDDL, ModuleDeclaration]]


#
# These utility functions work on EdgeQL AST nodes
#


def get_targets(target: typing.Union[None, TypeExpr, Expr]):
    if target is None:
        return []
    elif isinstance(target, TypeOp):
        return get_targets(target.left) + get_targets(target.right)
    else:
        return [target]


def get_ddl_field_command(
    ddlcmd: DDLOperation,
    name: str,
) -> typing.Optional[SetField]:
    for cmd in ddlcmd.commands:
        if isinstance(cmd, SetField) and cmd.name == name:
            return cmd

    return None


def get_ddl_field_value(
    ddlcmd: DDLOperation,
    name: str,
) -> typing.Union[Expr, TypeExpr, None]:
    cmd = get_ddl_field_command(ddlcmd, name)
    return cmd.value if cmd is not None else None


def has_ddl_subcommand(
    ddlcmd: DDLOperation,
    cmdtype: typing.Type[DDLOperation],
) -> bool:
    for cmd in ddlcmd.commands:
        if isinstance(cmd, cmdtype):
            return True
    else:
        return False
