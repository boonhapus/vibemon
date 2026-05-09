# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "sqlalchemy[asyncio]", "aiosqlite"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///
import sqlite3
import pathlib

DB = pathlib.Path(__file__).parent / "vibemon.db"
conn = sqlite3.connect(str(DB))

rows = conn.execute("""
    SELECT i.evo_seed, i.base_hp, i.base_attack, i.base_defense,
           i.base_sp_attack, i.base_sp_defense, i.base_speed
    FROM identity i
    JOIN affinity a ON a.identity_id = i.id
    JOIN vibemon v ON v.affinity_id = a.id
""").fetchall()

groups: dict[int, list[int]] = {}
for r in rows:
    seed = r[0]
    bst = sum(r[1:])
    groups.setdefault(seed, []).append(bst)

total = sum(len(v) for v in groups.values())
print(f"  Identities with vibemon: {total}")
print(f"\n  BST Distribution by Evolution Seed")
print(f"  {'='*70}")
print(f"  {'evo_seed':>10}  {'count':>5}  {'min':>4}  {'max':>4}  {'avg':>6}  {'median':>6}")
print(f"  {'-'*55}")

for seed in sorted(groups.keys()):
    bsts = groups[seed]
    n = len(bsts)
    mn, mx = min(bsts), max(bsts)
    avg = sum(bsts) / n
    med = sorted(bsts)[n // 2]
    print(f"  {seed:>10}  {n:>5}  {mn:>4}  {mx:>4}  {avg:>6.1f}  {med:>6}")

conn.close()
