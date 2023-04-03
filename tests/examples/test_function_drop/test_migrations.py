import pytest
import sqlalchemy.exc
from pytest_alembic import MigrationContext
from pytest_mock_resources import PostgresConfig, create_postgres_fixture
from sqlalchemy import text

alembic_engine = create_postgres_fixture(scope="function", engine_kwargs={"echo": True})


@pytest.fixture(scope="session")
def pmr_postgres_config():
    return PostgresConfig(port=None, ci_port=None)


def test_apply_autogenerated_revision(alembic_runner: MigrationContext, alembic_engine):
    with alembic_engine.connect() as conn:
        conn.execute(
            text(
                "CREATE FUNCTION gimme() RETURNS INTEGER language sql as $$ select 1 $$;"
            )
        )

    alembic_runner.migrate_up_one()
    alembic_runner.generate_revision(autogenerate=True, prevent_file_generation=False)
    alembic_runner.migrate_up_one()

    with pytest.raises(sqlalchemy.exc.ProgrammingError) as e:
        with alembic_engine.connect() as conn:
            conn.execute(text("SELECT gimme()")).scalar()
    assert "function gimme() does not exist" in str(e.value)
