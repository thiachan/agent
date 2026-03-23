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

    # ── 1. Ensure all SQLAlchemy-mapped tables exist ──────────────────────────
    # This is a no-op for tables that are already present.
    Base.metadata.create_all(bind=engine)
    logger.info("migrate: create_all complete")

    if is_postgres:
        # ── 2. Add enum values (PostgreSQL only) ──────────────────────────────
        # CRITICAL: ALTER TYPE ... ADD VALUE cannot run inside a transaction
        # block in PostgreSQL.
        #
        # We use a raw DBAPI connection with autocommit=True so there is
        # absolutely no implicit BEGIN wrapping these statements.  The
        # engine-level execution_options approach can still open a
        # transaction internally in some SQLAlchemy versions, but obtaining
        # a raw_connection() and toggling autocommit at the DBAPI level is
        # always reliable.
        raw = engine.raw_connection()
        try:
            raw.set_isolation_level(0)  # psycopg2 ISOLATION_LEVEL_AUTOCOMMIT
            cur = raw.cursor()
            cur.execute(
                "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'leader'"
            )
            cur.execute(
                "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'manager'"
            )
            cur.close()
            logger.info("migrate: userrole enum ensured to contain 'leader' and 'manager'")
        except Exception as exc:
            logger.error(f"migrate: failed to alter userrole enum: {exc}", exc_info=True)
        finally:
            raw.close()

    if is_postgres:
        with engine.begin() as conn:
            # ── 3. Ensure new onboarding tables exist ─────────────────────────
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
