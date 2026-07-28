#!/usr/bin/env python3
"""
Export the evaluation dataset from the VoiceMatchr SQLite database as CSV.

One row per analyzed recording, ordered by session then submission, carrying the
cosine distance (the primary outcome measure), the five per-dimension signed
deltas, and the coaching dimension that was targeted. This is the table the final
paper's Results section is built from.

Standard library only. Run against a copy, or with the stack stopped, to avoid
reading mid-transaction WAL state:

    python3 scripts/export_results.py data/voicematchr.db > results.csv
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys

DIMENSIONS = ["f0_mean", "f0_range", "hnr", "spectral_tilt", "loudness"]

_QUERY = """
SELECT
    s.id            AS session_id,
    s.user_id       AS user_id,
    p.voice_name    AS target_voice,
    p.speed         AS target_speed,
    r.id            AS recording_id,
    r.cosine_distance,
    r.delta_vector,
    r.coaching_text,
    r.created_at
FROM recordings r
JOIN sessions s   ON s.id = r.session_id
JOIN prototypes p ON p.id = s.prototype_id
ORDER BY s.id, r.id
"""


def delta_columns(delta_vector: str | None) -> list[float | None]:
    """Unpack the stored JSON delta vector into fixed-order columns."""
    if not delta_vector:
        return [None] * len(DIMENSIONS)
    deltas = json.loads(delta_vector)
    return [deltas.get(dim) for dim in DIMENSIONS]


def export(db_path: str) -> int:
    # mode=ro fails fast on a missing file instead of silently creating an empty
    # database, which plain connect() would do and then report zero recordings.
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        print(f"Cannot open {db_path} read-only: {exc}", file=sys.stderr)
        return 1
    connection.row_factory = sqlite3.Row
    writer = csv.writer(sys.stdout)
    writer.writerow(
        [
            "session_id",
            "user_id",
            "target_voice",
            "target_speed",
            "recording_id",
            "submission_ordinal",
            "cosine_distance",
            *[f"delta_{dim}" for dim in DIMENSIONS],
            "coaching_text",
            "created_at",
        ]
    )

    row_count = 0
    ordinal = 0
    current_session = None
    try:
        rows = connection.execute(_QUERY).fetchall()
    finally:
        connection.close()
    for row in rows:
        # Submission ordinal restarts per session; it is the x-axis of the
        # convergence trajectory, mirroring ProgressChart's labeling.
        if row["session_id"] != current_session:
            current_session = row["session_id"]
            ordinal = 0
        ordinal += 1
        writer.writerow(
            [
                row["session_id"],
                row["user_id"],
                row["target_voice"],
                row["target_speed"],
                row["recording_id"],
                ordinal,
                row["cosine_distance"],
                *delta_columns(row["delta_vector"]),
                row["coaching_text"],
                row["created_at"],
            ]
        )
        row_count += 1

    print(f"exported {row_count} recordings", file=sys.stderr)
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: export_results.py <path-to-voicematchr.db>", file=sys.stderr)
        return 2
    return export(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
