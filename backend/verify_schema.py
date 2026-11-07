"""Verify Phase 1 database schema changes."""
import sqlite3

conn = sqlite3.connect('brandsentinel.sqlite')
cursor = conn.cursor()

print("=== Guidelines Table Schema ===")
cursor.execute("PRAGMA table_info(guidelines)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n=== Documents Table Schema ===")
cursor.execute("PRAGMA table_info(documents)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n=== Document Chunks Table Schema ===")
cursor.execute("PRAGMA table_info(document_chunks)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n=== Foreign Key Constraints ===")
cursor.execute("PRAGMA foreign_key_list(guidelines)")
print("Guidelines table foreign keys:")
for row in cursor.fetchall():
    print(f"  {row[3]} -> {row[2]}({row[4]})")

cursor.execute("PRAGMA foreign_key_list(document_chunks)")
print("\nDocument chunks table foreign keys:")
for row in cursor.fetchall():
    print(f"  {row[3]} -> {row[2]}({row[4]})")

print("\n=== Indexes ===")
cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND tbl_name IN ('documents', 'document_chunks')")
print("Indexes on new tables:")
for row in cursor.fetchall():
    print(f"  {row[0]} on {row[1]}")

conn.close()
print("\n[OK] Schema verification complete")
