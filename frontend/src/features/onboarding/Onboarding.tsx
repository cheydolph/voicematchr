import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import {
	createSession,
	fetchPrototypePreview,
	fetchPrototypes,
	onboardUser,
} from "@/api/client";
import type { Prototype, VocalTrainingHistory } from "@/api/types";
import { saveSession } from "@/lib/sessionStorage";

export default function Onboarding() {
	const navigate = useNavigate();
	const [prototypes, setPrototypes] = useState<Prototype[]>([]);
	const [selected, setSelected] = useState<Prototype | null>(null);
	const [accentBackground, setAccentBackground] = useState("");
	const [trainingHistory, setTrainingHistory] =
		useState<VocalTrainingHistory>("none");
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		fetchPrototypes()
			.then(setPrototypes)
			.catch((err: unknown) => {
				setError(
					err instanceof Error ? err.message : "Failed to load target voices.",
				);
			});
	}, []);

	const playPreview = async (prototypeId: number) => {
		try {
			const blob = await fetchPrototypePreview(prototypeId);
			await new Audio(URL.createObjectURL(blob)).play();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Preview playback failed.");
		}
	};

	const handleSubmit = async () => {
		if (!selected) {
			setError("Select a target voice first.");
			return;
		}
		try {
			const { token } = await onboardUser({
				accent_background: accentBackground,
				vocal_training_history: trainingHistory,
			});
			const { session_id: sessionId } = await createSession(selected.id, token);
			saveSession({ token, sessionId, prototype: selected });
			await navigate({ to: "/session" });
		} catch (err) {
			setError(err instanceof Error ? err.message : "Onboarding failed.");
		}
	};

	return (
		<main className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
			<h1 className="text-2xl font-semibold">Choose Your Target Voice</h1>
			{error && (
				<p role="alert" className="text-sm text-red-600">
					{error}
				</p>
			)}

			<div className="flex flex-col gap-3">
				{prototypes.map((prototype) => (
					<div
						key={prototype.id}
						className="flex items-center justify-between rounded-md border border-neutral-200 px-4 py-3"
					>
						<span>
							{prototype.voice_name} (speed {prototype.speed})
						</span>
						<div className="flex gap-2">
							<button
								type="button"
								onClick={() => void playPreview(prototype.id)}
								className="rounded-md border px-3 py-1 text-sm"
							>
								Play
							</button>
							<button
								type="button"
								onClick={() => setSelected(prototype)}
								className="rounded-md bg-blue-600 px-3 py-1 text-sm text-white"
							>
								{selected?.id === prototype.id ? "Selected" : "Select"}
							</button>
						</div>
					</div>
				))}
			</div>

			<section className="flex flex-col gap-3">
				<h2 className="text-lg font-semibold">About You</h2>
				<label htmlFor="accent-background" className="text-sm font-medium">
					Accent background
				</label>
				<input
					id="accent-background"
					value={accentBackground}
					onChange={(event) => setAccentBackground(event.target.value)}
					className="rounded-md border px-3 py-2"
				/>

				<label htmlFor="training-history" className="text-sm font-medium">
					Vocal training history
				</label>
				<select
					id="training-history"
					value={trainingHistory}
					onChange={(event) =>
						setTrainingHistory(event.target.value as VocalTrainingHistory)
					}
					className="rounded-md border px-3 py-2"
				>
					<option value="none">None</option>
					<option value="amateur">Amateur</option>
					<option value="professional">Professional</option>
				</select>
			</section>

			<button
				type="button"
				onClick={() => void handleSubmit()}
				className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white"
			>
				Begin
			</button>
		</main>
	);
}
