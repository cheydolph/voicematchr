"""
Dimension-specific template bank for the VoiceMatchr coaching text generator.

Authoring rules:
  - Plain prose only. No markdown, bolding, or HTML.
  - Three to five sentences per template.
  - Every template must pass the four-dimension taxonomy checklist in
    taxonomy.py before being committed.
  - State measurements as facts. Do not hedge with "possibly" or "might be."
"""

from __future__ import annotations

TEMPLATES: dict[str, dict[str, str]] = {
    "f0_mean": {
        "above": (
            "Your average pitch on this attempt sits about {delta:.1f} semitones above the target. "
            "On your next recording, bring your voice down by relaxing the muscles at the base of "
            "your tongue and letting your larynx settle lower in your throat — imagine the sound "
            "originating in your chest rather than behind your eyes. "
            "Try the passage again and see whether you can sustain that lower center without "
            "letting the pitch rise at the ends of phrases."
        ),
        "below": (
            "Your average pitch on this attempt sits about {delta:.1f} semitones below the target. "
            "On your next recording, let your voice lift by thinking of the sound arcing forward "
            "and upward — place it behind your front teeth rather than in your throat. "
            "Read the passage again and allow yourself to reach for the upper end of your "
            "comfortable range on stressed syllables, and notice whether the center settles higher."
        ),
    },
    "f0_range": {
        "above": (
            "Your pitch variation on this attempt is wider than the target by about "
            "{delta:.2f} normalized units. "
            "On your next recording, narrow your intonation arc: let most syllables land at a "
            "similar level and reserve pitch movement for only the most semantically important words. "
            "Think of your voice as a line that stays level except at deliberate peaks, "
            "and see if you can reduce the overall sweep while keeping the delivery from sounding flat."
        ),
        "below": (
            "Your pitch variation on this attempt fell about {delta:.2f} normalized units short "
            "of the target. "
            "On your next recording, widen the arc of your intonation — imagine your voice lifting "
            "into the room as each phrase rises and landing with weight on the final stressed syllable. "
            "Try reading the passage again and let the ends of sentences land higher or lower than "
            "feels entirely natural, and notice whether the overall arc becomes more expressive."
        ),
    },
    "hnr": {
        "above": (
            "Your voice on this attempt is cleaner than the target, with an HNR gap "
            "of about {delta:.1f} dB. "
            "On your next recording, allow a small amount of breath to mix into the tone — "
            "think of letting your breath and voice travel the same channel without holding "
            "the air back, as though the tone is being carried outward on a slow exhale. "
            "A slight relaxation of glottal closure on sustained vowels may help you match "
            "the prototype's texture; try the passage and see whether the voice feels slightly more open."
        ),
        "below": (
            "Your voice on this attempt is breathier than the target, with an HNR gap "
            "of about {delta:.1f} dB. "
            "On your next recording, bring the edges of your vocal folds into firmer contact "
            "by thinking of the sound as having a narrow, focused core — imagine projecting "
            "toward a specific point across the room and keeping the tone tightly aimed there. "
            "Try the passage again and notice whether the voice feels cleaner and more "
            "forward-placed when you maintain that imagined target."
        ),
    },
    "spectral_tilt": {
        "above": (
            "The brightness of your voice on this attempt is above the target by about "
            "{delta:.2f} alpha-ratio units. "
            "On your next recording, warm the tone by directing resonance toward the back of "
            "your mouth — let the sound feel fuller behind your upper molars rather than in "
            "front of your lips, and allow your lips to close slightly on rounded vowels. "
            "Try the passage again with a slightly more relaxed, back-placed resonance and "
            "see whether the tone becomes warmer without losing its projection."
        ),
        "below": (
            "The brightness of your voice on this attempt is below the target by about "
            "{delta:.2f} alpha-ratio units. "
            "On your next recording, brighten the tone by letting resonance move forward in "
            "your mouth — think of the sound sitting just behind your front teeth, or of "
            "projecting to a point above the listener's eye level. "
            "Try the passage again with a slightly more open upper-resonance space and "
            "notice whether the sound becomes cleaner and more forward-placed."
        ),
    },
    "loudness": {
        "above": (
            "Your overall loudness on this attempt is about {delta:.2f} units above the target. "
            "On your next recording, reduce your projection slightly — think of directing the "
            "sound toward a listener two or three feet away rather than across a large room, "
            "and let your breath support the tone without pushing from behind it. "
            "Try the passage at a conversational level and see whether the volume settles "
            "closer to the target while the tone stays clear."
        ),
        "below": (
            "Your overall loudness on this attempt is about {delta:.2f} units below the target. "
            "On your next recording, increase your projection by imagining you are speaking to "
            "someone just past the back of the room — feel your breath expand outward from your "
            "lower ribcage rather than from your chest or throat. "
            "Try the passage again with that expanded breath support and notice whether the "
            "volume increases without added tension in your neck or jaw."
        ),
    },
}


def select_template(dimension: str, direction: str, delta: float) -> str:
    """
    Render and return a coaching paragraph for `dimension`.

    Args:
        dimension: One of the keys in TEMPLATES (matches DIMENSIONS in extractor.py).
        direction: 'above' if learner value exceeds prototype value, else 'below'.
        delta:     Absolute magnitude of the gap in dimension-native units.

    Raises:
        KeyError: If `dimension` or `direction` is not present in TEMPLATES.
    """
    return TEMPLATES[dimension][direction].format(delta=delta)
