import { describe, expect, it } from "vitest";

import type { SessionSummary } from "@/api/types";
import { progressSeries } from "./history";

function summary(
	sessionId: number,
	recordings: SessionSummary["recordings"],
): SessionSummary {
	return { session_id: sessionId, prototype_id: 1, recordings };
}

describe("progressSeries", () => {
	it("returns an empty series when the session is absent from the payload", () => {
		expect(progressSeries([summary(1, [])], 99)).toEqual([]);
	});

	it("returns an empty series when the session has no recordings", () => {
		expect(progressSeries([summary(1, [])], 1)).toEqual([]);
	});

	it("selects only the requested session", () => {
		const payload = [
			summary(1, [
				{
					recording_id: 1,
					cosine_distance: 0.4,
					created_at: "2026-07-11 10:00:00",
				},
			]),
			summary(2, [
				{
					recording_id: 2,
					cosine_distance: 0.2,
					created_at: "2026-07-11 11:00:00",
				},
			]),
		];
		expect(progressSeries(payload, 2)).toEqual([0.2]);
	});

	it("drops recordings whose analysis produced no distance", () => {
		const payload = [
			summary(1, [
				{
					recording_id: 1,
					cosine_distance: 0.4,
					created_at: "2026-07-11 10:00:00",
				},
				{
					recording_id: 2,
					cosine_distance: null,
					created_at: "2026-07-11 10:01:00",
				},
			]),
		];
		expect(progressSeries(payload, 1)).toEqual([0.4]);
	});

	it("orders the series by recording id regardless of payload order", () => {
		const payload = [
			summary(1, [
				{
					recording_id: 3,
					cosine_distance: 0.19,
					created_at: "2026-07-11 10:02:00",
				},
				{
					recording_id: 1,
					cosine_distance: 0.31,
					created_at: "2026-07-11 10:00:00",
				},
				{
					recording_id: 2,
					cosine_distance: 0.24,
					created_at: "2026-07-11 10:01:00",
				},
			]),
		];
		expect(progressSeries(payload, 1)).toEqual([0.31, 0.24, 0.19]);
	});
});
