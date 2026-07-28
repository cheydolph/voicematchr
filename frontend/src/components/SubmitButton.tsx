import { analyzeRecording } from "@/api/client";
import type { AnalyzeResponse } from "@/api/types";

interface SubmitButtonProps {
	file: File | null;
	sessionId: number;
	token: string;
	onResult: (result: AnalyzeResponse) => void;
	onError: (message: string) => void;
}

export default function SubmitButton({
	file,
	sessionId,
	token,
	onResult,
	onError,
}: Readonly<SubmitButtonProps>) {
	const handleSubmit = async () => {
		if (!file) return;
		try {
			const result = await analyzeRecording(file, sessionId, token);
			onResult(result);
		} catch (err) {
			onError(err instanceof Error ? err.message : "Analysis failed.");
		}
	};

	return (
		<button
			type="button"
			onClick={() => void handleSubmit()}
			disabled={!file}
			className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
		>
			Submit Recording
		</button>
	);
}
