import {
	Chart as ChartJS,
	Filler,
	Legend,
	LineElement,
	PointElement,
	RadialLinearScale,
	Tooltip,
} from "chart.js";
import { Radar } from "react-chartjs-2";

import type { AcousticFeatures } from "@/api/types";
import {
	DIMENSION_LABELS,
	DIMENSIONS,
	normalize,
} from "@/constants/dimensions";

ChartJS.register(
	RadialLinearScale,
	PointElement,
	LineElement,
	Filler,
	Tooltip,
	Legend,
);

interface RadarChartProps {
	learnerFeatures: AcousticFeatures;
	prototypeFeatures: AcousticFeatures;
}

export default function RadarChart({
	learnerFeatures,
	prototypeFeatures,
}: Readonly<RadarChartProps>) {
	const labels = DIMENSIONS.map((dimension) => DIMENSION_LABELS[dimension]);

	const data = {
		labels,
		datasets: [
			{
				label: "Your Voice",
				data: DIMENSIONS.map((dimension) =>
					normalize(dimension, learnerFeatures[dimension]),
				),
				borderColor: "#4f9dff",
				backgroundColor: "rgba(79, 157, 255, 0.25)",
			},
			{
				label: "Target Voice",
				data: DIMENSIONS.map((dimension) =>
					normalize(dimension, prototypeFeatures[dimension]),
				),
				borderColor: "#ff9d4f",
				backgroundColor: "rgba(255, 157, 79, 0.15)",
				borderDash: [6, 4],
			},
		],
	};

	const options = {
		scales: {
			r: { min: 0, max: 100, ticks: { display: false } },
		},
	};

	return <Radar data={data} options={options} />;
}
