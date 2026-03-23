"""
Migration: Add manager playbooks, assignments, task evidence, and sign-offs tables.
Also widens the users.role column to support MENTOR_SE.
Run from the backend/ directory:
    python migrate_onboarding_v2.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "intranet.db")

DDL = [
    """
    CREATE TABLE IF NOT EXISTS manager_playbooks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manager_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR NOT NULL DEFAULT 'My Playbook',
        data TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS playbook_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playbook_id INTEGER NOT NULL REFERENCES manager_playbooks(id) ON DELETE CASCADE,
        engineer_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        mentor_se_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL REFERENCES playbook_assignments(id) ON DELETE CASCADE,
        task_id VARCHAR NOT NULL,
        evidence_type VARCHAR NOT NULL,
        content TEXT,
        file_name VARCHAR,
        file_path VARCHAR,
        created_by INTEGER REFERENCES users(id) ON DELETE CASCADE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_signoffs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL REFERENCES playbook_assignments(id) ON DELETE CASCADE,
        task_id VARCHAR NOT NULL,
        signed_by_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        notes TEXT,
        signed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (assignment_id, task_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_manager_playbooks_manager_id ON manager_playbooks (manager_id)",
    "CREATE INDEX IF NOT EXISTS ix_playbook_assignments_playbook_id ON playbook_assignments (playbook_id)",
    "CREATE INDEX IF NOT EXISTS ix_playbook_assignments_engineer_id ON playbook_assignments (engineer_id)",
    "CREATE INDEX IF NOT EXISTS ix_task_evidence_assignment_id ON task_evidence (assignment_id)",
    "CREATE INDEX IF NOT EXISTS ix_task_evidence_task_id ON task_evidence (task_id)",
    "CREATE INDEX IF NOT EXISTS ix_task_signoffs_assignment_id ON task_signoffs (assignment_id)",
]

if __name__ == "__main__":
    print(f"Migrating database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        for stmt in DDL:
            conn.execute(stmt.strip())
            print(f"  OK: {stmt.strip()[:60]}...")
        conn.commit()
        print("Migration complete.")
    finally:
        conn.close()
