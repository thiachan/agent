"""
Idempotent startup migration runner.

Handles schema changes that SQLAlchemy's create_all() cannot perform
automatically, such as adding values to an existing PostgreSQL enum or
creating tables that were added after the initial DB initialisation.

Runs automatically on every backend start — all statements use IF NOT EXISTS
or conditional logic, so it is always safe to re-run.
"""
import logging

from sqlalchemy import text
from app.core.database import engine, Base

# Import all models so Base.metadata is populated before create_all
from app.models import user, document, chat, knowledge_base, onboarding, bookmark  # noqa: F401

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Apply all pending schema migrations."""
    is_postgres = "postgresql" in str(engine.url)

    with engine.begin() as conn:
        # ── 1. Ensure all SQLAlchemy-mapped tables exist ──────────────────────
        # This is a no-op for tables that are already present.
        Base.metadata.create_all(bind=engine)
        logger.info("migrate: create_all complete")

        if is_postgres:
            # ── 2. Add 'leader' to the userrole enum (PostgreSQL only) ────────
            # ALTER TYPE ... ADD VALUE is idempotent via IF NOT EXISTS (PG 9.3+)
            conn.execute(text(
                "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'leader'"
            ))
            logger.info("migrate: userrole enum ensured to contain 'leader'")

            # ── 3. Add 'manager' to the userrole enum (safety) ────────────────
            conn.execute(text(
                "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'manager'"
            ))

            # ── 4. Ensure new onboarding tables exist ─────────────────────────
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS manager_playbooks (
                    id          SERIAL PRIMARY KEY,
                    manager_id  INTEGER NOT NULL UNIQUE
                                    REFERENCES users(id) ON DELETE CASCADE,
                    name        VARCHAR NOT NULL DEFAULT 'My Playbook',
                    data        TEXT NOT NULL,
                    created_at  TIMESTAMP DEFAULT now(),
                    updated_at  TIMESTAMP DEFAULT now()
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_manager_playbooks_manager_id "
                "ON manager_playbooks (manager_id)"
            ))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS playbook_assignments (
                    id            SERIAL PRIMARY KEY,
                    playbook_id   INTEGER NOT NULL
                                      REFERENCES manager_playbooks(id) ON DELETE CASCADE,
                    engineer_id   INTEGER NOT NULL UNIQUE
                                      REFERENCES users(id) ON DELETE CASCADE,
                    mentor_se_id  INTEGER
                                      REFERENCES users(id) ON DELETE SET NULL,
                    assigned_at   TIMESTAMP DEFAULT now()
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_playbook_assignments_playbook_id "
                "ON playbook_assignments (playbook_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_playbook_assignments_engineer_id "
                "ON playbook_assignments (engineer_id)"
            ))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS task_evidence (
                    id              SERIAL PRIMARY KEY,
                    assignment_id   INTEGER NOT NULL
                                        REFERENCES playbook_assignments(id) ON DELETE CASCADE,
                    task_id         VARCHAR NOT NULL,
                    evidence_type   VARCHAR NOT NULL,
                    content         TEXT,
                    file_name       VARCHAR,
                    file_path       VARCHAR,
                    created_by      INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    created_at      TIMESTAMP DEFAULT now()
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_task_evidence_assignment_id "
                "ON task_evidence (assignment_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_task_evidence_task_id "
                "ON task_evidence (task_id)"
            ))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS task_signoffs (
                    id              SERIAL PRIMARY KEY,
                    assignment_id   INTEGER NOT NULL
                                        REFERENCES playbook_assignments(id) ON DELETE CASCADE,
                    task_id         VARCHAR NOT NULL,
                    signed_by_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    notes           TEXT,
                    signed_at       TIMESTAMP DEFAULT now(),
                    UNIQUE (assignment_id, task_id)
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_task_signoffs_assignment_id "
                "ON task_signoffs (assignment_id)"
            ))

            logger.info("migrate: onboarding tables ensured")
