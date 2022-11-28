import pytest
import sqlalchemy.exc
from pytest_alembic import MigrationContext, tests
from sqlalchemy.sql.expression import text

from sqlalchemy_declarative_extensions.dialects import get_roles


def test_apply_autogenerated_revision(alembic_runner: MigrationContext, alembic_engine):
    result = alembic_runner.generate_revision(
        autogenerate=True, prevent_file_generation=False
    )
    alembic_runner.migrate_up_one()

    # Verify this no longer sees changes to make! Failing here would imply the autogenerate
    # is not fully normalizing the difference.
    tests.test_model_definitions_match_ddl(alembic_runner)

    result = [r.name for r in get_roles(alembic_engine, exclude=["user"])]

    expected_result = [
        "o1_app",
        "o2_read",
        "o2_write",
    ]
    assert expected_result == result

    # only "o2_write" can write
    with pytest.raises(sqlalchemy.exc.ProgrammingError):
        alembic_engine.execute(
            text("SET ROLE o2_read; INSERT INTO foo VALUES (DEFAULT)")
        )

    alembic_engine.execute(text("SET ROLE o2_write; INSERT INTO foo VALUES (DEFAULT)"))

    # only "o2_read" can read
    with pytest.raises(sqlalchemy.exc.ProgrammingError):
        alembic_engine.execute(text("SET ROLE o2_write; SELECT * FROM created_at"))

    alembic_engine.execute(text("SET ROLE o2_read; SELECT * FROM foo"))

    # "o1_app" can do both
    alembic_engine.execute(text("SET ROLE o1_app; INSERT INTO foo VALUES (DEFAULT)"))
    alembic_engine.execute(text("SET ROLE o1_app; SELECT * FROM foo"))
