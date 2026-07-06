import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import type { AcousticFeatures, AnalyzeResponse } from "@/api/types";
import RadarChart from "@/components/RadarChart";
import Recorder from "@/components/Recorder";
import SubmitButton from "@/components/SubmitButton";
import UploadPanel from "@/components/UploadPanel";
import { loadSession, type StoredSession } from "@/lib/sessionStorage";

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
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!session) {
			void navigate({ to: "/" });
		}
	}, [session, navigate]);

	if (!session) return null;

	return (
		<main className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
			<Recorder onRecordingReady={(selectedFile) => setFile(selectedFile)} />
			<UploadPanel onFileSelected={(selectedFile) => setFile(selectedFile)} />
			<SubmitButton
				file={file}
				sessionId={session.sessionId}
				token={session.token}
				onResult={(analyzeResult) => {
					setError(null);
					setResult(analyzeResult);
				}}
				onError={setError}
			/>

			{error && (
				<p role="alert" className="text-sm text-red-600">
					{error}
				</p>
			)}

			{result && (
				<section className="flex flex-col gap-3">
					<p className="text-sm">
						Cosine distance: {result.cosine_distance.toFixed(3)}
					</p>
					<p className="text-sm">{result.coaching_text}</p>
					<RadarChart
						learnerFeatures={result.features}
						prototypeFeatures={prototypeFeaturesFrom(session)}
					/>
				</section>
			)}
		</main>
	);
}
