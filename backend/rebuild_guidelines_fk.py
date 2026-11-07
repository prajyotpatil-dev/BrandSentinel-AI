"""
Rebuild guidelines table with proper foreign key constraints.

This migration:
1. Creates new guidelines table with foreign keys
2. Copies all existing data
3. Replaces old table with new one
4. Preserves all records
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path


def rebuild_guidelines_table():
    """Rebuild guidelines table with foreign key constraints."""
    db_path = Path("brandsentinel.sqlite")

    if not db_path.exists():
        print("[ERROR] Database does not exist")
        return False

    # Backup database
    backup_path = f"brandsentinel.sqlite.fk_rebuild_backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Database backed up to: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Enable foreign key enforcement
        cursor.execute("PRAGMA foreign_keys = ON")
        print("[OK] Foreign key enforcement enabled")

        # Get current guidelines count
        cursor.execute("SELECT COUNT(*) FROM guidelines")
        original_count = cursor.fetchone()[0]
        print(f"[INFO] Current guidelines count: {original_count}")

        # Create new guidelines table with foreign keys
        cursor.execute("""
            CREATE TABLE guidelines_new (
                id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                rule_text TEXT NOT NULL,
                source_document VARCHAR NOT NULL,
                version VARCHAR DEFAULT '1.0',
                tags JSON DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                document_id TEXT,
                chunk_id TEXT,
                extraction_method TEXT DEFAULT 'manual',
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL,
                FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE SET NULL
            )
        """)
        print("[OK] Created new guidelines table with foreign keys")

        # Copy all data from old table to new
        cursor.execute("""
            INSERT INTO guidelines_new
            (id, title, category, rule_text, source_document, version, tags,
             created_at, updated_at, document_id, chunk_id, extraction_method)
            SELECT id, title, category, rule_text, source_document, version, tags,
                   created_at, updated_at, document_id, chunk_id, extraction_method
            FROM guidelines
        """)

        # Verify all records copied
        cursor.execute("SELECT COUNT(*) FROM guidelines_new")
        new_count = cursor.fetchone()[0]
        print(f"[INFO] Records copied to new table: {new_count}")

        if new_count != original_count:
            raise Exception(f"Record count mismatch: {original_count} -> {new_count}")

        # Drop old table
        cursor.execute("DROP TABLE guidelines")
        print("[OK] Dropped old guidelines table")

        # Rename new table
        cursor.execute("ALTER TABLE guidelines_new RENAME TO guidelines")
        print("[OK] Renamed new table to guidelines")

        # Commit changes
        conn.commit()
        print("[OK] All changes committed successfully")

        # Validate migration
        print("\n=== Validation ===")

        # Verify foreign keys
        cursor.execute("PRAGMA foreign_key_list(guidelines)")
        fks = cursor.fetchall()
        print(f"[INFO] Foreign keys on guidelines table: {len(fks)}")
        for fk in fks:
            print(f"  {fk[3]} -> {fk[2]}({fk[4]}) [ON DELETE {fk[6]}]")

        if len(fks) == 2:
            print("[OK] Both foreign keys created successfully")
        else:
            print(f"[WARN] Expected 2 foreign keys, found {len(fks)}")

        # Verify record count
        cursor.execute("SELECT COUNT(*) FROM guidelines")
        final_count = cursor.fetchone()[0]
        print(f"[OK] Final guidelines count: {final_count}")

        if final_count == original_count:
            print("[OK] All records preserved")
        else:
            raise Exception(f"Records lost: {original_count} -> {final_count}")

        print("\n=== Rebuild Complete ===")
        print(f"[OK] Guidelines table rebuilt with foreign key constraints")
        print(f"[OK] Backup available at: {backup_path}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Rebuild failed: {e}")
        print(f"[INFO] Database can be restored from backup: {backup_path}")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = rebuild_guidelines_table()
    exit(0 if success else 1)
