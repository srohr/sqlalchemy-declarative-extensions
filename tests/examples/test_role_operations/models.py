from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_declarative_extensions import Roles, declarative_database
from sqlalchemy_declarative_extensions.dialects.postgresql import Role

_Base = declarative_base()


@declarative_database
class Base(_Base):
    __abstract__ = True

    roles = Roles(ignore_unspecified=True).are(
        "read",
        Role("write", login=True),
    )