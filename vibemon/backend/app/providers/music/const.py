"""Music provider constants: classify-rule visuals and signal phrase tables.

Visual phrases stay anatomy-neutral (palette, texture, markings, sheen) so the element
body archetype keeps sole control of silhouette and body plan in the sprite prompts.
"""

from typing import Literal

RuleCategoryT = Literal["genre", "mood", "instrument"]

# Play-weighted classify rules → short creature-visual cues for GenAI prompts.
RULE_VISUALS: dict[tuple[RuleCategoryT, str], str] = {
    # genre
    ("genre", "metal"): "brushed-steel sheen with rivet-stud markings",
    ("genre", "rock"): "roughened stone texture with guitar-pick-shaped markings",
    ("genre", "indie_alternative"): "hand-painted patch markings and thrift-soft faded tones",
    ("genre", "punk"): "safety-pin glints and patched-scrap stitch markings",
    ("genre", "dark"): "ink-black velvet sheen and silver gothic filigree markings",
    ("genre", "flying"): "hazy soft-focus edges and washed-out pastel tones",
    ("genre", "microgenre"): "glitchy pixel-broken markings and scanline shimmer",
    ("genre", "minimal"): "crystalline geometric facet markings and frost-pale tones",
    ("genre", "noise_industrial"): "rust-streaked patina and smoke-stained tones",
    ("genre", "progressive"): "spiraling fractal markings and layered ring patterns",
    ("genre", "spectral"): "iridescent ghost-sheen shimmer",
    ("genre", "sparkle"): "glitter-dusted markings and candy-bright gem flecks",
    ("genre", "electronic"): "neon edge glow and circuit-trace line markings",
    ("genre", "pop"): "bubblegum-bright palette and candy-pop spot markings",
    ("genre", "hiphop"): "bold block markings and gold-glint accents",
    ("genre", "rnb_soul_funk"): "satin-smooth sheen and groove-line stripes",
    ("genre", "jazz"): "smoky speckled markings and brass-glow accents",
    ("genre", "blues"): "faded denim-blue tones and worn woodgrain texture",
    ("genre", "country"): "straw-gold tones and barn-red band markings",
    ("genre", "reggae_ska"): "checker-stripe markings and sun-bleached tips",
    ("genre", "latin"): "warm terracotta markings and carnival-bright color bands",
    ("genre", "folk"): "leaf-stitched patch markings and twine-texture banding",
    ("genre", "classical"): "marble-smooth pale tones and laurel filigree markings",
    ("genre", "experimental"): "asymmetric collage markings and mismatched texture patches",
    ("genre", "world"): "woven textile-pattern markings and bead-bright dots",
    # mood
    ("mood", "happy"): "sunlit spot markings and warm upbeat brightness",
    ("mood", "sad"): "rain-washed grey tones and tear-streak markings",
    ("mood", "dark"): "shadow-pooled undertones and ash-dust markings",
    ("mood", "energetic"): "flame-tip streak markings and high-voltage color pops",
    ("mood", "calm"): "moss-soft muted tones and gentle gradient washes",
    ("mood", "aggressive"): "scar-line markings and jagged high-contrast streaks",
    ("mood", "dreamy"): "soft-focus edges and pearl-mist shimmer",
    ("mood", "romantic"): "rose-pink blush tones and heart-shaped spot markings",
    ("mood", "epic"): "banner-bright color blocking and gold-trim edging",
    ("mood", "funky"): "zebra-stripe groove markings and disco-glint flecks",
    ("mood", "cold"): "rime-frosted tones and icicle droplet markings",
    ("mood", "warm"): "amber-glow undertones and hearth-warm patches",
    ("mood", "nostalgic"): "faded sepia markings and worn-soft edges",
    # instrument
    ("instrument", "guitar"): "string-line markings and pick-shaped spot accents",
    ("instrument", "piano"): "ivory-and-ebony key-stripe markings",
    ("instrument", "synth"): "LED-edge glow seams and waveform-line markings",
    ("instrument", "drums"): "drum-skin matte patches and stick-stripe markings",
    ("instrument", "violin"): "varnish-amber gloss and bow-curve line markings",
    ("instrument", "acoustic"): "warm woodgrain texture and felt-soft matte finish",
    ("instrument", "orchestral"): "layered brass-and-string filigree markings",
    ("instrument", "bass"): "deep-rumble dark undertones and thick wave-band markings",
    ("instrument", "organ"): "pipe-rank stripe markings and cathedral-dim undertones",
    ("instrument", "brass"): "polished brass sheen and valve-knob ring markings",
    ("instrument", "flute"): "silvery reed-line markings and pearl-hole spot dots",
    ("instrument", "harp"): "golden string-line markings and gilded curve accents",
}

DEFAULT_VISUAL_NOTES = "quiet neutral tones, plain and unmarked"
