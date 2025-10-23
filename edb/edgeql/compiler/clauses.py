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


"""EdgeQL compiler functions to process shared clauses."""


from __future__ import annotations

from typing import Optional, Sequence

from edb.edgeql import ast as qlast
from edb.ir import ast as irast

from edb import errors
from edb.ir import utils as irutils
from edb.schema import name as sn
from edb.schema import operators as s_oper

from . import context
from . import dispatch
from . import polyres
from . import schemactx
from . import setgen
from . import typegen
from . import pathctx


def compile_where_clause(
    where: Optional[qlast.Base], *, ctx: context.ContextLevel
) -> Optional[irast.Set]:

    if where is None:
        return None

    if ctx.partial_path_prefix:
        pathctx.register_set_in_scope(ctx.partial_path_prefix, ctx=ctx)

    with ctx.newscope(fenced=True) as subctx:
        subctx.expr_exposed = context.Exposure.UNEXPOSED
        subctx.path_scope.unnest_fence = True
        subctx.disallow_dml = "in a FILTER clause"
        ir_expr = dispatch.compile(where, ctx=subctx)
        bool_t = ctx.env.get_schema_type_and_track(sn.QualName('std', 'bool'))
        ir_set = setgen.scoped_set(ir_expr, typehint=bool_t, ctx=subctx)

    return ir_set


def adjust_nones_order(
    ir_sortexpr: irast.Set,
    sort: qlast.SortExpr,
    *,
    ctx: context.ContextLevel,
) -> Optional[qlast.NonesOrder]:
    if sort.nones_order:
        return sort.nones_order

    # If we are doing an ORDER BY on a required property that has an
    # exclusive constraint and no nones_order specified, we want to
    # defualt to EMPTY LAST (or EMPTY FIRST for DESC).  Since the
    # property is required, this doesn't have a semantic impact, but
    # our exclusive constraints (sigh.) use a UNIQUE constraint,
    # which is always NULLS LAST.
    #
    # Postgres seems to *sometimes* be able to use the indexes without
    # this intervention, but not always?
    # See #8035.
    ir = irutils.unwrap_set(ir_sortexpr)
    expr = ir.expr
    if (
        isinstance(expr, irast.Pointer)
        and expr.source == ctx.partial_path_prefix
        and expr.dir_cardinality
        and not expr.dir_cardinality.can_be_zero()
        and isinstance(expr.ptrref, irast.PointerRef)
        and (ptr := typegen.ptrcls_from_ptrref(
            expr.ptrref, ctx=ctx,
        ))
        and bool(ptr.get_exclusive_constraints(ctx.env.schema))
    ):
        if sort.direction == qlast.SortOrder.Desc:
            return qlast.NonesOrder.First
        else:
            return qlast.NonesOrder.Last

    return None


def compile_orderby_clause(
    sortexprs: Optional[Sequence[qlast.SortExpr]], *, ctx: context.ContextLevel
) -> Optional[list[irast.SortExpr]]:

    if not sortexprs:
        return None

    result: list[irast.SortExpr] = []

    if ctx.partial_path_prefix:
        pathctx.register_set_in_scope(ctx.partial_path_prefix, ctx=ctx)

    with ctx.new() as subctx:
        subctx.expr_exposed = context.Exposure.UNEXPOSED
        subctx.disallow_dml = "in an ORDER BY clause"
        for sortexpr in sortexprs:
            with subctx.newscope(fenced=True) as exprctx:
                exprctx.path_scope.unnest_fence = True
                ir_sortexpr = dispatch.compile(sortexpr.path, ctx=exprctx)
                ir_sortexpr = setgen.scoped_set(
                    ir_sortexpr, force_reassign=True, ctx=exprctx)
                ir_sortexpr.span = sortexpr.span

                # Check that the sortexpr type is actually orderable
                # with either '>' or '<' based on the DESC or ASC sort
                # order.
                env = exprctx.env
                sort_type = setgen.get_set_type(ir_sortexpr, ctx=ctx)
                # Postgres by default treats ASC as using '<' and DESC
                # as using '>'. We should do the same.
                if sortexpr.direction == qlast.SortDesc:
                    op_name = '>'
                else:
                    op_name = '<'
                opers = s_oper.lookup_operators(
                    op_name,
                    module_aliases=exprctx.modaliases,
                    schema=env.schema
                )

                # Verify that a comparison operator is defined for 2
                # sort_type expressions.
                matched = polyres.find_callable(
                    opers,
                    args=[(sort_type, ir_sortexpr), (sort_type, ir_sortexpr)],
                    kwargs={},
                    ctx=exprctx)
                if len(matched) != 1:
                    sort_type_name = schemactx.get_material_type(
                        sort_type, ctx=ctx).get_displayname(env.schema)
                    if len(matched) == 0:
                        raise errors.QueryError(
                            f'type {sort_type_name!r} cannot be used in '
                            f'ORDER BY clause because ordering is not '
                            f'defined for it',
                            span=sortexpr.span)

                    elif len(matched) > 1:
                        raise errors.QueryError(
                            f'type {sort_type_name!r} cannot be used in '
                            f'ORDER BY clause because ordering is '
                            f'ambiguous for it',
                            span=sortexpr.span)

            result.append(
                irast.SortExpr(
                    expr=ir_sortexpr,
                    direction=sortexpr.direction,
                    nones_order=adjust_nones_order(
                        ir_sortexpr,
                        sortexpr,
                        ctx=ctx,
                    ),
                ))

    return result


def compile_limit_offset_clause(
    expr: Optional[qlast.Base], *, ctx: context.ContextLevel
) -> Optional[irast.Set]:
    if expr is None:
        ir_set = None
    else:
        with ctx.newscope(fenced=True) as subctx:
            subctx.expr_exposed = context.Exposure.UNEXPOSED
            # Clear out the partial_path_prefix, since we aren't in
            # the scope of the select subject
            subctx.partial_path_prefix = None

            ir_expr = dispatch.compile(expr, ctx=subctx)
            int_t = ctx.env.get_schema_type_and_track(
                sn.QualName('std', 'int64'))
            ir_set = setgen.scoped_set(
                ir_expr, force_reassign=True, typehint=int_t, ctx=subctx)
            ir_set.span = expr.span

    return ir_set
