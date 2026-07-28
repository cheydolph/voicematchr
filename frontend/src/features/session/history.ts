import type { RecordingSummary, SessionSummary } from "@/api/types";

function hasDistance(
	recording: RecordingSummary,
): recording is RecordingSummary & { cosine_distance: number } {
	return typeof recording.cosine_distance === "number";
}

/**
 * Reduce the GET /sessions/ payload to the cosine-distance series of one session,
 * oldest submission first.
 *
 * Pure and total: an unknown session id, or a session whose recordings all failed
 * analysis, yields an empty series rather than throwing. Recordings are sorted by
 * recording_id here rather than trusting the server's ORDER BY, and any recording
 * with a null distance (the column is nullable) is dropped, so ProgressChart
 * receives nothing but plottable numbers and needs no knowledge of the API shape.
 */
export function progressSeries(
	summaries: readonly SessionSummary[],
	sessionId: number,
): number[] {
	const match = summaries.find((summary) => summary.session_id === sessionId);
	if (!match) return [];
	return match.recordings
		.filter(hasDistance)
		.sort((left, right) => left.recording_id - right.recording_id)
		.map((recording) => recording.cosine_distance);
}
