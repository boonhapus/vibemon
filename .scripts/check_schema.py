# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "sqlalchemy[asyncio]", "aiosqlite"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///
import sqlite3, pathlib

DB = pathlib.Path(__file__).parent / "vibemon.db"
conn = sqlite3.connect(str(DB))

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    cols = conn.execute(f"PRAGMA table_info({t[0]})").fetchall()
    print(f"{t[0]}: {[c[1] for c in cols]}")

# Check linking
print("\n-- Vibemon -> Affinity -> Identity chain --")
r = conn.execute("SELECT COUNT(*) FROM vibemon").fetchone()
print(f"Vibemon: {r[0]}")
r = conn.execute("SELECT COUNT(*) FROM affinity").fetchone()
print(f"Affinity: {r[0]}")
r = conn.execute("SELECT COUNT(*) FROM identity").fetchone()
print(f"Identity: {r[0]}")

# How many identities are used by vibemon (main affinity)
r = conn.execute("""
    SELECT COUNT(DISTINCT i.id) FROM identity i
    JOIN affinity a ON a.identity_id = i.id
    JOIN vibemon v ON v.affinity_id = a.id
""").fetchone()
print(f"Identities with vibemon (main affinity): {r[0]}")

# How many identities are only in birth_affinities
r = conn.execute("""
    SELECT COUNT(*) FROM identity i
    WHERE i.id IN (
        SELECT identity_id FROM affinity
        WHERE id IN (SELECT affinity_id FROM birth_affinities)
    )
    AND i.id NOT IN (
        SELECT a.identity_id FROM affinity a
        JOIN vibemon v ON v.affinity_id = a.id
    )
""").fetchone()
print(f"Identities only in birth_affinities: {r[0]}")

conn.close()
