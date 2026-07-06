import type { ChangeEvent } from "react";

interface UploadPanelProps {
	onFileSelected: (file: File, previewUrl: string) => void;
}

export default function UploadPanel({
	onFileSelected,
}: Readonly<UploadPanelProps>) {
	const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		if (file) onFileSelected(file, URL.createObjectURL(file));
	};

	return (
		<div className="flex flex-col gap-2">
			<label htmlFor="wav-upload" className="text-sm font-medium">
				Or upload a WAV file:
			</label>
			<input
				id="wav-upload"
				type="file"
				accept="audio/wav"
				onChange={handleChange}
			/>
		</div>
	);
}
