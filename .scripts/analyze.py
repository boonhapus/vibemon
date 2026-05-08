import sqlite3
import json
import sys

conn = sqlite3.connect('.scripts/vibemon.db')
conn.row_factory = sqlite3.Row

# Tier thresholds from schema.py Identity.tier
def get_tier(bst):
    if bst < 400: return "RUNT"
    if bst < 500: return "MID"
    if bst < 570: return "SOLID"
    if bst < 670: return "APEX"
    return "MYTHIC"

def get_battle_role(row):
    hp = row["base_hp"]
    atk = row["base_attack"]
    defense = row["base_defense"]
    sp_atk = row["base_sp_attack"]
    sp_def = row["base_sp_defense"]
    speed = row["base_speed"]
    bst = hp + atk + defense + sp_atk + sp_def + speed

    offense_weight = atk + sp_atk + speed
    defense_weight = hp + defense + sp_def
    off_pct = offense_weight / bst
    def_pct = defense_weight / bst
    spd_pct = speed / bst
    ehp_pct = hp / bst
    is_fast = speed >= 80
    is_slow = speed < 50
    is_squishy = defense < 50 and sp_def < 50
    is_tanky = defense >= 70 or sp_def >= 70
    is_fast_breaker = is_fast and (atk >= 70 or sp_atk >= 70)
    is_slow_breaker = is_slow and (atk >= 70 or sp_atk >= 70)

    if def_pct > 0.5 and is_tanky and ehp_pct > 0.2: return "DEFENSIVE_WALL"
    if def_pct > 0.4 and (atk >= 50 or sp_atk >= 50): return "DEFENSIVE_TANK"
    if def_pct > 0.45 and is_slow: return "DEFENSIVE_STALLER"
    if off_pct > 0.55 and is_fast and is_squishy: return "OFFENSIVE_GLASS_CANNON"
    if off_pct > 0.55 and is_fast_breaker: return "OFFENSIVE_SWEEPER"
    if off_pct > 0.55 and is_slow_breaker: return "OFFENSIVE_WALLBREAKER"
    if off_pct > 0.5 and spd_pct > 0.25: return "OFFENSIVE_REVENGE_KILLER"
    if spd_pct > 0.3 and def_pct > 0.35: return "UTILITY_PIVOT"
    if off_pct < 0.45 and def_pct < 0.45: return "UTILITY_CLERIC"
    return "UTILITY"

rows = conn.execute('SELECT * FROM identity').fetchall()
data = []
for r in rows:
    bst = r["base_hp"] + r["base_attack"] + r["base_defense"] + r["base_sp_attack"] + r["base_sp_defense"] + r["base_speed"]
    tier = get_tier(bst)
    role = get_battle_role(r)
    elements = json.loads(r["elements"])
    data.append({
        "name": r["name"],
        "bst": bst,
        "tier": tier,
        "role": role,
        "elements": elements,
        "evo_stage": r["evo_stage"],
        "evo_seed": r["evo_seed"],
        "is_mythic": bool(r["is_mythic"]),
        "hp": r["base_hp"], "attack": r["base_attack"], "defense": r["base_defense"],
        "sp_attack": r["base_sp_attack"], "sp_defense": r["base_sp_defense"], "speed": r["base_speed"],
    })

# === Tier distribution ===
print("=" * 60)
print("TIER DISTRIBUTION")
print("=" * 60)
tiers = {}
for d in data:
    tiers.setdefault(d["tier"], {"count": 0, "bsts": [], "stats": {s: [] for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]}})
    t = tiers[d["tier"]]
    t["count"] += 1
    t["bsts"].append(d["bst"])
    for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]:
        t["stats"][s].append(d[s])

for tname in ["RUNT", "MID", "SOLID", "APEX", "MYTHIC"]:
    if tname not in tiers: continue
    t = tiers[tname]
    avg_bst = sum(t["bsts"]) / len(t["bsts"])
    print(f"\n{tname} ({t['count']} mons, avg BST: {avg_bst:.0f})")
    for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]:
        avg = sum(t["stats"][s]) / len(t["stats"][s])
        print(f"  {s:>10}: avg={avg:>6.1f}")

# === Role distribution ===
print("\n" + "=" * 60)
print("ROLE DISTRIBUTION")
print("=" * 60)
roles = {}
for d in data:
    roles.setdefault(d["role"], {"count": 0, "tiers": {}, "bsts": [], "stats": {s: [] for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]}})
    r = roles[d["role"]]
    r["count"] += 1
    r["tiers"][d["tier"]] = r["tiers"].get(d["tier"], 0) + 1
    r["bsts"].append(d["bst"])
    for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]:
        r["stats"][s].append(d[s])

for rname in sorted(roles, key=lambda x: roles[x]["count"], reverse=True):
    r = roles[rname]
    avg_bst = sum(r["bsts"]) / len(r["bsts"])
    tiers_str = ", ".join(f"{k}={v}" for k, v in sorted(r["tiers"].items()))
    print(f"\n{rname} ({r['count']} mons, avg BST: {avg_bst:.0f})")
    print(f"  Tier split: {tiers_str}")
    for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]:
        avg = sum(r["stats"][s]) / len(r["stats"][s])
        print(f"  {s:>10}: avg={avg:>6.1f}")

# === Element distribution ===
print("\n" + "=" * 60)
print("ELEMENT DISTRIBUTION")
print("=" * 60)
elements = {}
element_solo = {}
for d in data:
    for e in d["elements"]:
        elements.setdefault(e, {"count": 0, "bsts": [], "stats": {s: [] for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]}})
        el = elements[e]
        el["count"] += 1
        el["bsts"].append(d["bst"])
        for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]:
            el["stats"][s].append(d[s])
    if len(d["elements"]) == 1:
        element_solo.setdefault(d["elements"][0], {"count": 0, "bsts": [], "stats": {s: [] for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]}})
        el = element_solo[d["elements"][0]]
        el["count"] += 1
        el["bsts"].append(d["bst"])
        for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]:
            el["stats"][s].append(d[s])

# Dual type counts
dual_counts = {}
for d in data:
    if len(d["elements"]) == 2:
        key = tuple(sorted(d["elements"]))
        dual_counts[key] = dual_counts.get(key, 0) + 1

for ename in sorted(elements, key=lambda x: elements[x]["count"], reverse=True):
    el = elements[ename]
    avg_bst = sum(el["bsts"]) / len(el["bsts"])
    solo = element_solo.get(ename, {}).get("count", 0)
    print(f"\n{ename.upper()} ({el['count']} total, {solo} pure)")
    print(f"  avg BST: {avg_bst:.0f}")
    for s in ["hp","attack","defense","sp_attack","sp_defense","speed"]:
        avg = sum(el["stats"][s]) / len(el["stats"][s])
        print(f"  {s:>10}: avg={avg:>6.1f}")

# === BST histogram by tier ===
print("\n" + "=" * 60)
print("BST HISTOGRAM")
print("=" * 60)
all_bsts = sorted(d["bst"] for d in data)
# bucket into ranges of 50
buckets = {}
for b in all_bsts:
    bucket = (b // 50) * 50
    buckets[bucket] = buckets.get(bucket, 0) + 1
for bucket in sorted(buckets):
    bar = "#" * buckets[bucket]
    print(f"{bucket:>3}-{bucket+49:>3}: {bar} ({buckets[bucket]})")

# === Mythic distribution ===
print("\n" + "=" * 60)
print("MYTHIC DISTRIBUTION")
print("=" * 60)
mythics = [d for d in data if d["is_mythic"]]
print(f"Mythic mons: {len(mythics)}/{len(data)} ({100*len(mythics)/len(data):.1f}%)")
if mythics:
    avg_bst = sum(m["bst"] for m in mythics) / len(mythics)
    print(f"Mythic avg BST: {avg_bst:.0f}")

# === Anomalies ===
print("\n" + "=" * 60)
print("POTENTIAL ANOMALIES")
print("=" * 60)
# RUNT with BST > 370
for d in data:
    if d["tier"] == "RUNT" and d["bst"] > 370:
        print(f"  High RUNT: {d['name']} (BST={d['bst']})")
    if d["tier"] == "MYTHIC" and d["bst"] < 680:
        print(f"  Low MYTHIC: {d['name']} (BST={d['bst']})")

# Stats that seem extreme
for d in data:
    stats = {k: d[k] for k in ["hp","attack","defense","sp_attack","sp_defense","speed"]}
    max_s = max(stats, key=stats.get)
    min_s = min(stats, key=stats.get)
    if stats[max_s] >= 180:
        print(f"  Extreme stat: {d['name']} ({d['tier']}) - {max_s}={stats[max_s]}")
    if stats[min_s] <= 10 and d["bst"] > 300:
        print(f"  Dump stat: {d['name']} ({d['tier']}) - {min_s}={stats[min_s]}")
