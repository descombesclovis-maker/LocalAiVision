"""Curated art-direction families for the premium engine. The LLM only picks a mood; the code
draws palette, type pairing and stylistic switches at random (seeded), so every site differs
while always staying in tasteful territory."""
import random

# palette: bg, surface, text, muted, accent, accent2
MOODS: dict[str, dict] = {
    "dark-cinematic": {
        "label": "Sombre cinématique",
        "palettes": [
            ("#0b0a09", "#16130f", "#f4efe6", "#9c9488", "#ff6a1a", "#ffd166"),
            ("#0a0a0b", "#151517", "#f5f3ee", "#8f8c86", "#f5b700", "#ff4d2e"),
            ("#0d0b0b", "#1a1414", "#f7ece6", "#a4908a", "#ff3b2f", "#ffb38a"),
        ],
        "fonts": [("Anton", "Inter Tight"), ("Bebas Neue", "Manrope"), ("Oswald", "DM Sans"), ("Big Shoulders Display", "Barlow")],
        "case": "uppercase", "weight": 400, "tracking": "0", "heroes": ["cinematic", "kinetic", "split"],
    },
    "editorial-classic": {
        "label": "Éditorial classique",
        "palettes": [
            ("#f2ece1", "#e8e0d1", "#1c1a17", "#6f675c", "#1f3fb5", "#c7522a"),
            ("#f5f1ea", "#ebe4d8", "#191714", "#736a5f", "#9b1c1c", "#2f4b3a"),
            ("#efe9df", "#e4dccd", "#201c18", "#6d6459", "#556b2f", "#b5651d"),
        ],
        "fonts": [("Playfair Display", "Inter"), ("Cormorant Garamond", "Work Sans"), ("DM Serif Display", "Karla"), ("Instrument Serif", "Inter Tight")],
        "case": "none", "weight": 400, "tracking": "-0.02em", "heroes": ["editorial", "split", "kinetic"],
    },
    "tech-futurist": {
        "label": "Tech futuriste",
        "palettes": [
            ("#05070a", "#0d1117", "#e9f1f7", "#7d8a96", "#b6ff3b", "#3be8ff"),
            ("#06060a", "#101018", "#eceaf5", "#85839a", "#3be8ff", "#8b5cf6"),
            ("#070807", "#111311", "#ecf0ea", "#868d84", "#ff5e1a", "#e8ff3b"),
        ],
        "fonts": [("Space Grotesk", "Inter"), ("Unbounded", "Manrope"), ("Syne", "IBM Plex Sans"), ("Sora", "JetBrains Mono")],
        "case": "none", "weight": 600, "tracking": "-0.045em", "heroes": ["network", "cinematic", "kinetic"],
    },
    "warm-artisan": {
        "label": "Artisan chaleureux",
        "palettes": [
            ("#1a120d", "#24180f", "#f6e9da", "#b39b84", "#e0703a", "#e8b04a"),
            ("#f4eadc", "#eadbc6", "#2a1d14", "#7a6552", "#c4552b", "#6b7f3a"),
            ("#efe4d2", "#e2d3bb", "#2b2118", "#7b6a58", "#a3472a", "#d99a2b"),
        ],
        "fonts": [("Fraunces", "Outfit"), ("Young Serif", "Figtree"), ("Gloock", "Mulish"), ("Bricolage Grotesque", "Lora")],
        "case": "none", "weight": 600, "tracking": "-0.03em", "heroes": ["split", "editorial", "cinematic"],
    },
    "luxury-minimal": {
        "label": "Luxe minimal",
        "palettes": [
            ("#0e0e0d", "#181816", "#efe9df", "#8f897f", "#c8a96a", "#e7d7b4"),
            ("#f6f4f0", "#ece8e1", "#141412", "#77736b", "#9a7b4f", "#2c2a26"),
            ("#101214", "#191c1f", "#eceae6", "#8b8e91", "#b8c4cc", "#d8b98a"),
        ],
        "fonts": [("Cormorant", "Jost"), ("Italiana", "Montserrat"), ("Bodoni Moda", "Hanken Grotesk"), ("Marcellus", "Raleway")],
        "case": "uppercase", "weight": 400, "tracking": "0.04em", "heroes": ["cinematic", "editorial", "split"],
    },
    "bold-pop": {
        "label": "Pop audacieux",
        "palettes": [
            ("#f4f1ea", "#ebe6da", "#111111", "#5f5b55", "#ff4d2e", "#2b59ff"),
            ("#fff8ec", "#f8ead1", "#141014", "#66595f", "#ff3ea5", "#1fbf75"),
            ("#121212", "#1d1d1d", "#f8f6f0", "#9a978f", "#ffe14d", "#ff4d2e"),
        ],
        "fonts": [("Archivo Black", "Archivo"), ("Dela Gothic One", "Space Grotesk"), ("Darker Grotesque", "Rubik"), ("Familjen Grotesk", "Instrument Sans")],
        "case": "uppercase", "weight": 900, "tracking": "-0.03em", "heroes": ["kinetic", "split", "editorial"],
    },
    "nature-organic": {
        "label": "Nature organique",
        "palettes": [
            ("#eef0e6", "#e1e5d5", "#18231b", "#5f6b5f", "#3f7d4e", "#c9a227"),
            ("#10201a", "#172b23", "#eef2e6", "#93a597", "#a8d672", "#e9c46a"),
            ("#f3efe6", "#e7e1d3", "#1f2a24", "#69736b", "#2f6f73", "#d4874c"),
        ],
        "fonts": [("Libre Caslon Display", "Nunito Sans"), ("Gloock", "Figtree"), ("Newsreader", "Outfit"), ("Fraunces", "Karla")],
        "case": "none", "weight": 400, "tracking": "-0.02em", "heroes": ["editorial", "split", "cinematic"],
    },
}

LABELS = ["// {n}", "({n})", "N°{n}", "— {n}", "[{n}]"]


def _lum(hex_: str) -> float:
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def pick_theme(mood: str, seed: str) -> dict:
    rnd = random.Random(seed)
    fam = MOODS.get(mood) or MOODS[rnd.choice(list(MOODS))]
    mood = next(k for k, v in MOODS.items() if v is fam)
    bg, surface, text, muted, accent, accent2 = rnd.choice(fam["palettes"])
    if rnd.random() < 0.35:
        accent, accent2 = accent2, accent
    heading, body = rnd.choice(fam["fonts"])
    return {
        "mood": mood,
        "mood_label": fam["label"],
        "palette": {"background": bg, "surface": surface, "text": text, "muted": muted, "accent": accent, "accent2": accent2},
        "accent_ink": "#0b0b0b" if _lum(accent) > 0.55 else "#ffffff",
        "dark": _lum(bg) < 0.4,
        "fonts": {"heading": heading, "body": body},
        "case": fam["case"],
        "weight": fam["weight"],
        "tracking": fam["tracking"],
        "hero": rnd.choice(fam["heroes"]),
        "radius": rnd.choice(["0px", "6px", "18px", "999px"]),
        "cursor": rnd.choice(["dot", "ring", "blend", "none"]),
        "label": rnd.choice(LABELS),
        "grain": rnd.random() < 0.6,
        "header": rnd.choice(["split", "center", "pill"]),
        "footer": rnd.choice(["giant", "columns"]),
        "scale": rnd.choice([0.9, 1.0, 1.12]),
        "loader": rnd.random() < 0.7,
        "seed": rnd.randint(1, 10**6),
    }
