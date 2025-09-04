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
from typing import TYPE_CHECKING, Any, Mapping, Optional

from dataclasses import dataclass

import os
import pathlib

from edb import errors
from edb.common import parsing

from . import annos as s_anno
from . import delta as sd
from . import name as sn
from . import schema as s_schema

if TYPE_CHECKING:
    from . import indexes as s_indexes
    from . import objtypes as s_objtypes


@dataclass(kw_only=True, frozen=True)
class ProviderDesc:
    """A description of an AI provider from a reference json."""
    name: str


@dataclass(kw_only=True, frozen=True)
class EmbeddingModelDesc:
    """A description of an AI embedding model from a reference json.

    The provider_label field is a short name which can be used in a URI.
    """
    model_name: str
    provider_label: str
    max_input_tokens: int
    max_batch_tokens: int
    max_output_dimensions: int
    supports_shortening: bool


@dataclass(kw_only=True, frozen=True)
class EmbeddingModelProperties:
    """Properties used by the AI extension.

    Really the only difference is that model_provider is "full".
    ie. "builtin::openai" instead "openai"
    """
    model_name: str
    model_provider: str
    max_input_tokens: int
    max_batch_tokens: int
    max_output_dimensions: int
    supports_shortening: bool


def get_local_reference_data() -> str:
    if test_reference_path := os.environ.get("EDGEDB_TEST_AI_REFERENCE_PATH"):
        local_reference_path = test_reference_path
    else:
        local_reference_path = os.path.join(
            pathlib.Path(__file__).parent.parent,
            'server',
            'protocol',
            'ai_reference.json',
        )
    with open(local_reference_path) as local_reference_file:
        return local_reference_file.read()


def load_reference_descs(reference_data: Mapping[str, Any]) -> Optional[
    tuple[
        Mapping[str, ProviderDesc],
        Mapping[str, EmbeddingModelDesc],
    ]
]:
    """Convert the ai extension refs into provider and model descs"""
    # Wrap the entire thing in a try block in case the json is malformed
    # for whatever reason.
    try:
        provider_descs: dict[str, ProviderDesc] = {}
        embedding_model_descs: dict[str, EmbeddingModelDesc] = {}

        if provider_ref := reference_data.get("providers"):
            for name, ref in provider_ref.items():
                provider_descs[name] = ProviderDesc(
                    name=ref["name"],
                )
        if embedding_models_ref := reference_data.get("embedding_models"):
            for name, ref in embedding_models_ref.items():
                embedding_model_descs[name] = EmbeddingModelDesc(
                    model_name=ref["model_name"],
                    provider_label=ref["provider_label"],
                    max_input_tokens=ref["max_input_tokens"],
                    max_batch_tokens=ref["max_batch_tokens"],
                    max_output_dimensions=ref["max_output_dimensions"],
                    supports_shortening=ref["supports_shortening"],
                )

        return (provider_descs, embedding_model_descs)

    except Exception:
        return None


def _get_embedding_model_properties_from_desc(
    provider_label: str,
    model_name: str,
    provider_descs: Mapping[str, ProviderDesc],
    embedding_model_descs: Mapping[str, EmbeddingModelDesc],
) -> Optional[EmbeddingModelProperties]:
    provider_desc = provider_descs.get(provider_label, None)
    model_desc = embedding_model_descs.get(model_name, None)
    if provider_desc is None or model_desc is None:
        return None
    if model_desc.provider_label != provider_label:
        return None
    return EmbeddingModelProperties(
        model_name=model_name,
        model_provider=provider_desc.name,
        max_input_tokens=model_desc.max_input_tokens,
        max_batch_tokens=model_desc.max_batch_tokens,
        max_output_dimensions=model_desc.max_output_dimensions,
        supports_shortening=model_desc.supports_shortening,
    )


_embedding_model = sn.QualName("ext::ai", "EmbeddingModel")
_model_name = sn.QualName("ext::ai", "model_name")


def _get_schema_embedding_model_types(
    schema: s_schema.Schema,
    model_name: Optional[str] = None,
) -> dict[str, s_objtypes.ObjectType]:
    from . import objtypes as s_objtypes

    base_embedding_model = schema.get(
        _embedding_model,
        type=s_objtypes.ObjectType,
    )

    def _flt(
        schema: s_schema.Schema,
        anno: s_anno.AnnotationValue,
    ) -> bool:
        if anno.get_shortname(schema) != _model_name:
            return False

        subject = anno.get_subject(schema)
        value = anno.get_value(schema)

        return (
            value is not None and value != "<must override>"
            and (model_name is None or anno.get_value(schema) == model_name)
            and isinstance(subject, s_objtypes.ObjectType)
            and subject.issubclass(schema, base_embedding_model)
        )

    annos = schema.get_objects(
        type=s_anno.AnnotationValue,
        extra_filters=(_flt,),
    )

    result = {}
    for anno in annos:
        subject = anno.get_subject(schema)
        assert isinstance(subject, s_objtypes.ObjectType)
        result[anno.get_value(schema)] = subject

    return result


def _get_schema_embedding_model_properties(
    model_stype: s_objtypes.ObjectType,
    schema: s_schema.Schema,
) -> EmbeddingModelProperties:
    model_name = model_stype.must_get_annotation(
        schema,
        sn.QualName("ext::ai", "model_name"),
    )
    model_provider = model_stype.must_get_annotation(
        schema,
        sn.QualName("ext::ai", "model_provider"),
    )
    max_input_tokens = model_stype.must_get_annotation_as_int(
        schema,
        sn.QualName("ext::ai", "embedding_model_max_input_tokens"),
    )
    max_batch_tokens = model_stype.must_get_annotation_as_int(
        schema,
        sn.QualName("ext::ai", "embedding_model_max_batch_tokens"),
    )
    max_output_dimensions = model_stype.must_get_annotation_as_int(
        schema,
        sn.QualName("ext::ai", "embedding_model_max_output_dimensions"),
    )
    supports_shortening = model_stype.must_get_annotation_as_bool(
        schema,
        sn.QualName("ext::ai", "embedding_model_supports_shortening"),
    )

    return EmbeddingModelProperties(
        model_name=model_name,
        model_provider=model_provider,
        max_input_tokens=max_input_tokens,
        max_batch_tokens=max_batch_tokens,
        max_output_dimensions=max_output_dimensions,
        supports_shortening=supports_shortening,
    )


def _get_ai_descs(extension_refs: Optional[Mapping[str, Any]]) -> tuple[
    Mapping[str, ProviderDesc],
    Mapping[str, EmbeddingModelDesc],
]:
    provider_descs: Mapping[str, ProviderDesc] = {}
    embedding_model_descs: Mapping[
        str, EmbeddingModelDesc
    ] = {}

    if (
        extension_refs is not None
        and (ai_extension_ref := extension_refs.get('ai', None))
        and (
            reference_descs := load_reference_descs(
                ai_extension_ref
            )
        )
    ):
        provider_descs, embedding_model_descs = reference_descs

    return provider_descs, embedding_model_descs


def get_index_embedding_model_properties(
    index: s_indexes.Index,
    schema: s_schema.Schema,
    context: sd.CommandContext,
    *,
    span: Optional[parsing.Span] = None
) -> tuple[
    EmbeddingModelProperties,
    Optional[s_objtypes.ObjectType],
]:
    """Get an AI Index's embedding model properties.

    Checks that the specified model exists in either the schema or the descs.
    If the model is from the schema, checks that the provider is consistent.
    """
    provider_descs, embedding_model_descs = _get_ai_descs(
        context.extension_refs
    )

    kwargs = index.get_concrete_kwargs_as_values(schema)

    model_name: str = kwargs["embedding_model"]

    provider_label = None
    model_provider = None
    if ':' in model_name:

        model_name_parts = model_name.split(':')
        if len(model_name_parts) > 2:
            raise errors.SchemaDefinitionError(
                f"Invalid model uri, ':' used more than once: {model_name}",
                span=span
            )

        provider_label = model_name_parts[0]
        model_name = model_name_parts[1]

        provider_desc = provider_descs.get(provider_label, None)
        if provider_desc is not None:
            model_provider = provider_desc.name

    models = _get_schema_embedding_model_types(schema, model_name)
    if len(models) == 0:
        # If a URI was used and no model type exists,
        # try to get properties from the descs directly.
        if (
            provider_label is not None
            and (
                model_properties := _get_embedding_model_properties_from_desc(
                    provider_label,
                    model_name,
                    provider_descs,
                    embedding_model_descs,
                )
            )
        ):
            return (model_properties, None)

        raise errors.SchemaDefinitionError(
            f'undefined embedding model: no subtype of '
            f'ext::ai::EmbeddingModel is annotated as {model_name!r}',
            span=span,
        )
    elif len(models) > 1:
        models_dn = [
            model.get_displayname(schema) for model in models.values()
        ]
        raise errors.SchemaDefinitionError(
            f'expecting only one embedding model to be annotated '
            f'with ext::ai::model_name={model_name!r}: got multiple: '
            f'{", ".join(models_dn)}',
            span=span,
        )

    model_stype = next(iter(models.values()))
    model_properties = _get_schema_embedding_model_properties(
        model_stype, schema
    )

    # If a URI was used and a model type exists,
    # ensure that the provider name matches
    if (
        provider_label is not None
        and model_properties.model_provider != model_provider
    ):
        # The URI will specify "openai" instead of "builtin::openai"
        # We want to show only "openai" in the case of an error here.
        model_provider_label = model_properties.model_provider
        for desc_label, provider_desc in provider_descs.items():
            if provider_desc.name == model_properties.model_provider:
                model_provider_label = desc_label
                break

        raise errors.SchemaDefinitionError(
            f"An embedding model with the name '{model_name}' "
            f"exists but the provider specified by the index "
            f"('{provider_label}') differs from the one "
            f"specified by the model ('{model_provider_label}').",
            span=span,
        )

    return (model_properties, model_stype)


def get_all_embedding_model_properties(
    schema: s_schema.Schema,
    context: sd.CommandContext,
) -> Mapping[str, EmbeddingModelProperties]:
    """Gets the model properties for all embeding models.

    If a model with the same name exists in both the schema and reference data,
    the schema takes priority.
    """

    all_model_properties: dict[str, EmbeddingModelProperties] = {}

    # Get all schema models
    schema_models = _get_schema_embedding_model_types(schema)
    for model_name, model_stype in schema_models.items():
        all_model_properties[model_name] = (
            _get_schema_embedding_model_properties(model_stype, schema)
        )

    # Get reference data models
    provider_descs, embedding_model_descs = _get_ai_descs(
        context.extension_refs
    )
    for model_name, model_desc in embedding_model_descs.items():
        if model_name in all_model_properties:
            # Model in schema
            continue

        if provider_desc := provider_descs.get(model_desc.provider_label, None):
            model_provider = provider_desc.name
        else:
            model_provider = model_desc.provider_label
        all_model_properties[model_name] = EmbeddingModelProperties(
            model_name=model_name,
            model_provider=model_provider,
            max_input_tokens=model_desc.max_input_tokens,
            max_batch_tokens=model_desc.max_batch_tokens,
            max_output_dimensions=model_desc.max_output_dimensions,
            supports_shortening=model_desc.supports_shortening,
        )

    return all_model_properties


def get_ai_index_id(
    schema: s_schema.Schema,
    index: s_indexes.Index,
) -> str:
    # TODO: Use the model name?
    return f'base'
