"use client";
import { useEffect, useState } from "react";
import { api, type Investigation } from "@/lib/api";
import { InsiderEvidence } from "@/components/insider-evidence";

export default function InvestigationPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const [data, setData] = useState<Investigation | null>(null); const [error, setError] = useState("");
  useEffect(() => { params.then(({ sessionId }) => api.investigations.get(sessionId).then(setData).catch(() => setError("Investigation not found."))); }, [params]);
  if (error) return <p>{error}</p>; if (!data) return <p className="text-muted-foreground">Loading investigation…</p>;
  return <div className="max-w-3xl space-y-6"><div><p className="text-xs text-primary font-mono">{data.session_id}</p><h2 className="text-2xl font-bold">Attack investigation</h2><p className="text-sm text-muted-foreground">Source {data.source_ip}</p></div><div className="space-y-3">{data.events.map((event) => <div key={event.id} className="rounded border border-border bg-card p-4"><div className="flex justify-between"><b className="text-sm">{event.event_type.replace(/_/g, " ").toUpperCase()}</b><span className="text-xs text-muted-foreground">Score {event.threat_score}</span></div><p className="mt-2 font-mono text-xs text-muted-foreground">{event.raw_log}</p><InsiderEvidence event={event} />{event.mitre_technique && <p className="mt-2 text-xs text-amber-400">{event.mitre_technique} · {event.mitre_tactic}</p>}</div>)}</div></div>;
}
