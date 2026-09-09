"""
Alembic migration to add embedding and embedding_model columns to document_chunks table.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("document_chunks", sa.Column("embedding", sa.JSON(), nullable=True))
    op.add_column("document_chunks", sa.Column("embedding_model", sa.String(), nullable=True))


def downgrade():
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "embedding")
