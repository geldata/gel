#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2016-present MagicStack Inc. and the EdgeDB authors.
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


"""Patches copied over from 6.x.

Deeply unfortunately, we need to be able to apply the user_ext patches...

"""

from __future__ import annotations


"""
The actual list of patches. The patches are (kind, script) pairs.

The current kinds are:
 * sql - simply runs a SQL script
 * metaschema-sql - create a function from metaschema
 * edgeql - runs an edgeql DDL command
 * edgeql+schema - runs an edgeql DDL command and updates the std schemas
 *                 NOTE: objects and fields added to the reflschema must
 *                 have their patch_level set to the `get_patch_level` value
 *                 for this patch.
 * edgeql+user_ext|<extname> - updates extensions installed in user databases
 *                           - should be paired with an ext-pkg patch
 * ...+config - updates config views
 * ext-pkg - installs an extension package given a name
 * repair - fix up inconsistencies in *user* schemas
 * sql-introspection - refresh all sql introspection views
 * ...+testmode - only run the patch in testmode. Works with any patch kind.
"""
PATCHES: list[tuple[str, str]] = [
    # 6.0b2
    # One of the sql-introspection's adds a param with a default to
    # uuid_to_oid, so we need to drop the original to avoid ambiguity.
    ('sql', '''
drop function if exists edgedbsql_v6_2f20b3fed0.uuid_to_oid(uuid) cascade
'''),
    ('sql-introspection', ''),
    ('metaschema-sql', 'SysConfigFullFunction'),
    # 6.0rc1
    ('edgeql+schema+config+testmode', '''
CREATE SCALAR TYPE cfg::TestEnabledDisabledEnum
    EXTENDING enum<Enabled, Disabled>;
ALTER TYPE cfg::AbstractConfig {
    CREATE PROPERTY __check_function_bodies -> cfg::TestEnabledDisabledEnum {
        CREATE ANNOTATION cfg::internal := 'true';
        CREATE ANNOTATION cfg::backend_setting := '"check_function_bodies"';
        SET default := cfg::TestEnabledDisabledEnum.Enabled;
    };
};
'''),
    ('metaschema-sql', 'PostgresConfigValueToJsonFunction'),
    ('metaschema-sql', 'SysConfigFullFunction'),
    ('edgeql', '''
ALTER FUNCTION
std::assert_single(
    input: SET OF anytype,
    NAMED ONLY message: OPTIONAL str = <str>{},
) {
    SET volatility := 'Immutable';
};
ALTER FUNCTION
std::assert_exists(
    input: SET OF anytype,
    NAMED ONLY message: OPTIONAL str = <str>{},
) {
    SET volatility := 'Immutable';
};
ALTER FUNCTION
std::assert_distinct(
    input: SET OF anytype,
    NAMED ONLY message: OPTIONAL str = <str>{},
) {
    SET volatility := 'Immutable';
};
'''),
     ('edgeql+schema+config', '''
CREATE SCALAR TYPE sys::TransactionAccessMode
    EXTENDING enum<ReadOnly, ReadWrite>;


CREATE SCALAR TYPE sys::TransactionDeferrability
    EXTENDING enum<Deferrable, NotDeferrable>;

ALTER TYPE cfg::AbstractConfig {
    CREATE REQUIRED PROPERTY default_transaction_isolation
        -> sys::TransactionIsolation
    {
        CREATE ANNOTATION cfg::affects_compilation := 'true';
        CREATE ANNOTATION cfg::backend_setting :=
            '"default_transaction_isolation"';
        CREATE ANNOTATION std::description :=
            'Controls the default isolation level of each new transaction, \
            including implicit transactions. Defaults to `Serializable`. \
            Note that changing this to a lower isolation level implies \
            that the transactions are also read-only by default regardless \
            of the value of the `default_transaction_access_mode` setting.';
        SET default := sys::TransactionIsolation.Serializable;
    };

    CREATE REQUIRED PROPERTY default_transaction_access_mode
        -> sys::TransactionAccessMode
    {
        CREATE ANNOTATION cfg::affects_compilation := 'true';
        CREATE ANNOTATION std::description :=
            'Controls the default read-only status of each new transaction, \
            including implicit transactions. Defaults to `ReadWrite`. \
            Note that if `default_transaction_isolation` is set to any value \
            other than Serializable this parameter is implied to be \
            `ReadOnly` regardless of the actual value.';
        SET default := sys::TransactionAccessMode.ReadWrite;
    };

    CREATE REQUIRED PROPERTY default_transaction_deferrable
        -> sys::TransactionDeferrability
    {
        CREATE ANNOTATION cfg::backend_setting :=
            '"default_transaction_deferrable"';
        CREATE ANNOTATION std::description :=
            'Controls the default deferrable status of each new transaction. \
            It currently has no effect on read-write transactions or those \
            operating at isolation levels lower than `Serializable`. \
            The default is `NotDeferrable`.';
        SET default := sys::TransactionDeferrability.NotDeferrable;
    };
};
'''),
    # 6.2
    ('ext-pkg', 'ai'),
    ('edgeql+user_ext+config|ai', '''
alter type ext::ai::EmbeddingModel {
    drop annotation
      ext::ai::embedding_model_max_batch_tokens;
    create annotation
      ext::ai::embedding_model_max_batch_tokens := "8191";
}
'''),
    # 6.3
    ('repair', ''),  # For #8466
    # 6.5
    ('sql-introspection', ''),  # For #8511
    ('edgeql+user_ext|ai', r'''
update ext::ai::ChatPrompt filter .name = 'builtin::rag-default' set {
    messages += (insert ext::ai::ChatPromptMessage {
                    participant_role := ext::ai::ChatParticipantRole.User,
                    content := (
                        "Query: {query}\n\
                         Answer: "
                    ),
                })
}
'''),  # For #8553
    # 6.6
    ('edgeql+schema', ''),  # For #8554
    ('ext-pkg', 'ai'),  # For #8521, #8646
    ('edgeql+user_ext+config|ai', '''
    create function ext::ai::search(
        object: anyobject,
        query: str,
    ) -> optional tuple<object: anyobject, distance: float64>
    {
        create annotation std::description := '
            Search an object using its ext::ai::index index.
            Gets an embedding for the query from the ai provider then
            returns objects that match the specified semantic query and the
            similarity score.
        ';
        set volatility := 'Stable';
        # Needed to pick up the indexes when used in ORDER BY.
        set prefer_subquery_args := true;
        set server_param_conversions :=
            '{"query": ["ai_text_embedding", "object"]}';
        using sql expression;
    };

    alter scalar type ext::ai::ProviderAPIStyle
        extending enum<OpenAI, Anthropic, Ollama>;

    create type ext::ai::OllamaProviderConfig
      extending ext::ai::ProviderConfig {
        alter property name {
            set protected := true;
            set default := 'builtin::ollama';
        };

        alter property display_name {
            set protected := true;
            set default := 'Ollama';
        };

        alter property api_url {
            set default := 'http://localhost:11434/api'
        };

        alter property secret {
            set default := ''
        };

        alter property api_style {
            set protected := true;
            set default := ext::ai::ProviderAPIStyle.Ollama;
        };
    };

    # Ollama embedding models
    create abstract type ext::ai::OllamaLlama_3_2_Model
        extending ext::ai::TextGenerationModel
    {
        alter annotation
            ext::ai::model_name := "llama3.2";
        alter annotation
            ext::ai::model_provider := "builtin::ollama";
        alter annotation
            ext::ai::text_gen_model_context_window := "131072";
    };

    create abstract type ext::ai::OllamaLlama_3_3_Model
        extending ext::ai::TextGenerationModel
    {
        alter annotation
            ext::ai::model_name := "llama3.3";
        alter annotation
            ext::ai::model_provider := "builtin::ollama";
        alter annotation
            ext::ai::text_gen_model_context_window := "131072";
    };

    create abstract type ext::ai::OllamaNomicEmbedTextModel
        extending ext::ai::EmbeddingModel
    {
        alter annotation
            ext::ai::model_name := "nomic-embed-text";
        alter annotation
            ext::ai::model_provider := "builtin::ollama";
        alter annotation
            ext::ai::embedding_model_max_input_tokens := "8192";
        alter annotation
            ext::ai::embedding_model_max_batch_tokens := "8192";
        alter annotation
            ext::ai::embedding_model_max_output_dimensions := "768";
    };

    create abstract type ext::ai::OllamaBgeM3Model
        extending ext::ai::EmbeddingModel
    {
        alter annotation
            ext::ai::model_name := "bge-m3";
        alter annotation
            ext::ai::model_provider := "builtin::ollama";
        alter annotation
            ext::ai::embedding_model_max_input_tokens := "8192";
        alter annotation
            ext::ai::embedding_model_max_batch_tokens := "8192";
        alter annotation
            ext::ai::embedding_model_max_output_dimensions := "1024";
    };
'''),
    # 6.8
    ('edgeql+user+remove_pointless_triggers', ''),
    ('edgeql', '''
CREATE FUNCTION
std::to_bytes(j: std::json) -> std::bytes {
    CREATE ANNOTATION std::description :=
        'Convert a json value to a binary UTF-8 string.';
    SET volatility := 'Immutable';
    USING (to_bytes(to_str(j)));
};
'''),
    ('metaschema-sql', 'ArrayIndexWithBoundsFunction'),
    ('metaschema-sql', 'ArraySliceFunction'),
    ('metaschema-sql', 'StringIndexWithBoundsFunction'),
    ('metaschema-sql', 'BytesIndexWithBoundsFunction'),
    ('metaschema-sql', 'StringSliceFunction'),
    ('metaschema-sql', 'BytesSliceFunction'),
    ('metaschema-sql', 'JSONIndexByTextFunction'),
    ('metaschema-sql', 'JSONIndexByIntFunction'),
    ('metaschema-sql', 'JSONSliceFunction'),
    ('edgeql', '''
CREATE MODULE std::lang;

CREATE MODULE std::lang::go;
CREATE ABSTRACT ANNOTATION std::lang::go::type;

CREATE MODULE std::lang::js;
CREATE ABSTRACT ANNOTATION std::lang::js::type;

CREATE MODULE std::lang::py;
CREATE ABSTRACT ANNOTATION std::lang::py::type;

CREATE MODULE std::lang::rs;
CREATE ABSTRACT ANNOTATION std::lang::rs::type;
'''),
    # 6.9
    ('edgeql', '''
CREATE FUNCTION
std::__pg_generate_series(
    `start`: std::int64,
    stop: std::int64
) -> SET OF std::int64
{
    SET volatility := 'Immutable';
    USING SQL FUNCTION 'generate_series';
};
'''),

    # !!!!!! 7.x !!!!!
    ('edgeql+user_ext+config|auth', '''
    create type ext::auth::OneTimeCode extending ext::auth::Auditable {
        create required property code_hash: std::bytes {
            create constraint exclusive;
            create annotation std::description :=
                "The securely hashed one-time code.";
        };
        create required property expires_at: std::datetime {
            create annotation std::description :=
                "The date and time when the code expires.";
        };
        create index on (.expires_at);

        create required link factor: ext::auth::Factor {
            on target delete delete source;
        };
    };

    create scalar type ext::auth::AuthenticationAttemptType extending std::enum<
        SignIn,
        EmailVerification,
        PasswordReset,
        MagicLink,
        OneTimeCode
    >;

    create type ext::auth::AuthenticationAttempt
    extending ext::auth::Auditable {
        create required link factor: ext::auth::Factor {
            on target delete delete source;
        };
        create required property attempt_type:
            ext::auth::AuthenticationAttemptType {
            create annotation std::description :=
                "The type of authentication attempt being made.";
        };
        create required property successful: std::bool {
            create annotation std::description :=
                "Whether this authentication attempt was successful.";
        };
    };

    create scalar type ext::auth::VerificationMethod
    extending std::enum<Link, Code>;

    alter type ext::auth::EmailPasswordProviderConfig {
        create required property verification_method:
            ext::auth::VerificationMethod {
            set default := ext::auth::VerificationMethod.Link;
        };
    };

    alter type ext::auth::WebAuthnProviderConfig {
        create required property verification_method:
            ext::auth::VerificationMethod {
            set default := ext::auth::VerificationMethod.Link;
        };
    };

    alter type ext::auth::MagicLinkProviderConfig {
        create required property verification_method:
            ext::auth::VerificationMethod {
            set default := ext::auth::VerificationMethod.Link;
        };
    };

    alter scalar type ext::auth::WebhookEvent extending std::enum<
        IdentityCreated,
        IdentityAuthenticated,
        EmailFactorCreated,
        EmailVerified,
        EmailVerificationRequested,
        PasswordResetRequested,
        MagicLinkRequested,
        OneTimeCodeRequested,
        OneTimeCodeVerified,
    >;

'''),
]
