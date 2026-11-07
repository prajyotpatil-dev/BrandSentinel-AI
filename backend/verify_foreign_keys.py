"""Verify foreign key constraints in SQLite database."""
import sqlite3

conn = sqlite3.connect('brandsentinel.sqlite')
cursor = conn.cursor()

print("=== Foreign Key Enforcement Status ===")
cursor.execute("PRAGMA foreign_keys")
result = cursor.fetchone()
print(f"Foreign keys: {'ENABLED' if result[0] == 1 else 'DISABLED'}")
print()

print("=== Foreign Key Constraints by Table ===")

# Check document_chunks foreign keys
print("\n1. document_chunks table:")
cursor.execute("PRAGMA foreign_key_list(document_chunks)")
fks = cursor.fetchall()
if fks:
    for fk in fks:
        print(f"   {fk[3]} -> {fk[2]}({fk[4]}) [ON DELETE {fk[6]}]")
else:
    print("   [WARN] No foreign keys found")

# Check guidelines foreign keys
print("\n2. guidelines table:")
cursor.execute("PRAGMA foreign_key_list(guidelines)")
fks = cursor.fetchall()
if fks:
    for fk in fks:
        print(f"   {fk[3]} -> {fk[2]}({fk[4]}) [ON DELETE {fk[6]}]")
else:
    print("   [WARN] No foreign keys found")

# Check other tables for reference
print("\n3. findings table:")
cursor.execute("PRAGMA foreign_key_list(findings)")
fks = cursor.fetchall()
if fks:
    for fk in fks:
        print(f"   {fk[3]} -> {fk[2]}({fk[4]})")

print("\n4. decisions table:")
cursor.execute("PRAGMA foreign_key_list(decisions)")
fks = cursor.fetchall()
if fks:
    for fk in fks:
        print(f"   {fk[3]} -> {fk[2]}({fk[4]})")

print("\n=== Expected Foreign Keys ===")
print("Expected:")
print("  document_chunks.document_id -> documents.id [ON DELETE CASCADE]")
print("  guidelines.document_id -> documents.id [ON DELETE SET NULL]")
print("  guidelines.chunk_id -> document_chunks.id [ON DELETE SET NULL]")

conn.close()
print("\n[INFO] Verification complete")
