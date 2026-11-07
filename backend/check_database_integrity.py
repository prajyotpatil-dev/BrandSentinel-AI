"""Run SQLite integrity checks on the database."""
import sqlite3

conn = sqlite3.connect('brandsentinel.sqlite')
cursor = conn.cursor()

print("=== SQLite Integrity Checks ===\n")

# Enable foreign key enforcement for the check
cursor.execute("PRAGMA foreign_keys = ON")
print("[INFO] Foreign key enforcement: ENABLED for checks\n")

# Run integrity check
print("1. PRAGMA integrity_check:")
cursor.execute("PRAGMA integrity_check")
results = cursor.fetchall()
for row in results:
    status = row[0]
    if status == "ok":
        print(f"   [OK] {status}")
    else:
        print(f"   [ERROR] {status}")

# Run foreign key check
print("\n2. PRAGMA foreign_key_check:")
cursor.execute("PRAGMA foreign_key_check")
violations = cursor.fetchall()
if not violations:
    print("   [OK] No foreign key violations found")
else:
    print(f"   [ERROR] Found {len(violations)} foreign key violations:")
    for v in violations:
        print(f"     Table: {v[0]}, Row: {v[1]}, Parent: {v[2]}, FK Index: {v[3]}")

# Check specific tables for referential integrity
print("\n3. Manual Referential Integrity Checks:")

# Check document_chunks.document_id references
print("   a. document_chunks -> documents:")
cursor.execute("""
    SELECT COUNT(*) FROM document_chunks
    WHERE document_id NOT IN (SELECT id FROM documents)
""")
orphaned_chunks = cursor.fetchone()[0]
if orphaned_chunks == 0:
    print("      [OK] All chunks have valid document_id references")
else:
    print(f"      [ERROR] {orphaned_chunks} chunks reference non-existent documents")

# Check guidelines.document_id references (nullable)
print("   b. guidelines -> documents:")
cursor.execute("""
    SELECT COUNT(*) FROM guidelines
    WHERE document_id IS NOT NULL
    AND document_id NOT IN (SELECT id FROM documents)
""")
orphaned_guideline_docs = cursor.fetchone()[0]
if orphaned_guideline_docs == 0:
    print("      [OK] All non-null document_id references are valid")
else:
    print(f"      [ERROR] {orphaned_guideline_docs} guidelines reference non-existent documents")

# Check guidelines.chunk_id references (nullable)
print("   c. guidelines -> document_chunks:")
cursor.execute("""
    SELECT COUNT(*) FROM guidelines
    WHERE chunk_id IS NOT NULL
    AND chunk_id NOT IN (SELECT id FROM document_chunks)
""")
orphaned_guideline_chunks = cursor.fetchone()[0]
if orphaned_guideline_chunks == 0:
    print("      [OK] All non-null chunk_id references are valid")
else:
    print(f"      [ERROR] {orphaned_guideline_chunks} guidelines reference non-existent chunks")

# Check findings.submission_id references
print("   d. findings -> submissions:")
cursor.execute("""
    SELECT COUNT(*) FROM findings
    WHERE submission_id NOT IN (SELECT id FROM submissions)
""")
orphaned_findings = cursor.fetchone()[0]
if orphaned_findings == 0:
    print("      [OK] All findings have valid submission_id references")
else:
    print(f"      [ERROR] {orphaned_findings} findings reference non-existent submissions")

# Check decisions.submission_id references
print("   e. decisions -> submissions:")
cursor.execute("""
    SELECT COUNT(*) FROM decisions
    WHERE submission_id NOT IN (SELECT id FROM submissions)
""")
orphaned_decisions = cursor.fetchone()[0]
if orphaned_decisions == 0:
    print("      [OK] All decisions have valid submission_id references")
else:
    print(f"      [ERROR] {orphaned_decisions} decisions reference non-existent submissions")

# Summary
print("\n=== Summary ===")
total_violations = orphaned_chunks + orphaned_guideline_docs + orphaned_guideline_chunks + orphaned_findings + orphaned_decisions

if len(violations) == 0 and total_violations == 0 and results[0][0] == "ok":
    print("[OK] Database integrity verified - no violations found")
else:
    print(f"[ERROR] Database has integrity issues")
    print(f"  - SQLite integrity_check: {'PASS' if results[0][0] == 'ok' else 'FAIL'}")
    print(f"  - Foreign key violations: {len(violations)}")
    print(f"  - Referential integrity issues: {total_violations}")

conn.close()
print("\n[INFO] Integrity check complete")
