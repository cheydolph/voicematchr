import { ClientOnly, createFileRoute } from "@tanstack/react-router";

import Session from "@/features/session/Session";

export const Route = createFileRoute("/session")({ component: RouteComponent });

function RouteComponent() {
	return (
		<ClientOnly
			fallback={<p className="px-4 py-10 text-center text-sm">Loading...</p>}
		>
			<Session />
		</ClientOnly>
	);
}
