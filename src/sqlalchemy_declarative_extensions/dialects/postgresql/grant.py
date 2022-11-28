"""Abstract a postgresql GRANT statement.

See https://www.postgresql.org/docs/latest/sql-grant.html.

ALTER DEFAULT PRIVILEGES
    [ FOR { ROLE | USER } target_role [, ...] ]
    [ IN SCHEMA schema_name [, ...] ]
    abbreviated_grant_or_revoke

where abbreviated_grant_or_revoke is one of:

GRANT { { SELECT | INSERT | UPDATE | DELETE | TRUNCATE | REFERENCES | TRIGGER }
    [, ...] | ALL [ PRIVILEGES ] }
    ON TABLES
    TO { [ GROUP ] role_name | PUBLIC } [, ...] [ WITH GRANT OPTION ]

GRANT { { USAGE | SELECT | UPDATE }
    [, ...] | ALL [ PRIVILEGES ] }
    ON SEQUENCES
    TO { [ GROUP ] role_name | PUBLIC } [, ...] [ WITH GRANT OPTION ]

GRANT { EXECUTE | ALL [ PRIVILEGES ] }
    ON FUNCTIONS
    TO { [ GROUP ] role_name | PUBLIC } [, ...] [ WITH GRANT OPTION ]

GRANT { USAGE | ALL [ PRIVILEGES ] }
    ON TYPES
    TO { [ GROUP ] role_name | PUBLIC } [, ...] [ WITH GRANT OPTION ]
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Generic, Optional, Protocol, runtime_checkable, Tuple, Union

from sqlalchemy.sql.elements import TextClause
from sqlalchemy.sql.expression import text

from sqlalchemy_declarative_extensions.dialects.postgresql.grant_type import (
    DefaultGrantTypes,
    G,
    GrantOptions,
    GrantTypes,
)


@runtime_checkable
class HasName(Protocol):
    name: str


@dataclass(frozen=True)
class Grant(Generic[G]):
    grants: Tuple[Union[str, G], ...]
    target_role: str
    grant_option: bool = False
    revoke_: bool = False

    @classmethod
    def new(
        cls,
        grant: Union[str, G],
        *grants: Union[str, G],
        to: Union[str, HasName],
        grant_option=False,
    ) -> Grant:
        return cls(
            grants=tuple(sorted([grant, *grants])),
            target_role=_coerce_name(to),
            grant_option=grant_option,
        )

    def revoke(self) -> Grant:
        return replace(self, revoke_=True)

    def with_grant_option(self):
        return replace(self, grant_option=True)

    def on_objects(self, *objects: Union[str, HasName], object_type: GrantTypes):
        variants = object_type.to_variants()
        grant = replace(self, grants=tuple(_map_grant_names(variants, *self.grants)))

        names = [_coerce_name(obj) for obj in objects]
        return GrantStatement(grant, grant_type=object_type, targets=tuple(names))

    def on_tables(self, *tables: Union[str, HasName]):
        return self.on_objects(*tables, object_type=GrantTypes.table)

    def on_schemas(self, *schemas: Union[str, HasName]):
        return self.on_objects(*schemas, object_type=GrantTypes.schema)


@dataclass(frozen=True)
class DefaultGrant:
    grant_type: DefaultGrantTypes
    in_schemas: Tuple[str, ...]
    target_role: Optional[str] = None

    @classmethod
    def on_tables_in_schema(
        cls, *in_schemas: Union[str, HasName], for_role: Optional[HasName] = None
    ) -> DefaultGrant:
        schemas = _map_schema_names(*in_schemas)
        return cls(
            grant_type=DefaultGrantTypes.table,
            in_schemas=tuple(schemas),
            target_role=_coerce_name(for_role) if for_role is not None else None,
        )

    @classmethod
    def on_sequences_in_schema(
        cls, *in_schemas: Union[str, HasName], for_role: Optional[HasName] = None
    ) -> DefaultGrant:
        schemas = _map_schema_names(*in_schemas)
        return cls(
            grant_type=DefaultGrantTypes.sequence,
            in_schemas=tuple(schemas),
            target_role=_coerce_name(for_role) if for_role is not None else None,
        )

    @classmethod
    def on_types_in_schema(
        cls, *in_schemas: Union[str, HasName], for_role: Optional[HasName] = None
    ) -> DefaultGrant:
        schemas = _map_schema_names(*in_schemas)
        return cls(
            grant_type=DefaultGrantTypes.type,
            in_schemas=tuple(schemas),
            target_role=_coerce_name(for_role) if for_role is not None else None,
        )

    @classmethod
    def on_functions_in_schema(
        cls, *in_schemas: Union[str, HasName], for_role: Optional[HasName] = None
    ) -> DefaultGrant:
        schemas = _map_schema_names(*in_schemas)
        return cls(
            grant_type=DefaultGrantTypes.function,
            in_schemas=tuple(schemas),
            target_role=_coerce_name(for_role) if for_role is not None else None,
        )

    def for_role(self, role: str):
        return replace(self, target_role=role)

    def grant(
        self,
        grant: Union[str, G, Grant],
        *grants: Union[str, G],
        to,
        grant_option=False,
    ):
        if not isinstance(grant, Grant):
            grant = Grant(
                grants=tuple(
                    _map_grant_names(self.grant_type.to_variants(), grant, *grants)
                ),
                target_role=to,
                grant_option=grant_option,
            )
        return DefaultGrantStatement(self, grant)


@dataclass(frozen=True)
class DefaultGrantStatement(Generic[G]):
    default_grant: DefaultGrant
    grant: Grant[G]

    def for_role(self, role: Union[str, HasName]) -> DefaultGrantStatement:
        return replace(
            self, default_grant=replace(self.default_grant, target_role=role)
        )

    def invert(self) -> DefaultGrantStatement:
        return replace(self, grant=replace(self.grant, revoke_=not self.grant.revoke_))

    def to_sql(self) -> TextClause:
        result = []

        result.append("ALTER DEFAULT PRIVILEGES")

        if self.default_grant.target_role:
            result.append(f'FOR ROLE "{self.default_grant.target_role}"')

        schemas_str = ", ".join([f'"{t}"' for t in self.default_grant.in_schemas])
        result.append(f"IN SCHEMA {schemas_str}")

        result.append(_render_grant_or_revoke(self.grant))
        result.append(_render_privilege(self.grant, self.default_grant.grant_type))

        result.append(f"ON {self.default_grant.grant_type.value}S")
        result.append(_render_to_or_from(self.grant))

        text_result = " ".join(result)
        return text(text_result + ";")


@dataclass(frozen=True)
class GrantStatement(Generic[G]):
    grant: Grant[G]
    grant_type: GrantTypes
    targets: Tuple[str, ...]

    def invert(self) -> GrantStatement:
        return replace(self, grant=replace(self.grant, revoke_=not self.grant.revoke_))

    def for_role(self, role: Union[str, HasName]) -> GrantStatement:
        return replace(self, grant=replace(self.grant, target_role=_coerce_name(role)))

    def to_sql(self) -> TextClause:
        result = []

        result.append(_render_grant_or_revoke(self.grant))
        result.append(_render_privilege(self.grant, self.grant_type))
        result.append(f"ON {self.grant_type.value}")

        result.append(", ".join([f'"{t}"' for t in self.targets]))
        result.append(_render_to_or_from(self.grant))

        grant_option = _render_grant_option(self.grant)
        if grant_option:
            result.append(grant_option)

        text_result = " ".join(result)
        return text(text_result + ";")

    def explode(self):
        return [
            GrantStatement(
                grant=Grant(
                    grants=(grant,),
                    target_role=self.grant.target_role,
                    grant_option=self.grant.grant_option,
                    revoke_=self.grant.revoke_,
                ),
                grant_type=self.grant_type,
                targets=(target,),
            )
            for target in self.targets
            for grant in self.grant.grants
        ]


def _render_grant_or_revoke(grant: Grant) -> str:
    if grant.revoke_:
        return "REVOKE"
    return "GRANT"


def _render_to_or_from(grant: Grant) -> str:
    if grant.revoke_:
        return f'FROM "{grant.target_role}"'
    return f'TO "{grant.target_role}"'


def _render_privilege(
    grant: Grant, grant_type: Union[DefaultGrantTypes, GrantTypes]
) -> str:
    grant_variant_cls = grant_type.to_variants()
    return ", ".join(v.value for v in grant_variant_cls.from_strings(grant.grants))


def _render_grant_option(grant: Grant) -> Optional[str]:
    if grant.grant_option:
        return "WITH GRANT OPTION"
    return None


def _map_schema_names(*schemas: Union[str, HasName]):
    return sorted([_coerce_name(s) for s in schemas])


def _map_grant_names(variant: G, *grants: Union[str, G]):
    return sorted(
        [g if isinstance(g, GrantOptions) else variant.from_string(g) for g in grants]
    )


def _coerce_name(name: Union[str, HasName]):
    if isinstance(name, HasName):
        return name.name
    return name