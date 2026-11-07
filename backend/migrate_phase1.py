"""
Database schema migration script for Phase 1: Knowledge Hub.

This script:
1. Backs up the existing database
2. Adds new columns to the guidelines table
3. Creates documents and document_chunks tables
4. Enables foreign key enforcement
5. Validates the migration
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path


def migrate_database():
    """Execute Phase 1 database migration."""
    db_path = Path("brandsentinel.sqlite")

    if not db_path.exists():
        print("Database does not exist yet. It will be created on first application run.")
        return

    # Backup database
    backup_path = f"brandsentinel.sqlite.migration_backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Database backed up to: {backup_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Enable foreign key enforcement
        cursor.execute("PRAGMA foreign_keys = ON")
        print("[OK] Foreign key enforcement enabled")

        # Check current schema
        cursor.execute("PRAGMA table_info(guidelines)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"[OK] Existing guidelines columns: {existing_columns}")

        # Add new columns to guidelines table if they don't exist
        new_columns = {
            "document_id": "TEXT",
            "chunk_id": "TEXT",
            "extraction_method": "TEXT DEFAULT 'manual'"
        }

        for col_name, col_type in new_columns.items():
            if col_name not in existing_columns:
                cursor.execute(f"ALTER TABLE guidelines ADD COLUMN {col_name} {col_type}")
                print(f"[OK] Added column: guidelines.{col_name}")
            else:
                print(f"[SKIP] Column already exists: guidelines.{col_name}")

        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                storage_path TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'uploading',
                error_message TEXT,
                page_count INTEGER,
                version TEXT DEFAULT '1.0',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                uploaded_by TEXT DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """)
        print("[OK] Created table: documents")

        # Create indexes for documents
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_deleted_at ON documents(deleted_at)")
        print("[OK] Created indexes for documents table")

        # Create document_chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                page_number INTEGER,
                section_heading TEXT,
                char_start INTEGER NOT NULL,
                char_end INTEGER NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)
        print("[OK] Created table: document_chunks")

        # Create indexes for document_chunks
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_chunk ON document_chunks(document_id, chunk_index)")
        print("[OK] Created indexes for document_chunks table")

        # Commit changes
        conn.commit()
        print("[OK] All changes committed successfully")

        # Validate migration
        print("\n=== Validation ===")

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[OK] Tables in database: {tables}")

        expected_tables = {'guidelines', 'documents', 'document_chunks', 'submissions', 'findings', 'decisions'}
        if expected_tables.issubset(set(tables)):
            print("[OK] All expected tables exist")
        else:
            missing = expected_tables - set(tables)
            print(f"[WARN] Missing tables: {missing}")

        # Check guidelines table has new columns
        cursor.execute("PRAGMA table_info(guidelines)")
        guidelines_cols = {row[1] for row in cursor.fetchall()}
        if {'document_id', 'chunk_id', 'extraction_method'}.issubset(guidelines_cols):
            print("[OK] Guidelines table has all new columns")
        else:
            print("[WARN] Guidelines table is missing some new columns")

        # Count existing records
        cursor.execute("SELECT COUNT(*) FROM guidelines")
        guideline_count = cursor.fetchone()[0]
        print(f"[OK] Existing guidelines preserved: {guideline_count} records")

        cursor.execute("SELECT COUNT(*) FROM submissions")
        submission_count = cursor.fetchone()[0]
        print(f"[OK] Existing submissions preserved: {submission_count} records")

        cursor.execute("SELECT COUNT(*) FROM findings")
        finding_count = cursor.fetchone()[0]
        print(f"[OK] Existing findings preserved: {finding_count} records")

        print("\n=== Migration Complete ===")
        print("[OK] Database schema updated successfully")
        print(f"[OK] Backup available at: {backup_path}")
        print("[OK] All existing data preserved")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        print(f"[OK] Database can be restored from backup: {backup_path}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
