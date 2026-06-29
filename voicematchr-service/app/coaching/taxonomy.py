"""
Coaching text taxonomy for VoiceMatchr.

Every coaching paragraph produced by the template generator must instantiate
all four dimensions of this taxonomy simultaneously. A template satisfying
fewer than four dimensions is incomplete and must be revised before committing.

DIMENSION 1 — Specificity  (Kluger & DeNisi, 1996)
    The opening sentence names the acoustic parameter and quantifies the gap.
    It does not evaluate overall quality or assign a global rating.
    BAD:  "Good effort, but your voice needs work."
    GOOD: "Your average pitch on this attempt sits 3.2 semitones above the target."

DIMENSION 2 — Behavioral Directiveness  (Hattie & Timperley, 2007 — feed-forward)
    An imperative specifies exactly what the learner should change next. It
    prescribes action rather than describing the current problem.
    BAD:  "Your pitch was too high."
    GOOD: "On your next recording, bring your voice down by relaxing the muscles
           at the base of your tongue."

DIMENSION 3 — Physiological Grounding  (Molloy, 2021)
    The behavioral directive is paired with a kinesthetic or spatial cue,
    translating the acoustic parameter into a body sensation the learner can
    reproduce without a spectrogram.
    BAD:  "Increase your alpha ratio by adjusting resonance placement."
    GOOD: "Let resonance move forward in your mouth — think of the sound sitting
           just behind your front teeth."

DIMENSION 4 — Autonomy-Supportive Register  (Carpentier & Mageau, 2016)
    The closing phrase preserves learner agency with modal or observational
    language. Commands implying mandatory compliance are avoided.
    BAD:  "Make sure you do this on the next attempt."
    GOOD: "Try the passage again and notice whether the tone becomes cleaner."
"""

from app.services.extractor import DIMENSIONS  # noqa: F401  (re-exported)

DIMENSION_LABELS: dict[str, str] = {
    "f0_mean": "Average Pitch",
    "f0_range": "Pitch Variation",
    "hnr": "Voice Clarity",
    "spectral_tilt": "Vocal Brightness",
    "loudness": "Loudness",
}
