from pytest_alembic import MigrationContext
from sqlalchemy import text


def test_apply_autogenerated_revision(alembic_runner: MigrationContext, alembic_engine):
    result = alembic_runner.generate_revision(
        autogenerate=True, prevent_file_generation=False
    )
    alembic_runner.migrate_up_one()

    result = alembic_engine.execute(
        text("select nspname from pg_namespace where nspname not like 'pg_%'")
    ).all()
    assert result == [("public",), ("information_schema",)]