"use client";

import { useEffect, useState } from "react";
import { api, type AttackEvent } from "@/lib/api";
import { InsiderEvidence } from "@/components/insider-evidence";

export default function EventsPage() {
  const [events, setEvents] = useState<AttackEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [ipFilter, setIpFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("");
  const [showEngagement, setShowEngagement] = useState<string | null>(null);

  const load = () => {
    const params: Record<string, string> = { limit: "200" };
    if (filter !== "all") params.event_type = filter;
    if (ipFilter) params.source_ip = ipFilter;
    if (actorFilter) params.actor_id = actorFilter;
    api.events.list(params).then((r) => {
      setEvents(r.items);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 6000);
    return () => clearInterval(interval);
  }, [filter, ipFilter, actorFilter]);

  const decideEngagement = async (honeypotId: string) => {
    setShowEngagement(honeypotId);
    try {
      const result = await api.engagement.decide(honeypotId);
      alert(`${result.action}: ${result.message}`);
    } catch {
      alert("Engagement decision failed");
    }
    setShowEngagement(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Attack Events</h2>
        <p className="text-sm text-muted-foreground">
          Decoy activity and insider findings across accounts and devices
        </p>
      </div>

      <div className="flex gap-3 items-center flex-wrap">
        <input value={actorFilter} onChange={(e) => setActorFilter(e.target.value)} aria-label="Filter by account ID" placeholder="Filter by account ID..." className="bg-card border border-border rounded-md px-3 py-2 text-sm w-56" />
        <input
          type="text"
          value={ipFilter}
          onChange={(e) => setIpFilter(e.target.value)}
          placeholder="Filter by IP..."
          className="bg-card border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary w-48"
        />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="bg-card border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
        >
          <option value="all">All Events</option>
          <option value="connection">Connection</option>
          <option value="login_attempt">Login Attempt</option>
          <option value="login_success">Login Success</option>
          <option value="command">Command</option>
          <option value="file_download">File Download</option>
          <option value="file_upload">File Upload</option>
          <option value="exploit_attempt">Exploit Attempt</option>
          <option value="canary_trip">Canary Trip</option>
        </select>
        <span className="text-xs text-muted-foreground">
          {events.length} events
        </span>
      </div>

      {loading ? (
        <div className="text-center text-muted-foreground py-12">Loading...</div>
      ) : (
        <div className="space-y-2">
          {events.map((event) => (
            <div
              key={event.id}
              className="bg-card border border-border rounded-lg p-4 hover:border-primary/20 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span
                      className={`text-xs font-mono px-1.5 py-0.5 rounded ${
                        event.threat_score >= 70
                          ? "bg-red-500/10 text-red-400"
                          : event.threat_score >= 40
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-sky-500/10 text-sky-400"
                      }`}
                    >
                      {event.event_type.replace(/_/g, " ").toUpperCase()}
                    </span>
                    <span className="text-xs font-mono text-muted-foreground">
                      {event.source_ip}:{event.source_port || "?"}
                    </span>
                    {event.username && (
                      <span className="text-xs text-muted-foreground">
                        user: {event.username}
                      </span>
                    )}
                    {event.mitre_technique && (
                      <span className="text-[10px] font-mono bg-amber-500/10 text-amber-400 px-1.5 py-0.5 rounded">
                        {event.mitre_technique}
                      </span>
                    )}
                    {event.session_id && (
                      <span className="text-[10px] font-mono text-muted-foreground">
                        session: {event.session_id.slice(0, 12)}
                      </span>
                    )}
                  </div>
                  {event.raw_log && (
                    <pre className="text-xs text-muted-foreground mt-2 p-2 bg-background rounded border border-border overflow-x-auto max-h-32">
                      {event.raw_log}
                    </pre>
                  )}
                  <InsiderEvidence event={event} />
                  {event.session_id && <a className="mt-2 inline-block text-xs text-primary hover:underline" href={`/investigations/${encodeURIComponent(event.session_id)}`}>Open investigation</a>}
                </div>
                <div className="shrink-0 flex flex-col items-end gap-1">
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(event.timestamp).toLocaleString()}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    score: {event.threat_score}
                  </span>
                  {event.honeypot_id && (
                    <button
                      onClick={() => decideEngagement(event.honeypot_id!)}
                      disabled={showEngagement === event.honeypot_id}
                      className="text-[10px] text-primary hover:underline disabled:opacity-50"
                    >
                      {showEngagement === event.honeypot_id
                        ? "Analyzing..."
                        : "AI Engage"}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
          {events.length === 0 && (
            <div className="text-center text-muted-foreground py-12 text-sm">
              No events match these filters. Run a demo or ingest trusted collector telemetry.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
