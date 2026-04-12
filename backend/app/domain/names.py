from __future__ import annotations

import random

SYLLABLES: dict[str, list[str]] = {
    "Fire": [
        "pyr", "emb", "bla", "sol", "ign", "kar", "tor", "vul", "cin", "scor",
        "ash", "cind", "flar", "mag", "inf", "sear", "char", "vol", "fyr", "bran",
        "coa", "ember", "flare", "kind", "lava", "nova", "spark", "ther", "wild", "zen",
        "aro", "blaz", "cal", "drak", "ember", "fue", "glow", "heat", "infer", "kind",
    ],
    "Water": [
        "aqu", "tid", "rip", "del", "vas", "mer", "flu", "tur", "bri", "cor",
        "mar", "nept", "ocean", "plank", "riv", "sal", "surf", "tide", "wave", "whelm",
        "blue", "coral", "deep", "foam", "gulf", "kelp", "lag", "mist", "naut", "pool",
        "rain", "spray", "swell", "trid", "und", "vap", "wet", "whirl", "sur", "ript",
    ],
    "Ice": [
        "gla", "fro", "cry", "chi", "sno", "bor", "gel", "arc", "hal", "nim",
        "rime", "shard", "ic", "polar", "berg", "chill", "hail", "sleet", "win", "yeti",
        "bore", "drift", "flake", "glac", "hoar", "ice", "jok", "kel", "melt", "north",
        "rime", "skate", "tund", "urs", "vail", "wint", "yuk", "zero", "froz", "icel",
    ],
    "Electric": [
        "vol", "sho", "zap", "amp", "thr", "kin", "cra", "sul", "ion", "nex",
        "bolt", "charge", "jolt", "ohm", "spark", "stat", "volt", "watt", "zest", "arc",
        "live", "neon", "plasma", "pulse", "shock", "surge", "tes", "volt", "wire", "zap",
        "flash", "grid", "hum", "lekt", "magn", "node", "ohm", "pulse", "relay", "storm",
    ],
    "Grass": [
        "vir", "blo", "spr", "flo", "lea", "mos", "tho", "cha", "fer", "gro",
        "root", "vine", "seed", "fern", "moss", "clad", "stem", "bud", "peat", "syl",
        "oak", "pine", "reed", "rush", "sage", "thorn", "weed", "yew", "zen", "bloom",
        "clover", "dew", "elm", "frond", "green", "herb", "ivy", "jade", "kud", "leaf",
    ],
    "Ground": [
        "ter", "bou", "qua", "sed", "gra", "mol", "cla", "dus", "bru", "erd",
        "stone", "rock", "sand", "clay", "silt", "crag", "mesa", "dune", "loam", "marl",
        "crust", "depth", "earth", "foss", "grit", "hard", "iron", "mine", "ore", "pit",
        "quar", "rubble", "soil", "turf", "under", "vault", "weld", "yard", "zone", "bed",
    ],
    "Dark": [
        "nox", "sha", "voi", "hex", "dre", "cur", "obs", "phe", "sco", "nul",
        "shade", "gloom", "void", "umbra", "night", "eclipse", "murk", "dusk", "grim", "haze",
        "black", "crow", "dread", "fang", "grim", "hollow", "ink", "jet", "knell", "lurk",
        "mire", "nether", "onyx", "pitch", "que", "rift", "shade", "tar", "umb", "veil",
    ],
    "Psychic": [
        "psi", "pha", "tel", "mne", "eso", "var", "mis", "eid", "zer", "kal",
        "mind", "aura", "dream", "vision", "trance", "zen", "echo", "omen", "rune", "soul",
        "astro", "blur", "cosm", "delta", "ether", "flux", "glim", "halo", "id", "jinx",
        "karma", "lumen", "myst", "nova", "orb", "pulse", "quas", "rift", "sig", "tele",
    ],
    "Normal": [
        "nor", "com", "bas", "sim", "ord", "gen", "pri", "pla", "ven", "mid",
        "plain", "mono", "neo", "typ", "van", "reg", "std", "bal", "even", "fair",
        "apex", "blend", "core", "dual", "even", "fair", "gist", "hub", "icon", "join",
        "kind", "link", "mean", "norm", "open", "peak", "quo", "rest", "sync", "true",
    ],
}


_VOWELS = frozenset("aeiouyAEIOUY")


def _has_triple_consonant(s: str) -> bool:
    run = 0
    for ch in s:
        if ch in _VOWELS:
            run = 0
        elif ch.isalpha():
            run += 1
            if run >= 3:
                return True
    return False


def generate_name(element: str, seed: int) -> str:
    pool = SYLLABLES.get(element) or SYLLABLES["Normal"]
    rng = random.Random(seed)
    for _ in range(16):
        n_syl = rng.randint(2, 3)
        parts = [rng.choice(pool) for _ in range(n_syl)]
        raw = "".join(parts)
        if not _has_triple_consonant(raw):
            return raw[:1].upper() + raw[1:10]
    raw = "".join(rng.choice(pool) for _ in range(2))
    return raw[:1].upper() + raw[1:10]
