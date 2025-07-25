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


"""EdgeQL compiler routines for polymorphic call resolution."""


from __future__ import annotations

from typing import (
    Any,
    Optional,
    AbstractSet,
    Iterable,
    Mapping,
    Sequence,
    NamedTuple,
    cast,
)

import hashlib
import json

from edb import errors

from edb.ir import ast as irast
from edb.ir import utils as irutils

from edb.schema import functions as s_func
from edb.schema import name as sn
from edb.schema import types as s_types
from edb.schema import pseudo as s_pseudo
from edb.schema import expr as s_expr
from edb.schema import scalars as s_scalars
from edb.schema import schema as s_schema

from edb.edgeql import ast as qlast
from edb.edgeql import qltypes as ft

from . import context
from . import dispatch
from . import pathctx
from . import setgen
from . import tuple_args
from . import typegen


class BoundArg(NamedTuple):

    param: Optional[s_func.ParameterLike]
    param_type: s_types.Type
    val: irast.Set
    valtype: s_types.Type
    cast_distance: int
    arg_id: Optional[int | str]
    is_default: bool = False
    polymorphism: ft.Polymorphism = ft.Polymorphism.NotUsed


class MissingArg(NamedTuple):

    param: Optional[s_func.ParameterLike]
    param_type: s_types.Type


class BoundCall(NamedTuple):

    func: s_func.CallableLike
    args: list[BoundArg]
    null_args: set[str]
    return_type: s_types.Type
    variadic_arg_id: Optional[int]
    variadic_arg_count: Optional[int]
    return_polymorphism: ft.Polymorphism = ft.Polymorphism.NotUsed

    server_param_conversions: Optional[dict[
        str,
        dict[str, context.ServerParamConversion],
    ]] = None


_VARIADIC = ft.ParameterKind.VariadicParam
_NAMED_ONLY = ft.ParameterKind.NamedOnlyParam
_POSITIONAL = ft.ParameterKind.PositionalParam

_SET_OF = ft.TypeModifier.SetOfType
_OPTIONAL = ft.TypeModifier.OptionalType
_SINGLETON = ft.TypeModifier.SingletonType


def find_callable_typemods(
    candidates: Sequence[s_func.CallableLike],
    *,
    num_args: int,
    kwargs_names: AbstractSet[str],
    ctx: context.ContextLevel,
) -> dict[int | str, ft.TypeModifier]:
    """Find the type modifiers for a callable.

    We do this early, before we've compiled/checked the arguments,
    so that we can compile the arguments with the proper fences.
    """

    typ: s_types.Type = s_pseudo.PseudoType.get(ctx.env.schema, 'anytype')
    dummy = irast.DUMMY_SET
    args = [(typ, dummy)] * num_args
    kwargs = {k: (typ, dummy) for k in kwargs_names}
    options = find_callable(
        candidates, basic_matching_only=True, args=args, kwargs=kwargs, ctx=ctx
    )

    # No options means an error is going to happen later, but for now,
    # just return some placeholders so that we can make it to the
    # error later.
    if not options:
        return {k: _SINGLETON for k in set(range(num_args)) | kwargs_names}

    fts: dict[int | str, ft.TypeModifier] = {}
    for choice in options:
        for barg in choice.args:
            if not barg.param or barg.arg_id is None:
                continue
            ft = barg.param.get_typemod(ctx.env.schema)
            if barg.arg_id in fts and fts[barg.arg_id] != ft:
                if ft == _SET_OF or fts[barg.arg_id] == _SET_OF:
                    raise errors.QueryError(
                        f'argument could be SET OF or not in call to '
                        f'{candidates[0].get_verbosename(ctx.env.schema)}: '
                        f'seems like a stdlib bug!')
                else:
                    # If there is a mix between OPTIONAL and SINGLETON
                    # arguments in possible call sites, we just call it
                    # optional. Generated code quality will be a little
                    # worse but still correct.
                    fts[barg.arg_id] = _OPTIONAL
            else:
                fts[barg.arg_id] = ft

    return fts


def find_callable(
    candidates: Iterable[s_func.CallableLike],
    *,
    args: list[tuple[s_types.Type, irast.Set]],
    kwargs: dict[str, tuple[s_types.Type, irast.Set]],
    basic_matching_only: bool = False,
    ctx: context.ContextLevel,
) -> list[BoundCall]:

    implicit_cast_distance = None
    matched = []

    candidates = list(candidates)
    for candidate in candidates:
        call = None
        if (
            not basic_matching_only
            and (conversion := _check_server_arg_conversion(
                candidate, args, kwargs, ctx=ctx
            ))
        ):
            # If there is a server param conversion, the argument should be
            # treated as if it has already been converted.
            #
            # This means we need to check the other candidates to see if they
            # match the converted args.
            converted_args, converted_kwargs, converted_params = conversion

            for alt_candidate in candidates:
                if alt_candidate is candidate:
                    continue
                if call := try_bind_call_args(
                    converted_args,
                    converted_kwargs,
                    alt_candidate,
                    basic_matching_only,
                    ctx=ctx,
                    server_param_conversions=converted_params,
                ):
                    # A call which matches the conversion exists.
                    # Add the server param conversions to the env.
                    break

        else:
            call = try_bind_call_args(
                args, kwargs, candidate, basic_matching_only, ctx=ctx)

        if call is None:
            continue

        total_cd = sum(barg.cast_distance for barg in call.args)

        if implicit_cast_distance is None:
            implicit_cast_distance = total_cd
            matched.append(call)
        elif implicit_cast_distance == total_cd:
            matched.append(call)
        elif implicit_cast_distance > total_cd:
            implicit_cast_distance = total_cd
            matched = [call]

    if len(matched) <= 1:
        # Unambiguios resolution
        return matched

    else:
        # Ambiguous resolution, try to disambiguate by
        # checking for total type distance.
        type_dist = None
        remaining = []

        for call in matched:
            call_type_dist = 0

            for barg in call.args:
                if barg.param is None:
                    # Skip injected bitmask argument.
                    continue

                paramtype = barg.param.get_type(ctx.env.schema)
                arg_type_dist = barg.valtype.get_common_parent_type_distance(
                    paramtype, ctx.env.schema)
                call_type_dist += arg_type_dist

            if type_dist is None:
                type_dist = call_type_dist
                remaining.append(call)
            elif type_dist == call_type_dist:
                remaining.append(call)
            elif type_dist > call_type_dist:
                type_dist = call_type_dist
                remaining = [call]

        return remaining


def try_bind_call_args(
    args: Sequence[tuple[s_types.Type, irast.Set]],
    kwargs: Mapping[str, tuple[s_types.Type, irast.Set]],
    func: s_func.CallableLike,
    basic_matching_only: bool,
    *,
    ctx: context.ContextLevel,
    server_param_conversions: Optional[
        dict[str, dict[str, context.ServerParamConversion]]
    ] = None,
) -> Optional[BoundCall]:

    return_type = func.get_return_type(ctx.env.schema)
    is_abstract = func.get_abstract(ctx.env.schema)
    resolved_poly_base_type: Optional[s_types.Type] = None

    def _get_cast_distance(
        arg: irast.Set,
        arg_type: s_types.Type,
        param_type: s_types.Type,
    ) -> int:
        nonlocal resolved_poly_base_type
        if basic_matching_only:
            return 0

        if in_polymorphic_func:
            # Compiling a body of a polymorphic function.

            if arg_type.is_polymorphic(schema):
                if param_type.is_polymorphic(schema):
                    if arg_type.test_polymorphic(schema, param_type):
                        return 0
                    else:
                        return -1
                else:
                    if arg_type.resolve_polymorphic(schema, param_type):
                        return 0
                    else:
                        return -1

        if param_type.is_polymorphic(schema):
            if not arg_type.test_polymorphic(schema, param_type):
                return -1

            resolved = param_type.resolve_polymorphic(schema, arg_type)
            if resolved is None:
                return -1

            if resolved_poly_base_type is None:
                resolved_poly_base_type = resolved

            if resolved_poly_base_type == resolved:
                if is_abstract:
                    return s_types.MAX_TYPE_DISTANCE
                elif arg_type.is_range() and param_type.is_multirange():
                    # Ranges are implicitly cast into multiranges of the same
                    # type, so they are compatible as far as polymorphic
                    # resolution goes, but it's still 1 cast.
                    return 1
                else:
                    return 0

            ctx.env.schema, ct = (
                resolved_poly_base_type.find_common_implicitly_castable_type(
                    resolved,
                    ctx.env.schema,
                )
            )

            if ct is not None:
                # If we found a common implicitly castable type, we
                # refine our resolved_poly_base_type to be that as the
                # more general case.
                resolved_poly_base_type = ct
            else:
                # Try resolving a polymorphic argument type against the
                # resolved base type. This lets us handle cases like
                #  - if b then x else {}
                #  - if b then [1] else []
                # Though it is still unfortunately not smart enough
                # to handle the reverse case.
                if resolved.is_polymorphic(schema):
                    ct = resolved.resolve_polymorphic(
                        schema, resolved_poly_base_type)

            if ct is not None:
                return s_types.MAX_TYPE_DISTANCE if is_abstract else 0
            else:
                return -1

        if arg_type.issubclass(schema, param_type):
            return 0

        return arg_type.get_implicit_cast_distance(param_type, schema)

    schema = ctx.env.schema

    in_polymorphic_func = (
        ctx.env.options.func_params is not None and
        ctx.env.options.func_params.has_polymorphic(schema)
    )

    variadic_arg_id: Optional[int] = None
    variadic_arg_count: Optional[int] = None
    no_args_call = not args and not kwargs
    has_inlined_defaults = (
        func.has_inlined_defaults(schema)
        and not (
            isinstance(func, s_func.Function)
            and (
                func.get_volatility(schema) == ft.Volatility.Modifying
                or func.get_is_inlined(schema)
            )
        )
    )

    func_params = func.get_params(schema)

    if not func_params:
        if no_args_call:
            # Match: `func` is a function without parameters
            # being called with no arguments.
            bargs: list[BoundArg] = []
            if has_inlined_defaults:
                bytes_t = ctx.env.get_schema_type_and_track(
                    sn.QualName('std', 'bytes'))
                typeref = typegen.type_to_typeref(bytes_t, env=ctx.env)
                argval = setgen.ensure_set(
                    irast.BytesConstant(value=b'\x00', typeref=typeref),
                    typehint=bytes_t,
                    ctx=ctx)
                bargs = [BoundArg(None, bytes_t, argval, bytes_t, 0, -1)]
            return BoundCall(
                func,
                bargs,
                set(),
                return_type,
                None,
                None,
                server_param_conversions=server_param_conversions,
            )
        else:
            # No match: `func` is a function without parameters
            # being called with some arguments.
            return None

    named_only = func_params.find_named_only(schema)

    if no_args_call and func_params.has_required_params(schema):
        # A call without arguments and there is at least
        # one parameter without default.
        return None

    bound_args_prep: list[MissingArg | BoundArg] = []

    params = func_params.get_in_canonical_order(schema)
    nparams = len(params)
    nargs = len(args)
    has_missing_args = False

    ai = 0
    pi = 0
    matched_kwargs = 0

    # Bind NAMED ONLY arguments (they are compiled as first set of arguments).
    while True:
        if pi >= nparams:
            break

        param = params[pi]
        if param.get_kind(schema) is not _NAMED_ONLY:
            break

        pi += 1

        param_shortname = param.get_parameter_name(schema)
        param_type = param.get_type(schema)
        if param_shortname in kwargs:
            matched_kwargs += 1

            arg_type, arg_val = kwargs[param_shortname]
            cd = _get_cast_distance(arg_val, arg_type, param_type)
            if cd < 0:
                return None

            bound_args_prep.append(
                BoundArg(param, param_type, arg_val, arg_type, cd,
                         param_shortname))

        else:
            if param.get_default(schema) is None:
                # required named parameter without default and
                # without a matching argument
                return None

            has_missing_args = True
            bound_args_prep.append(MissingArg(param, param_type))

    if matched_kwargs != len(kwargs):
        # extra kwargs?
        return None

    # Bind POSITIONAL arguments (compiled to go after NAMED ONLY arguments).
    while True:
        if ai < nargs:
            arg_type, arg_val = args[ai]
            ai += 1

            if pi >= nparams:
                # too many positional arguments
                return None
            param = params[pi]
            param_type = param.get_type(schema)
            param_kind = param.get_kind(schema)
            pi += 1

            if param_kind is _NAMED_ONLY:
                # impossible condition
                raise RuntimeError('unprocessed NAMED ONLY parameter')

            if param_kind is _VARIADIC:
                param_type = cast(s_types.Array, param_type)
                var_type = param_type.get_subtypes(schema)[0]
                cd = _get_cast_distance(arg_val, arg_type, var_type)
                if cd < 0:
                    return None

                bound_args_prep.append(
                    BoundArg(param, param_type, arg_val, arg_type, cd, ai - 1))

                for di, (arg_type, arg_val) in enumerate(args[ai:]):
                    cd = _get_cast_distance(arg_val, arg_type, var_type)
                    if cd < 0:
                        return None

                    bound_args_prep.append(
                        BoundArg(param, param_type, arg_val, arg_type, cd,
                                 ai + di))

                variadic_arg_id = ai - 1
                variadic_arg_count = nargs - ai + 1

                break

            cd = _get_cast_distance(arg_val, arg_type, param_type)
            if cd < 0:
                return None

            bound_args_prep.append(
                BoundArg(param, param_type, arg_val, arg_type, cd, ai - 1))

        else:
            break

    # Handle yet unprocessed POSITIONAL & VARIADIC arguments.
    for i in range(pi, nparams):
        param = params[i]
        param_kind = param.get_kind(schema)

        if param_kind is _POSITIONAL:
            if param.get_default(schema) is None:
                # required positional parameter that we don't have a
                # positional argument for.
                return None

            has_missing_args = True
            param_type = param.get_type(schema)
            bound_args_prep.append(MissingArg(param, param_type))

        elif param_kind is _VARIADIC:
            variadic_arg_id = i
            variadic_arg_count = 0

        elif param_kind is _NAMED_ONLY:
            # impossible condition
            raise RuntimeError('unprocessed NAMED ONLY parameter')

    # Populate defaults.
    defaults_mask = 0
    null_args: set[str] = set()
    bound_param_args: list[BoundArg] = []
    if has_missing_args:
        if has_inlined_defaults or named_only:
            for i, barg in enumerate(bound_args_prep):
                if isinstance(barg, BoundArg):
                    bound_param_args.append(barg)
                    continue
                if barg.param is None:
                    # Shouldn't be possible; the code above takes care of this.
                    raise RuntimeError(
                        f'failed to resolve the parameter for the arg #{i}')

                param = barg.param
                param_shortname = param.get_parameter_name(schema)
                param_typemod = param.get_typemod(ctx.env.schema)
                null_args.add(param_shortname)

                defaults_mask |= 1 << i

                if not has_inlined_defaults:
                    param_default: Optional[s_expr.Expression] = (
                        param.get_default(schema)
                    )
                    assert param_default is not None
                    default = compile_arg(
                        param_default.parse(), param_typemod, ctx=ctx)

                empty_default = (
                    has_inlined_defaults or
                    irutils.is_empty(default)
                )

                param_type = param.get_type(schema)

                if empty_default and not basic_matching_only:
                    default_type = None

                    if param_type.is_any(schema):
                        if resolved_poly_base_type is None:
                            raise errors.QueryError(
                                f'could not resolve "anytype" type for the '
                                f'${param_shortname} parameter')
                        else:
                            default_type = resolved_poly_base_type
                    else:
                        default_type = param_type

                else:
                    default_type = param_type

                if has_inlined_defaults:
                    default = compile_arg(
                        qlast.TypeCast(
                            expr=qlast.Set(elements=[]),
                            type=typegen.type_to_ql_typeref(
                                default_type,
                                ctx=ctx,
                            ),
                        ),
                        ft.TypeModifier.OptionalType,
                        ctx=ctx,
                    )

                default = setgen.ensure_set(
                    default,
                    typehint=default_type,
                    ctx=ctx,
                )

                bound_param_args.append(
                    BoundArg(
                        param,
                        param_type,
                        default,
                        param_type,
                        0,
                        None,
                        True,
                    )
                )

        else:
            bound_param_args = [
                barg for barg in bound_args_prep if isinstance(barg, BoundArg)
            ]
    else:
        bound_param_args = cast(list[BoundArg], bound_args_prep)

    if has_inlined_defaults:
        # If we are compiling an EdgeQL function, inject the defaults
        # bit-mask as a first argument.
        bytes_t = ctx.env.get_schema_type_and_track(
            sn.QualName('std', 'bytes'))
        bm = defaults_mask.to_bytes(nparams // 8 + 1, 'little')
        typeref = typegen.type_to_typeref(bytes_t, env=ctx.env)
        bm_set = setgen.ensure_set(
            irast.BytesConstant(value=bm, typeref=typeref),
            typehint=bytes_t, ctx=ctx)
        bound_param_args.insert(
            0, BoundArg(None, bytes_t, bm_set, bytes_t, 0, None))

    return_polymorphism = ft.Polymorphism.NotUsed
    if return_type.is_polymorphic(schema):
        return_polymorphism = ft.Polymorphism.from_schema_type(return_type)

        if resolved_poly_base_type is not None:
            ctx.env.schema, return_type = return_type.to_nonpolymorphic(
                ctx.env.schema, resolved_poly_base_type)
        elif not in_polymorphic_func and not basic_matching_only:
            return None

    # resolved_poly_base_type may be legitimately None within
    # bodies of polymorphic functions
    if resolved_poly_base_type is not None:
        for i, barg in enumerate(bound_param_args):
            if barg.param_type.is_polymorphic(schema):
                ctx.env.schema, ptype = barg.param_type.to_nonpolymorphic(
                    ctx.env.schema, resolved_poly_base_type)
                polymorphism = ft.Polymorphism.from_schema_type(barg.param_type)
                bound_param_args[i] = BoundArg(
                    barg.param,
                    ptype,
                    barg.val,
                    barg.valtype,
                    barg.cast_distance,
                    barg.arg_id,
                    polymorphism=polymorphism
                )

    return BoundCall(
        func,
        bound_param_args,
        null_args,
        return_type,
        variadic_arg_id,
        variadic_arg_count,
        return_polymorphism=return_polymorphism,
        server_param_conversions=server_param_conversions,
    )


def _check_server_arg_conversion(
    func: s_func.CallableLike,
    args: list[tuple[s_types.Type, irast.Set]],
    kwargs: dict[str, tuple[s_types.Type, irast.Set]],
    *,
    ctx: context.ContextLevel,
) -> Optional[tuple[
    Sequence[tuple[s_types.Type, irast.Set]],
    Mapping[str, tuple[s_types.Type, irast.Set]],
    dict[str, dict[str, context.ServerParamConversion]],
]]:
    """Check if there is a server param conversion and get the effective args.

    Server param conversion allows the server to replace a function arg with
    another parameter which it computes before executing the query.

    For example when `ext::ai::search(anyobject, str)` is called, the server
    gets an embedding vector for string arg which it then substitutes into a
    call to `ext::ai::search(anyobject, array<float32>)`.

    If any conversions are applied, returns (args, kwargs) with new query
    parameters representing the converted parameters.
    """
    schema = ctx.env.schema

    func_params: s_func.FuncParameterList = cast(
        s_func.FuncParameterList,
        func.get_params(schema),
    )

    if arg_conversions_json := (
        isinstance(func, s_func.Function)
        and func.get_server_param_conversions(schema)
    ):
        curr_server_param_conversions: dict[
            str,
            dict[str, context.ServerParamConversion],
        ] = {}

        arg_conversions: dict[str, str | list[str]] = json.loads(
            arg_conversions_json
        )
        for arg_name, conversion_info in arg_conversions.items():
            if isinstance(conversion_info, str):
                conversion_name = conversion_info
            else:
                conversion_name = conversion_info[0]

            # Get the arg being converted
            arg_key: int | str
            arg: tuple[s_types.Type, irast.Set]
            param, arg_key, arg = _get_arg(
                func_params,
                arg_name,
                args,
                kwargs,
                error_msg=f'Server param conversion {conversion_name} error',
                schema=schema,
            )

            if arg[1].expr is None:
                # Dummy set, do nothing
                continue

            original_type: s_types.Type = arg[0].material_type(schema)[1]
            if original_type != param.get_type(schema):
                # Wrong param type, function candidate doesn't apply.
                # TODO: Check "any" params
                return None

            is_param_query_parameter = (
                isinstance(arg[1].expr, irast.QueryParameter)
                and not arg[1].expr.is_global
            )
            is_param_ir_constant = isinstance(arg[1].expr, irast.BaseConstant)
            if (
                not original_type.is_array()
                and not is_param_query_parameter
                and not is_param_ir_constant
            ):
                raise errors.QueryError(
                    f"Argument '{arg_name}' "
                    f"must be a constant or query parameter",
                    span=arg[1].expr.span,
                )
            elif (
                original_type.is_array()
                and not is_param_query_parameter
            ):
                # Array literals are normalized as expressions
                # For now, don't support them as constants
                raise errors.QueryError(
                    f"Argument '{arg_name}' must be a query parameter",
                    span=arg[1].expr.span,
                )

            # Get info about the conversion
            converted_type, additional_info, conversion_volatility = (
                _resolve_server_param_conversion(
                    func_params,
                    args,
                    kwargs,
                    conversion_name,
                    schema=schema,
                    conversion_info=(
                        conversion_info
                        if isinstance(conversion_info, list)
                        else None
                    )
                )
            )

            query_param_name: str
            constant_value: Optional[Any] = None
            if isinstance(arg[1].expr, irast.BaseConstant):
                # Currently only support str constants
                constant_expr = arg[1].expr
                if isinstance(constant_expr, irast.StringConstant):
                    constant_value = constant_expr.value
                elif isinstance(
                    constant_expr, (irast.IntegerConstant, irast.BigintConstant)
                ):
                    constant_value = int(constant_expr.value)
                elif isinstance(
                    constant_expr, (irast.FloatConstant, irast.DecimalConstant)
                ):
                    constant_value = float(constant_expr.value)
                else:
                    raise RuntimeError(
                        f'Unsupported constant argument: {arg_name}'
                    )
                # Use a hash of the text value as the name
                value_hash = (
                    hashlib.sha1(constant_expr.value.encode()).hexdigest()
                )
                query_param_name = f'const_{value_hash}'
            elif isinstance(arg[1].expr, irast.QueryParameter):
                query_param_name = arg[1].expr.name
            else:
                raise RuntimeError('Server param conversion has no parameter')

            # Create a substitute parameter set with the correct type
            existing_converted_path_id = None
            if (
                (curr_conversions := (
                    ctx.env.server_param_conversions.get(query_param_name, None)
                ))
                and (
                    existing_param_conversion := (
                        curr_conversions.get(conversion_name, None)
                    )
                )
            ):
                # If the param was converted in another call, reuse its path id
                existing_converted_path_id = existing_param_conversion.path_id

            converted_param_name = f'{query_param_name}~{conversion_name}'
            converted_required = (
                isinstance(arg[1].expr, irast.QueryParameter)
                and arg[1].expr.required
            )
            converted_typeref = typegen.type_to_typeref(
                converted_type, ctx.env
            )
            conversion_set: irast.Set = setgen.ensure_set(
                irast.QueryParameter(
                    name=converted_param_name,
                    required=converted_required,
                    typeref=converted_typeref,
                    span=arg[1].span,
                ),
                path_id=existing_converted_path_id,
                ctx=ctx,
            )

            if query_param_name not in curr_server_param_conversions:
                curr_server_param_conversions[query_param_name] = {}
            curr_conversions = (
                curr_server_param_conversions[query_param_name]
            )

            if existing_converted_path_id is None:
                # If this is the first time this conversion was applied to this
                # query param, save the conversion to be possibly reused by
                # another call.

                # Create the sub-params in case the resulting converted param
                # is a tuple. Currently, no such conversion exists, but this
                # is here to prepare for that distant future.
                sub_params = tuple_args.create_sub_params(
                    converted_param_name,
                    converted_required,
                    typeref=converted_typeref,
                    pt=converted_type,
                    is_func_param=True,
                    ctx=ctx
                )

                curr_conversions[conversion_name] = (
                    context.ServerParamConversion(
                        path_id=conversion_set.path_id,
                        ir_param=irast.Param(
                            name=converted_param_name,
                            required=converted_required,
                            schema_type=converted_type,
                            ir_type=converted_typeref,
                            sub_params=sub_params,
                        ),
                        additional_info=additional_info,
                        volatility=conversion_volatility,
                        script_param_index=(
                            list(ctx.env.script_params.keys()).index(
                                query_param_name
                            )
                            if query_param_name in ctx.env.script_params else
                            None
                        ),
                        constant_value=constant_value,
                    )
                )

                # Don't include the newly created irast.Param in
                # ctx.env.query_parameters.
                # Such parameters need to have a corresponding entry in
                # compiler.Context.Environment.script_params
                #
                # The parameters will be handled separately in fini_expression
                # and compile_ir_to_sql_tree.

            # Substitute the old arg
            if isinstance(arg_key, int):
                args = args.copy()
                args[arg_key] = (converted_type, conversion_set)
            else:
                kwargs = kwargs.copy()
                kwargs[arg_key] = (converted_type, conversion_set)

        if len(curr_server_param_conversions) != len(arg_conversions):
            # Not all conversions were applied, function candidate doesn't
            # apply.
            return None

        return args, kwargs, curr_server_param_conversions

    else:
        return None


def _resolve_server_param_conversion(
    func_params: s_func.FuncParameterList,
    args: list[tuple[s_types.Type, irast.Set]],
    kwargs: dict[str, tuple[s_types.Type, irast.Set]],
    conversion_name: str,
    *,
    schema: s_schema.Schema,
    conversion_info: Optional[list[str]] = None,
) -> tuple[
    s_types.Type,
    tuple[str, ...],
    ft.Volatility,
]:
    converted_type: s_types.Type
    additional_info: tuple[str, ...] = tuple()
    conversion_volatility: ft.Volatility

    if conversion_name == 'cast_int64_to_str':
        converted_type = schema.get(
            'std::str', type=s_scalars.ScalarType
        )
        conversion_volatility = ft.Volatility.Immutable

    elif conversion_name == 'cast_int64_to_str_volatile':
        converted_type = schema.get(
            'std::str', type=s_scalars.ScalarType
        )
        conversion_volatility = ft.Volatility.Volatile

    elif conversion_name == 'cast_int64_to_float64':
        converted_type = schema.get(
            'std::float64', type=s_scalars.ScalarType
        )
        conversion_volatility = ft.Volatility.Immutable

    elif conversion_name == 'join_str_array':
        assert conversion_info is not None
        separator = conversion_info[1]

        converted_type = schema.get(
            'std::str', type=s_scalars.ScalarType
        )
        additional_info = (separator,)
        conversion_volatility = ft.Volatility.Immutable

    elif conversion_name == 'ai_text_embedding':
        assert isinstance(conversion_info, list)
        object_param_name = conversion_info[1]

        converted_type = schema.get_global(
            s_types.Array,
            s_types.Array.generate_name(
                sn.QualName('std', 'float32')
            )
        )

        _, _, object_arg = _get_arg(
            func_params,
            object_param_name,
            args,
            kwargs,
            error_msg=f'Server param conversion {conversion_name} '
            f'error finding object argument',
            schema=schema,
        )

        object_type = object_arg[0].material_type(schema)[1]
        additional_info = (str(object_type.get_id(schema)),)
        conversion_volatility = ft.Volatility.Volatile

    else:
        raise RuntimeError(
            f'Unknown server param conversion: {conversion_name}'
        )

    return (
        converted_type,
        additional_info,
        conversion_volatility,
    )


def _get_arg(
    func_params: s_func.FuncParameterList,
    param_name: str,
    args: Sequence[tuple[s_types.Type, irast.Set]],
    kwargs: Mapping[str, tuple[s_types.Type, irast.Set]],
    *,
    error_msg: str,
    schema: s_schema.Schema,
) -> tuple[
    s_func.Parameter,
    int | str,
    tuple[s_types.Type, irast.Set],
]:
    param = func_params.get_by_name(name=param_name, schema=schema)
    if param is None:
        raise RuntimeError(
            f'{error_msg}: missing param "{param_name}"'
        )

    param_kind = param.get_kind(schema)
    if param_kind == ft.ParameterKind.PositionalParam:
        param_index: int = param.get_num(schema)
        return param, param_index, args[param_index]
    elif param_kind == ft.ParameterKind.NamedOnlyParam:
        return param, param_name, kwargs[param_name]
    else:
        raise RuntimeError(
            f'{error_msg}: variadic param "{param_name}" not allowed'
        )


def compile_arg(
    arg_ql: qlast.Expr,
    typemod: ft.TypeModifier,
    *,
    prefer_subquery_args: bool=False,
    ctx: context.ContextLevel,
) -> irast.Set:
    fenced = typemod is ft.TypeModifier.SetOfType
    optional = typemod is ft.TypeModifier.OptionalType

    # Create a branch for OPTIONAL ones. The OPTIONAL branch is to
    # have a place to mark as optional in the scope tree.
    # For fenced arguments we instead wrap it in a SELECT below.
    #
    # We also put a branch when we are trying to compile the argument
    # into a subquery, so that things it uses get bound locally.
    branched = optional or (prefer_subquery_args and not fenced)

    new = ctx.newscope(fenced=False) if branched else ctx.new()
    with new as argctx:
        if optional:
            argctx.path_scope.mark_as_optional()

        if fenced:
            arg_ql = qlast.SelectQuery(
                result=arg_ql, span=arg_ql.span,
                implicit=True, rptr_passthrough=True)

        argctx.implicit_limit = 0

        arg_ir = dispatch.compile(arg_ql, ctx=argctx)

        if optional:
            pathctx.register_set_in_scope(arg_ir, optional=True, ctx=ctx)

            if arg_ir.path_scope_id is None:
                pathctx.assign_set_scope(arg_ir, argctx.path_scope, ctx=argctx)

        elif branched:
            arg_ir = setgen.scoped_set(arg_ir, ctx=argctx)

        return arg_ir
