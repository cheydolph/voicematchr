import type { Prototype } from "@/api/types";

/**
 * Local persistence for the active practice session. Not a React hook, and
 * not called from anywhere that could run during SSR (see ClientOnly usage
 * in src/routes/index.tsx and src/routes/session.tsx) — localStorage does
 * not exist in the server rendering environment.
 */

const STORAGE_KEY = "voicematchr.session";

export interface StoredSession {
	token: string;
	sessionId: number;
	prototype: Prototype;
}

export function saveSession(session: StoredSession): void {
	localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function loadSession(): StoredSession | null {
	const raw = localStorage.getItem(STORAGE_KEY);
	if (!raw) return null;
	try {
		return JSON.parse(raw) as StoredSession;
	} catch {
		return null;
	}
}

export function clearSession(): void {
	localStorage.removeItem(STORAGE_KEY);
}
