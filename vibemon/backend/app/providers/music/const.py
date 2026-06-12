"""Music provider constants: classify-rule visuals and signal phrase tables."""

from typing import Literal

RuleCategoryT = Literal["genre", "mood", "instrument"]

# Play-weighted classify rules → short creature-visual cues for GenAI prompts.
RULE_VISUALS: dict[tuple[RuleCategoryT, str], str] = {
    # genre
    ("genre", "metal"): "spiked steel plates and brushed dark hide",
    ("genre", "rock"): "guitar-pick horn crest and roughened stone hide",
    ("genre", "indie_alternative"): "hand-painted patch markings and thrift-soft fur",
    ("genre", "punk"): "safety-pin spines and patched scrap hide",
    ("genre", "dark"): "ink-black velvet fur and silver gothic filigree",
    ("genre", "flying"): "hazy translucent wing edges and washed-out pastel hide",
    ("genre", "microgenre"): "glitchy pixel-broken markings and buzzing antenna stubs",
    ("genre", "minimal"): "crystalline geometric facets and frost-pale hide",
    ("genre", "noise_industrial"): "rusted rivet plates and smoke-stained hide",
    ("genre", "progressive"): "spiraling fractal markings and layered crest rings",
    ("genre", "spectral"): "iridescent ghost-sheen scales",
    ("genre", "sparkle"): "glitter-dusted markings and candy-bright crest gems",
    ("genre", "electronic"): "neon edge glow and synth-panel chest plates",
    ("genre", "pop"): "bubblegum roundness and chart-bright cheek spots",
    ("genre", "hiphop"): "bold block markings and gold-chain collar ridge",
    ("genre", "rnb_soul_funk"): "satin-smooth hide and groove-line stripes",
    ("genre", "jazz"): "smoky speckled markings and brass-knob horn buds",
    ("genre", "blues"): "faded denim-blue hide and worn woodgrain horns",
    ("genre", "country"): "straw-gold mane tufts and barn-red band markings",
    ("genre", "reggae_ska"): "checker stripe flanks and sun-bleached tail tip",
    ("genre", "latin"): "warm terracotta markings and carnival feather crest",
    ("genre", "folk"): "leaf-stitched patch fur and twine-wrapped leg bands",
    ("genre", "classical"): "marble-smooth pale hide and laurel filigree markings",
    ("genre", "experimental"): "asymmetric collage markings and mismatched limb textures",
    ("genre", "world"): "woven textile-pattern flanks and bead-bright crest dots",
    # mood
    ("mood", "happy"): "bouncy round cheeks and sunlit spot markings",
    ("mood", "sad"): "drooped ears and rain-washed grey hide",
    ("mood", "dark"): "shadow-pooled underbelly and ash-dust markings",
    ("mood", "energetic"): "coiled spring legs and flame-tip tail streaks",
    ("mood", "calm"): "slow-blink eyes and moss-soft paw pads",
    ("mood", "aggressive"): "knuckled crest spines and scar-line markings",
    ("mood", "dreamy"): "soft-focus edges and pearl-mist wing membranes",
    ("mood", "romantic"): "rose-pink cheek blush and heart-shaped tail tip",
    ("mood", "epic"): "heroic upright crest and banner-like dorsal fin",
    ("mood", "funky"): "zebra-stripe groove markings and platform-thick paws",
    ("mood", "cold"): "rime-frosted hide and icicle droplet markings",
    ("mood", "warm"): "amber-glow belly fur and hearth-warm cheek patches",
    ("mood", "nostalgic"): "faded sepia markings and worn-soft edges",
    # instrument
    ("instrument", "guitar"): "pick-shaped dorsal crest and string-line flank markings",
    ("instrument", "piano"): "ivory-key belly stripes and ebony paw pads",
    ("instrument", "synth"): "LED-edge glow seams and keyboard-ridge spine",
    ("instrument", "drums"): "round tom-shaped shoulder pads and stick-striped tail",
    ("instrument", "violin"): "bow-curve tail and varnish-amber flank wood",
    ("instrument", "acoustic"): "warm woodgrain hide and felt-soft unpolished paws",
    ("instrument", "orchestral"): "layered brass-and-string crest filigree",
    ("instrument", "bass"): "low thick stump legs and deep rumble throat markings",
    ("instrument", "organ"): "pipe-rank dorsal spines and reverberant hollow chest",
    ("instrument", "brass"): "brassy horn-snout and valve-knob joint rings",
    ("instrument", "flute"): "slender reed neck and pearl-hole spot markings",
    ("instrument", "harp"): "golden string-line mane and curved harp-bow crest",
}

DEFAULT_VISUAL_NOTES = "quiet neutral hide, still and unmarked"
