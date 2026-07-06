import { useRef, useState } from "react";

interface RecorderProps {
	onRecordingReady: (file: File, previewUrl: string) => void;
}

const PREFERRED_MIME_TYPES = [
	"audio/wav",
	"audio/webm;codecs=opus",
	"audio/webm",
	"audio/ogg",
];

function pickSupportedMimeType(): string {
	const supported = PREFERRED_MIME_TYPES.find((type) =>
		MediaRecorder.isTypeSupported(type),
	);
	if (!supported) {
		throw new Error(
			"No supported audio recording format found in this browser.",
		);
	}
	return supported;
}

function extensionForMimeType(mimeType: string): string {
	if (mimeType.startsWith("audio/wav")) return "wav";
	if (mimeType.startsWith("audio/webm")) return "webm";
	if (mimeType.startsWith("audio/ogg")) return "ogg";
	return "bin";
}

export default function Recorder({
	onRecordingReady,
}: Readonly<RecorderProps>) {
	const [isRecording, setIsRecording] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const mediaRecorderRef = useRef<MediaRecorder | null>(null);
	const chunksRef = useRef<Blob[]>([]);
	const canvasRef = useRef<HTMLCanvasElement | null>(null);
	const analyserRef = useRef<AnalyserNode | null>(null);
	const audioContextRef = useRef<AudioContext | null>(null);
	const animationFrameRef = useRef<number | null>(null);

	const drawWaveform = () => {
		const canvas = canvasRef.current;
		const analyser = analyserRef.current;
		if (!canvas || !analyser) return;
		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		const bufferLength = analyser.fftSize;
		const dataArray = new Uint8Array(bufferLength);

		const render = () => {
			analyser.getByteTimeDomainData(dataArray);
			ctx.fillStyle = "#111";
			ctx.fillRect(0, 0, canvas.width, canvas.height);
			ctx.lineWidth = 2;
			ctx.strokeStyle = "#4f9dff";
			ctx.beginPath();

			const sliceWidth = canvas.width / bufferLength;
			let x = 0;
			for (let i = 0; i < bufferLength; i += 1) {
				const value = dataArray[i] / 128.0;
				const y = (value * canvas.height) / 2;
				if (i === 0) {
					ctx.moveTo(x, y);
				} else {
					ctx.lineTo(x, y);
				}
				x += sliceWidth;
			}
			ctx.stroke();
			animationFrameRef.current = requestAnimationFrame(render);
		};
		render();
	};

	const stopTracksAndAnimation = (
		stream: MediaStream,
		audioContext: AudioContext,
	) => {
		stream.getTracks().forEach((track) => {
			track.stop();
		});
		void audioContext.close();
		if (animationFrameRef.current !== null) {
			cancelAnimationFrame(animationFrameRef.current);
			animationFrameRef.current = null;
		}
	};

	const startRecording = async () => {
		setError(null);
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			const audioContext = new AudioContext();
			const source = audioContext.createMediaStreamSource(stream);
			const analyser = audioContext.createAnalyser();
			source.connect(analyser);
			audioContextRef.current = audioContext;
			analyserRef.current = analyser;

			const mimeType = pickSupportedMimeType();
			chunksRef.current = [];
			const recorder = new MediaRecorder(stream, { mimeType });

			recorder.ondataavailable = (event) => {
				if (event.data.size > 0) chunksRef.current.push(event.data);
			};

			recorder.onstop = () => {
				const blob = new Blob(chunksRef.current, { type: mimeType });
				const extension = extensionForMimeType(mimeType);
				const file = new File([blob], `recording.${extension}`, {
					type: mimeType,
				});
				onRecordingReady(file, URL.createObjectURL(blob));
				stopTracksAndAnimation(stream, audioContext);
			};

			mediaRecorderRef.current = recorder;
			recorder.start();
			setIsRecording(true);
			drawWaveform();
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Unable to start recording.",
			);
		}
	};

	const stopRecording = () => {
		mediaRecorderRef.current?.stop();
		setIsRecording(false);
	};

	return (
		<div className="flex flex-col gap-3">
			<canvas
				ref={canvasRef}
				width={400}
				height={100}
				className="rounded-md bg-neutral-900"
			/>
			<div>
				{isRecording ? (
					<button
						type="button"
						onClick={stopRecording}
						className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white"
					>
						Stop Recording
					</button>
				) : (
					<button
						type="button"
						onClick={() => void startRecording()}
						className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white"
					>
						Start Recording
					</button>
				)}
			</div>
			{error && (
				<p role="alert" className="text-sm text-red-600">
					{error}
				</p>
			)}
			<p className="text-xs text-neutral-500">
				Recordings are captured in whatever format this browser&apos;s
				MediaRecorder supports (commonly WebM/Opus, not WAV). The backend&apos;s
				decoding step must accept that format, or the upload option below should
				be used with a pre-recorded WAV file.
			</p>
		</div>
	);
}
