import type { AttackEvent } from "@/lib/api";

export function InsiderEvidence({ event }: { event: Pick<AttackEvent, "parsed_data"> }) {
  const context = event.parsed_data?.insider;
  if (!context) return null;
  return <div className="mt-2 space-y-1 text-xs">
    <p>Account {context.actor_id} · {context.role} · {context.resource}</p>
    {event.parsed_data?.simulated === true && <p className="text-muted-foreground">Synthetic demo telemetry</p>}
    {event.parsed_data?.insider_assessment?.findings.map((finding) => <p key={finding.rule} className="text-amber-400">{finding.reason}</p>)}
  </div>;
}
