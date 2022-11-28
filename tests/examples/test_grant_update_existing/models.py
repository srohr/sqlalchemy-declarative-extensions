from sqlalchemy import Column, types
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_declarative_extensions import (
    declarative_database,
    Grants,
    PGRole,
    Roles,
)
from sqlalchemy_declarative_extensions.dialects.postgresql import DefaultGrant

_Base = declarative_base()


@declarative_database
class Base(_Base):
    __abstract__ = True

    roles = Roles(ignore_unspecified=True).are(
        "o2_read",
        "o2_write",
        PGRole("o1_app", login=False, in_roles=["o2_read", "o2_write"]),
    )
    grants = Grants().are(
        DefaultGrant.on_tables_in_schema("public").grant(
            "select", "insert", "update", "delete", to="o2_read"
        ),
        DefaultGrant.on_sequences_in_schema("public").grant("usage", to="o2_read"),
    )


class Foo(Base):
    __tablename__ = "foo"

    id = Column(types.Integer(), primary_key=True)