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


"""Patches to apply to databases"""

from __future__ import annotations


def get_patch_level(num_patches: int) -> int:
    return sum(p.startswith('edgeql+schema') for p, _ in PATCHES[:num_patches])


def get_version_key(num_patches: int) -> str:
    """Produce a version key to add to instdata keys after major patches.

    Patches that modify the schema class layout and introspection queries
    are not safe to downgrade from. So for such patches, we add a version
    suffix to the names of the core instdata entries that we would need to
    update, so that we don't clobber the old version.

    After a downgrade, we'll have more patches applied than we
    actually know exist in the running version, but since we compute
    the key based on the number of schema layout patches that we can
    *see*, we still compute the right key.
    """
    level = get_patch_level(num_patches)
    if level == 0:
        return ''
    else:
        return f'_v{level}'


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
    # 7.0b2 or 7.0rc1
    ('ext-pkg', 'auth'),  # For #8953, #8964
    ('edgeql+user_ext|auth', '''
    create permission ext::auth::perm::auth_read_user;

    alter function ext::auth::_jwt_check_signature(
        jwt: tuple<header: std::str, payload: std::str, signature: std::str>,
        key: std::str,
        algo: ext::auth::JWTAlgo = ext::auth::JWTAlgo.HS256,
    )
    {
        SET required_permissions := {};
    };

    alter function ext::auth::_jwt_parse(
        token: std::str,
    )
    {
        set volatility := 'Stable';
        using (
            for parts in std::str_split(token, ".")
            select
                (
                    header := parts[0],
                    payload := parts[1],
                    signature := parts[2],
                )
            order by
                assert(len(parts) = 3, message := "JWT is malformed")
        );
        SET required_permissions := {};
    };

    alter function ext::auth::_jwt_verify(
        token: std::str,
        key: std::str,
        algo: ext::auth::JWTAlgo = ext::auth::JWTAlgo.HS256,
    )
    {
        SET required_permissions := {};
    };

    create single global ext::auth::_client_token_id := (
        for conf_key in (
            (
                select cfg::Config.extensions[is ext::auth::AuthConfig]
                limit 1
            ).auth_signing_key
        )
        for jwt_claims in (
            ext::auth::_jwt_verify(
                global ext::auth::client_token,
                conf_key,
            )
        )
        select <uuid>json_get(jwt_claims, "sub")
    );
    alter type ext::auth::Identity {
        create access policy read_current allow select using (
            not global ext::auth::perm::auth_read
            and global ext::auth::perm::auth_read_user
            and .id ?= global ext::auth::_client_token_id
        );
    };

'''),
    # Because of bad interactions between the patch system and how
    # aliases work (aaaaaaaaa), I had to split this up.
    # The bug is I think on the patch system side, due to how
    # compile_schema_storage_in_delta is alienated from the schema changes.
    ('edgeql+user_ext|auth', '''
    alter global ext::auth::ClientTokenIdentity using (
        select
            ext::auth::Identity
        filter
            .id = global ext::auth::_client_token_id
    );

'''),
    ('sql-introspection', ''),  # For #8962
    ('edgeql+schema+config', ''),  # For #8971

    # 7.0rc2
    ('ext-pkg', 'auth'),  # For #9007
    ('edgeql+user_ext+config|auth', '''
    ALTER TYPE ext::auth::MagicLinkProviderConfig {
        CREATE REQUIRED PROPERTY auto_signup: std::bool {
            SET default := false;
        };
    };
'''),
    # 7.0rc3

    # For #9028.
    # N.B: We don't need to do any actual in place patching, since it
    # just adjusts the compat version numbers. If it is installed,
    # then we're already fine.
    ('ext-pkg', 'pgvector'),
    # For #9041, unfortunately -- this may actually drop and recreate
    # ai indexes in the database.
    # ('repair', ''),  # applied later for rc3

    # For #9040
    ('ext-pkg', 'ai'),
    ('edgeql+user_ext+config|ai', '''
    create abstract inheritable annotation
        ext::ai::embedding_model_max_batch_size;

    alter type ext::ai::EmbeddingModel {
        create annotation
            ext::ai::embedding_model_max_batch_size := "<optional>";
    };
    '''),
    ('repair+user_ext|ai', ''),

    # For #9053
    ('edgeql+schema', '''
    ALTER TYPE sys::Role {
        DROP ACCESS POLICY ap_read;
        CREATE ACCESS POLICY ap_read DENY SELECT USING (
            NOT global sys::perm::superuser
        );
    };
    '''),
    # For #9054
    ('edgeql+schema', '''
    CREATE REQUIRED GLOBAL sys::current_permissions -> array<str> {
        SET default := <array<str>>[];
    };
    '''),
    # For #8982
    ('edgeql+schema', '''
    CREATE FUNCTION
    std::math::exp(x: std::int64) -> std::float64
    {
        CREATE ANNOTATION std::description :=
            'Return the exponential of the input value.';
        SET volatility := 'Immutable';
        USING SQL FUNCTION 'exp';
    };

    CREATE FUNCTION
    std::math::exp(x: std::float64) -> std::float64
    {
        CREATE ANNOTATION std::description :=
            'Return the exponential of the input value.';
        SET volatility := 'Immutable';
        USING SQL FUNCTION 'exp';
    };

    CREATE FUNCTION
    std::math::exp(x: std::decimal) -> std::decimal
    {
        CREATE ANNOTATION std::description :=
            'Return the exponential of the input value.';
        SET volatility := 'Immutable';
        USING SQL FUNCTION 'exp';
    };
    '''),
    # 7.0rc4 or 7.0-final
    ('repair+user_ext|ai', ''),  # For #9073
    ('edgeql+schema', ''),  # For #9074

    # For #9111
    ('edgeql+user_ext|auth', '''
  alter type ext::auth::DiscordOAuthProvider {
    create required property prompt: std::str {
      create annotation std::description :=
        "Controls how the authorization flow handles existing authorizations. \
        If a user has previously authorized your application with the \
        requested scopes and prompt is set to consent, it will request them \
        to reapprove their authorization. If set to none, it will skip the \
        authorization screen and redirect them back to your redirect URI \
        without requesting their authorization. For passthrough scopes, like \
        bot and webhook.incoming, authorization is always required.";
      set default := 'consent';
    };
  };
    '''),

    # For #9104
    ('edgeql+schema+config', '''
    ALTER TYPE cfg::AbstractConfig {
        CREATE PROPERTY query_cache_size -> std::int32 {
            SET default := 1000;
            CREATE ANNOTATION cfg::system := 'true';
            CREATE ANNOTATION cfg::requires_restart := 'true';
            CREATE ANNOTATION std::description :=
                'Maximum number of queries to cache in the query cache';
        };
    };
    '''),
]
