/**
 * Single point of contact with the VoiceMatchr backend.
 * No other module in this application calls fetch() directly (SRP, DRY).
 * Requests are proxied through nginx at /api/ to voicematchr-service:3939.
 *
 * All exports here are called only from client-rendered code (see
 * src/routes/index.tsx and src/routes/session.tsx, which wrap their
 * feature components in ClientOnly). Relative fetch paths only resolve
 * correctly in the browser; do not call these from a loader or from any
 * component that could render during SSR.
 */

import type {
	AnalyzeResponse,
	OnboardRequest,
	OnboardResponse,
	Prototype,
	SessionCreateResponse,
} from "./types";

const API_BASE = import.meta.env.DEV ? "http://localhost:3939" : "/api";

interface ApiErrorBody {
	detail?: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const response = await fetch(`${API_BASE}${path}`, options);
	if (!response.ok) {
		const body: ApiErrorBody = await response.json().catch(() => ({}));
		throw new Error(
			body.detail ?? `Request to ${path} failed with status ${response.status}`,
		);
	}
	return response.json() as Promise<T>;
}

function authHeader(token: string): HeadersInit {
	return { Authorization: `Bearer ${token}` };
}

export function fetchPrototypes(): Promise<Prototype[]> {
	return request<Prototype[]>("/prototypes/");
}

export async function fetchPrototypePreview(
	prototypeId: number,
): Promise<Blob> {
	const response = await fetch(`${API_BASE}/prototypes/${prototypeId}/preview`);
	if (!response.ok) {
		throw new Error("Failed to load voice preview.");
	}
	return response.blob();
}

export function onboardUser(body: OnboardRequest): Promise<OnboardResponse> {
	return request<OnboardResponse>("/users/onboard", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(body),
	});
}

export function createSession(
	prototypeId: number,
	token: string,
): Promise<SessionCreateResponse> {
	return request<SessionCreateResponse>("/sessions/", {
		method: "POST",
		headers: { "Content-Type": "application/json", ...authHeader(token) },
		body: JSON.stringify({ prototype_id: prototypeId }),
	});
}

export function analyzeRecording(
	file: File,
	sessionId: number,
	token: string,
): Promise<AnalyzeResponse> {
	const formData = new FormData();
	formData.append("file", file);
	formData.append("session_id", String(sessionId));
	return request<AnalyzeResponse>("/recordings/analyze", {
		method: "POST",
		headers: authHeader(token),
		body: formData,
	});
}
