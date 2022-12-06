"""empty message

Revision ID: 2152079ac9a3
Revises: 
Create Date: 2022-12-04 15:37:26.523838

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2152079ac9a3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "foo",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.insert_table_row("foo", {"id": 3})
    op.insert_table_row("foo", {"id": 10})
    op.insert_table_row("foo", {"id": 11})
    op.insert_table_row("foo", {"id": 12})
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.delete_table_row("foo", {"id": 12})
    op.delete_table_row("foo", {"id": 11})
    op.delete_table_row("foo", {"id": 10})
    op.delete_table_row("foo", {"id": 3})
    op.drop_table("foo")
    # ### end Alembic commands ###