"""Persistent state for timed, replayable showcase runs."""
from alembic import op
from app.models.demo_run import DemoRun

revision = "0002_live_demo"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    # The original initial revision creates the entire ORM metadata on fresh installs.
    DemoRun.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    DemoRun.__table__.drop(op.get_bind(), checkfirst=True)
