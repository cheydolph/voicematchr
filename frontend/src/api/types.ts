/**
 * Types mirroring the VoiceMatchr backend API contracts.
 * Keys must stay in sync with app/services/extractor.py DIMENSIONS
 * and the response models in app/routes/*.py.
 */

export interface AcousticFeatures {
	f0_mean: number;
	f0_range: number;
	hnr: number;
	spectral_tilt: number;
	loudness: number;
}

export type VocalTrainingHistory = "none" | "amateur" | "professional";
export type CoachingDirection = "above" | "below";

export interface Prototype {
	id: number;
	voice_name: string;
	speed: number;
	f0_mean: number | null;
	f0_range: number | null;
	hnr: number | null;
	spectral_tilt: number | null;
	loudness: number | null;
}

export interface OnboardRequest {
	accent_background: string;
	vocal_training_history: VocalTrainingHistory;
}

export interface OnboardResponse {
	token: string;
}

export interface SessionCreateResponse {
	session_id: number;
}

export interface AnalyzeResponse {
	recording_id: number;
	cosine_distance: number;
	cosine_similarity: number;
	coaching_dimension: keyof AcousticFeatures;
	coaching_direction: CoachingDirection;
	coaching_text: string;
	delta_vector: AcousticFeatures;
	features: AcousticFeatures;
}
