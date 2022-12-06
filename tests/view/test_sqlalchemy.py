from pytest_mock_resources import (
    create_mysql_fixture,
    create_postgres_fixture,
    create_sqlite_fixture,
)
from sqlalchemy import Column, Index, select, types
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_declarative_extensions import (
    Row,
    Rows,
    Schemas,
    declarative_database,
    register_sqlalchemy_events,
    view,
)

Base_ = declarative_base()


@declarative_database
class Base(Base_):
    __abstract__ = True

    schemas = Schemas().are("fooschema")
    rows = Rows().are(
        Row("fooschema.foo", id=1),
        Row("fooschema.foo", id=2),
        Row("fooschema.foo", id=12),
        Row("fooschema.foo", id=13),
    )


class Foo(Base):
    __tablename__ = "foo"
    __table_args__ = {"schema": "fooschema"}

    id = Column(types.Integer(), primary_key=True)


foo_table = Foo.__table__


@view()
class Bar(Base):
    __tablename__ = "bar"
    __table_args__ = (
        Index("id_ix", "id"),
        {"schema": "fooschema"},
    )
    __view__ = select(foo_table.c.id).where(foo_table.c.id > 10)

    id = Column(types.Integer(), primary_key=True)


@view(Base)
class Baz:
    __tablename__ = "baz"
    __table_args__ = {"schema": "fooschema"}
    __view__ = select(foo_table.c.id).where(foo_table.c.id < 10)


register_sqlalchemy_events(Base.metadata, schemas=True, views=True, rows=True)

pg = create_postgres_fixture(
    scope="function", engine_kwargs={"echo": True}, session=True
)
sqlite = create_sqlite_fixture(scope="function", session=True)
mysql = create_mysql_fixture(scope="function", session=True)


def test_create_view_postgresql(pg):
    run_test(pg)


def test_create_view_mysql(mysql):
    run_test(mysql)


def run_test(session):
    Base.metadata.create_all(bind=session.connection())
    session.commit()

    result = [f.id for f in session.query(Foo).all()]
    assert result == [1, 2, 12, 13]

    result = [f.id for f in session.query(Bar).all()]
    assert result == [12, 13]

    result = [f.id for f in session.execute(Baz.__view__).all()]
    assert result == [1, 2]