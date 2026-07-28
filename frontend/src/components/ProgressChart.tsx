import {
	CategoryScale,
	Chart as ChartJS,
	Legend,
	LinearScale,
	LineElement,
	PointElement,
	Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";

// Chart.js is tree-shakeable: only registered elements exist at runtime.
// RadarChart.tsx registers the radial set; the line plot needs the cartesian set.
// Registration is idempotent, so the two components stay independent of each other.
ChartJS.register(
	CategoryScale,
	LinearScale,
	PointElement,
	LineElement,
	Tooltip,
	Legend,
);

interface ProgressChartProps {
	/** Cosine distances to the target prototype, oldest submission first. */
	distances: readonly number[];
}

export default function ProgressChart({
	distances,
}: Readonly<ProgressChartProps>) {
	if (distances.length === 0) {
		return (
			<p className="text-sm text-neutral-500">
				Your progress chart appears here once you have submitted a recording.
			</p>
		);
	}

	const data = {
		// The x-axis is submission ordinal, not wall-clock time: practice attempts are
		// unevenly spaced, and a time axis would compress a burst of attempts into an
		// unreadable cluster. Ordinal spacing is what the convergence trajectory in the
		// proposal actually measures.
		labels: distances.map((_, index) => String(index + 1)),
		datasets: [
			{
				label: "Distance to target voice",
				data: [...distances],
				borderColor: "#4f9dff",
				backgroundColor: "rgba(79, 157, 255, 0.25)",
				tension: 0.25,
			},
		],
	};

	const options = {
		scales: {
			x: { title: { display: true, text: "Submission" } },
			y: {
				min: 0,
				suggestedMax: 1,
				title: { display: true, text: "Cosine distance (lower is closer)" },
			},
		},
	};

	return <Line data={data} options={options} />;
}
