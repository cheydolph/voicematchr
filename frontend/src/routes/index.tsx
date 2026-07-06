import { ClientOnly, createFileRoute } from "@tanstack/react-router";

import Onboarding from "@/features/onboarding/Onboarding";

export const Route = createFileRoute("/")({ component: RouteComponent });

function RouteComponent() {
	return (
		<ClientOnly
			fallback={<p className="px-4 py-10 text-center text-sm">Loading...</p>}
		>
			<Onboarding />
		</ClientOnly>
	);
}
