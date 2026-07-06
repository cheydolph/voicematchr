import type { AcousticFeatures } from "@/api/types";

export const DIMENSION_LABELS: Record<keyof AcousticFeatures, string> = {
	f0_mean: "Average Pitch",
	f0_range: "Pitch Variation",
	hnr: "Voice Clarity",
	spectral_tilt: "Vocal Brightness",
	loudness: "Loudness",
};

export const DIMENSIONS = Object.keys(DIMENSION_LABELS) as Array<
	keyof AcousticFeatures
>;

interface DisplayRange {
	min: number;
	max: number;
}

/**
 * Starting normalization ranges for radar chart display. The backend returns
 * raw eGeMAPSv02 values; these ranges may need adjustment after observing
 * real data from registered prototypes.
 */
export const DIMENSION_RANGES: Record<keyof AcousticFeatures, DisplayRange> = {
	f0_mean: { min: 15, max: 50 },
	f0_range: { min: 0, max: 1 },
	hnr: { min: 0, max: 25 },
	spectral_tilt: { min: -30, max: 0 },
	loudness: { min: 0, max: 1 },
};

export function normalize(
	dimension: keyof AcousticFeatures,
	value: number,
): number {
	const { min, max } = DIMENSION_RANGES[dimension];
	const clamped = Math.min(Math.max(value, min), max);
	return ((clamped - min) / (max - min)) * 100;
}
