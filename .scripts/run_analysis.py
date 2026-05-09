# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "sqlalchemy[asyncio]", "aiosqlite"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///
import argparse
import json
import pathlib
import sqlite3
from collections import Counter


DB_PATH = pathlib.Path(__file__).parent / "vibemon.db"
BATTLE_PATH = pathlib.Path(__file__).parent / "generated" / "battle_runs" / "all_battles.txt"


class IdentityProxy:
    __slots__ = ("name", "elements", "base_hp", "base_attack", "base_defense", "base_sp_attack", "base_sp_defense", "base_speed")

    def __init__(self, row: sqlite3.Row) -> None:
        for s in self.__slots__:
            setattr(self, s, row[s] if s != "elements" else json.loads(row[s]))

    @property
    def bst(self) -> int:
        return self.base_hp + self.base_attack + self.base_defense + self.base_sp_attack + self.base_sp_defense + self.base_speed

    @property
    def tier(self) -> str:
        b = self.bst
        if b < 400: return "RUNT"
        if b < 500: return "MID"
        if b < 570: return "SOLID"
        if b < 670: return "APEX"
        return "MYTHIC"

    @property
    def battle_role(self) -> str:
        hp, atk, spa, df, spd, spe = self.base_hp, self.base_attack, self.base_sp_attack, self.base_defense, self.base_sp_defense, self.base_speed
        phys_ehp = hp * df
        spec_ehp = hp * spd
        off = max(atk, spa)
        if spe >= 100 and off >= 80 and max(phys_ehp, spec_ehp) < 8000:
            return "OFFENSIVE_GLASS_CANNON"
        if spe >= 80 and off >= 90 and max(phys_ehp, spec_ehp) < 12000:
            return "OFFENSIVE_SWEEPER"
        if off >= 100 and min(phys_ehp, spec_ehp) > 6000:
            return "OFFENSIVE_WALLBREAKER"
        if spe >= 70 and off >= 60:
            return "UTILITY"
        if spe >= 60 and off >= 50:
            return "UTILITY_CLERIC"
        if spe >= 50 and off >= 50:
            return "UTILITY_PIVOT"
        if off >= 80:
            return "OFFENSIVE_REVENGE_KILLER"
        if max(phys_ehp, spec_ehp) > 14000:
            return "DEFENSIVE_TANK"
        if max(phys_ehp, spec_ehp) > 10000:
            return "DEFENSIVE_WALL"
        return "DEFENSIVE_STALLER"


def analyze_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM vibemon").fetchone()[0]
    idents_raw = conn.execute("SELECT * FROM identity").fetchall()
    idents = [IdentityProxy(r) for r in idents_raw]

    print(f"\n{'='*60}")
    print(f"  VIBEMON POPULATION ANALYSIS")
    print(f"{'='*60}")
    print(f"  Total Vibemon:          {total}")
    print(f"  Unique Identities:      {len(idents)}")

    # Element type distribution
    print(f"\n  --- Element Type Distribution ---")
    all_elements: list[str] = []
    for id_ in idents:
        all_elements.extend(id_.elements)
    elem_counts = Counter(all_elements)
    for elem, count in sorted(elem_counts.items(), key=lambda x: -x[1]):
        pct = count / len(idents) * 100
        bar = "#" * int(pct) + "." * (30 - int(pct))
        print(f"  {elem:>12}: {count:3} ({pct:5.1f}%) {bar[:30]}")

    # Multi-type
    single = sum(1 for id_ in idents if len(id_.elements) == 1)
    dual = sum(1 for id_ in idents if len(id_.elements) == 2)
    print(f"\n  Single-type: {single}  Dual-type: {dual}")

    # Stat distributions
    print(f"\n  --- Base Stat Distribution ---")
    names = ["base_hp", "base_attack", "base_defense", "base_sp_attack", "base_sp_defense", "base_speed"]
    for name in names:
        vals = [getattr(id_, name) for id_ in idents]
        print(f"  {name:>15}: min={min(vals):3}, max={max(vals):3}, avg={sum(vals)/len(vals):6.1f}")

    bsts = [id_.bst for id_ in idents]
    print(f"  {'BST':>15}: min={min(bsts):3}, max={max(bsts):3}, avg={sum(bsts)/len(bsts):6.1f}")

    # Tier distribution
    print(f"\n  --- Tier Distribution ---")
    tiers: Counter = Counter()
    for id_ in idents:
        tiers[id_.tier] += 1
    for tier, count in sorted(tiers.items(), key=lambda x: -x[1]):
        pct = count / len(idents) * 100
        bar = "#" * int(pct) + "." * (30 - int(pct))
        print(f"  {tier:>8}: {count:3} ({pct:5.1f}%) {bar[:30]}")

    # Battle Role distribution (computed)
    print(f"\n  --- Battle Role Distribution (computed) ---")
    roles: Counter = Counter()
    for id_ in idents:
        roles[id_.battle_role] += 1
    for role, count in sorted(roles.items(), key=lambda x: -x[1]):
        pct = count / len(idents) * 100
        bar = "#" * int(pct) + "." * (30 - int(pct))
        print(f"  {role:>30}: {count:3} ({pct:5.1f}%) {bar[:30]}")

    conn.close()


def analyze_battles(battle_path: str) -> None:
    if not pathlib.Path(battle_path).exists():
        print(f"\n  No battle data at {battle_path}")
        return

    with open(battle_path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    print(f"\n{'='*60}")
    print(f"  BATTLE ANALYSIS (5000 simulations)")
    print(f"{'='*60}")

    # Parse each line
    parsed: list[dict[str, str]] = []
    for line in lines:
        d: dict[str, str] = {}
        for part in line.split():
            if "=" in part:
                k, v = part.split("=", 1)
                d[k] = v
        parsed.append(d)

    total = len(parsed)

    # Win rates
    red = sum(1 for p in parsed if p.get("WINNER") == "Red")
    blue = sum(1 for p in parsed if p.get("WINNER") == "Blue")
    draws = sum(1 for p in parsed if p.get("WINNER") == "draw")
    print(f"\n  Total battles:  {total}")
    print(f"  Red wins:       {red:4} ({red/total*100:5.1f}%)")
    print(f"  Blue wins:      {blue:4} ({blue/total*100:5.1f}%)")
    print(f"  Draws:          {draws:4} ({draws/total*100:5.1f}%)")

    # Turn distribution
    turns = [int(p["Turns"]) for p in parsed if "Turns" in p]
    if turns:
        print(f"\n  Turns: min={min(turns)}, max={max(turns)}, avg={sum(turns)/len(turns):.1f}")
        turn_hist: Counter = Counter()
        for t in turns:
            turn_hist[t // 5 * 5] += 1
        for bucket in sorted(turn_hist):
            pct = turn_hist[bucket] / total * 100
            bar = "#" * int(pct * 2) + "." * (60 - int(pct * 2))
            print(f"  {bucket:>3}-{bucket+4}: {turn_hist[bucket]:4} ({pct:5.1f}%) {bar[:40]}")

    # BST advantage analysis
    print(f"\n  --- BST Advantage ---")
    higher_wins, lower_wins, bst_diffs = 0, 0, []
    for p in parsed:
        w = p.get("Winner", "")
        l = p.get("Loser", "")
        if "BST=" not in w or "BST=" not in l:
            continue
        try:
            wbst = int(w.split("BST=")[1].rstrip(")"))
            lbst = int(l.split("BST=")[1].rstrip(")"))
        except (ValueError, IndexError):
            continue
        if p.get("WINNER") == "Blue":
            wbst, lbst = lbst, wbst
        if wbst > lbst:
            higher_wins += 1
        elif wbst < lbst:
            lower_wins += 1
        bst_diffs.append(wbst - lbst)
    total_paired = higher_wins + lower_wins
    if total_paired:
        print(f"  Higher BST won: {higher_wins:4} ({higher_wins/total_paired*100:5.1f}%)")
        print(f"  Lower BST won:  {lower_wins:4} ({lower_wins/total_paired*100:5.1f}%)")
        if bst_diffs:
            print(f"  Avg BST diff:   {sum(bst_diffs)/len(bst_diffs):+.1f}")

    # Type win rates
    print(f"\n  --- Type Win Rates ---")
    type_wins: Counter = Counter()
    type_appearances: Counter = Counter()
    for p in parsed:
        wt = p.get("WinnerTypes", "")
        lt = p.get("LoserTypes", "")
        for t in wt.split("/") if wt else []:
            type_wins[t] += 1
        for t in lt.split("/") if lt else []:
            type_appearances[t] += 1
    all_types = sorted(set(list(type_wins.keys()) + list(type_appearances.keys())))
    for t in all_types:
        wins = type_wins.get(t, 0)
        apps = type_wins.get(t, 0) + type_appearances.get(t, 0)
        if apps:
            rate = wins / apps * 100
            bar = "#" * int(rate / 2) + "." * (50 - int(rate / 2))
            print(f"  {t:>10}: {rate:5.1f}% ({wins:4}/{apps:4}) {bar[:30]}")

    # Role win rates
    print(f"\n  --- Battle Role Win Rates ---")
    role_wins: Counter = Counter()
    role_apps: Counter = Counter()
    for p in parsed:
        wr = p.get("WinnerRole", "")
        lr = p.get("LoserRole", "")
        if wr:
            role_wins[wr] += 1
        if lr:
            role_apps[lr] += 1
    all_roles = sorted(set(list(role_wins.keys()) + list(role_apps.keys())))
    for r in all_roles:
        wins = role_wins.get(r, 0)
        apps = role_wins.get(r, 0) + role_apps.get(r, 0)
        if apps:
            rate = wins / apps * 100
            bar = "#" * int(rate / 2) + "." * (50 - int(rate / 2))
            print(f"  {r:>30}: {rate:5.1f}% ({wins:4}/{apps:4}) {bar[:30]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", type=str, default=str(DB_PATH))
    parser.add_argument("--battle-path", type=str, default=str(BATTLE_PATH))
    args = parser.parse_args()

    analyze_db(args.db_path)
    analyze_battles(args.battle_path)


if __name__ == "__main__":
    main()
