import { useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";

import { fetchSessions } from "@/api/client";
import type { AcousticFeatures, AnalyzeResponse } from "@/api/types";
import ProgressChart from "@/components/ProgressChart";
import RadarChart from "@/components/RadarChart";
import Recorder from "@/components/Recorder";
import SubmitButton from "@/components/SubmitButton";
import UploadPanel from "@/components/UploadPanel";
import { loadSession, type StoredSession } from "@/lib/sessionStorage";
import { progressSeries } from "./history";

function prototypeFeaturesFrom(session: StoredSession): AcousticFeatures {
	const { prototype } = session;
	return {
		f0_mean: prototype.f0_mean ?? 0,
		f0_range: prototype.f0_range ?? 0,
		hnr: prototype.hnr ?? 0,
		spectral_tilt: prototype.spectral_tilt ?? 0,
		loudness: prototype.loudness ?? 0,
	};
}

export default function Session() {
	const navigate = useNavigate();
	const [session] = useState<StoredSession | null>(() => loadSession());
	const [file, setFile] = useState<File | null>(null);
	const [result, setResult] = useState<AnalyzeResponse | null>(null);
	const [distances, setDistances] = useState<number[]>([]);
	const [error, setError] = useState<string | null>(null);

	// The whole history is re-read from the backend rather than appending the newest
	// AnalyzeResponse to local state: the server is the single source of truth for what
	// has been persisted, so the chart stays correct across a reload or a submission
	// made from a second tab.
	const refreshHistory = useCallback(async (current: StoredSession) => {
		try {
			const summaries = await fetchSessions(current.token);
			setDistances(progressSeries(summaries, current.sessionId));
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to load session history.",
			);
		}
	}, []);

	useEffect(() => {
		if (!session) {
			void navigate({ to: "/" });
			return;
		}
		void refreshHistory(session);
	}, [session, navigate, refreshHistory]);

	if (!session) return null;

	const handleResult = (analyzeResult: AnalyzeResponse) => {
		setError(null);
		setResult(analyzeResult);
		void refreshHistory(session);
	};

	return (
		<main className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
			<h1 className="text-2xl font-semibold">
				Target: {session.prototype.voice_name} (speed {session.prototype.speed})
			</h1>

			<Recorder onRecordingReady={(selectedFile) => setFile(selectedFile)} />
			<UploadPanel onFileSelected={(selectedFile) => setFile(selectedFile)} />
			<SubmitButton
				file={file}
				sessionId={session.sessionId}
				token={session.token}
				onResult={handleResult}
				onError={setError}
			/>

			{error && (
				<p role="alert" className="text-sm text-red-600">
					{error}
				</p>
			)}

			{result && (
				<section className="flex flex-col gap-3">
					<h2 className="text-lg font-semibold">This Attempt</h2>
					<p className="text-sm">
						Cosine distance: {result.cosine_distance.toFixed(3)}
					</p>
					<RadarChart
						learnerFeatures={result.features}
						prototypeFeatures={prototypeFeaturesFrom(session)}
					/>
					<h2 className="text-lg font-semibold">What To Try Next</h2>
					<p className="text-sm leading-relaxed">{result.coaching_text}</p>
				</section>
			)}

			<section className="flex flex-col gap-3">
				<h2 className="text-lg font-semibold">Progress Across Submissions</h2>
				<ProgressChart distances={distances} />
			</section>
		</main>
	);
}
