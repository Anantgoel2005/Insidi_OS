"use client";

import { useEffect, useState } from "react";
import { api, type DashboardStats, type AttackEvent } from "@/lib/api";
import Link from "next/link";
import {
  Shield,
  Radio,
  AlertTriangle,
  Activity,
  Users,
} from "lucide-react";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [events, setEvents] = useState<AttackEvent[]>([]);

  useEffect(() => {
    const fetchData = () => {
      api.dashboard.stats().then(setStats).catch(() => {});
      api.events.list({ limit: "20" }).then((r) => setEvents(r.items)).catch(() => {});
    };
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const cards = [
    {
      label: "Active Honeypots",
      value: stats?.active_honeypots ?? 0,
      sub: `${stats?.total_honeypots ?? 0} total`,
      icon: Shield,
      color: "text-emerald-400",
    },
    {
      label: "Active Canaries",
      value: stats?.active_canaries ?? 0,
      sub: `${stats?.tripped_canaries ?? 0} tripped`,
      icon: Radio,
      color: "text-amber-400",
    },
    {
      label: "Events (24h)",
      value: stats?.events_last_24h ?? 0,
      sub: `${stats?.total_events ?? 0} total`,
      icon: Activity,
      color: "text-sky-400",
    },
    {
      label: "Open Alerts",
      value: stats?.open_alerts ?? 0,
      sub: `${stats?.critical_alerts ?? 0} critical`,
      icon: AlertTriangle,
      color: stats?.critical_alerts ? "text-red-400" : "text-amber-400",
    },
    {
      label: "Unique Attackers",
      value: stats?.unique_attackers_24h ?? 0,
      sub: "past 24 hours",
      icon: Users,
      color: "text-violet-400",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Insidi_OS Overview</h2>
        <p className="text-sm text-muted-foreground">
          Identity-aware findings, deception telemetry and insider-threat investigations
        </p>
      </div>

      <Link href="/demo" className="flex items-center justify-between gap-4 rounded-xl border border-cyan-300/25 bg-cyan-300/[.04] p-4"><div><p className="text-sm font-semibold text-cyan-200">Open the live showcase</p><p className="mt-1 text-xs text-muted-foreground">Follow an insider attack from valid access to detection and a sandbox response.</p></div><span className="text-sm text-cyan-300">Launch →</span></Link>

      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded bg-emerald-500/10 px-2 py-1 text-emerald-400">{stats?.deployment_mode || "checking"} control plane</span>
        <span className="rounded bg-accent px-2 py-1 text-muted-foreground">{stats?.demo_mode ? "safe demo mode enabled" : "demo mode disabled"}</span>
        <span className="rounded bg-accent px-2 py-1 text-muted-foreground">{stats?.local_decoys_enabled ? "local decoys enabled" : "no Docker decoys on this host"}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className="bg-card border border-border rounded-lg p-4 hover:border-primary/30 transition-colors"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">
                {card.label}
              </span>
              <card.icon className={`h-4 w-4 ${card.color}`} />
            </div>
            <div className="text-2xl font-bold">{card.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{card.sub}</div>
          </div>
        ))}
      </div>

      <div className="bg-card border border-border rounded-lg">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider">
            Live Attack Feed
          </h3>
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
        </div>
        <div className="divide-y divide-border max-h-[480px] overflow-auto">
          {events.length === 0 && (
            <div className="p-8 text-center text-muted-foreground text-sm">
              No events captured yet. Start a live showcase or ingest trusted telemetry.
            </div>
          )}
          {events.map((event) => (
            <div
              key={event.id}
              className="px-4 py-3 hover:bg-accent/50 transition-colors flex items-start gap-3"
            >
              <span
                className={`mt-0.5 h-2 w-2 rounded-full shrink-0 ${
                  event.threat_score >= 70
                    ? "bg-red-500"
                    : event.threat_score >= 40
                    ? "bg-amber-500"
                    : "bg-sky-500"
                }`}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                    {event.event_type.replace(/_/g, " ").toUpperCase()}
                  </span>
                  <span className="text-xs text-muted-foreground font-mono">
                    {event.source_ip}
                  </span>
                  {event.mitre_technique && (
                    <span className="text-[10px] text-amber-400 font-mono bg-amber-400/10 px-1.5 py-0.5 rounded">
                      {event.mitre_technique}
                    </span>
                  )}
                  {event.threat_score > 0 && (
                    <span className="text-[10px] text-muted-foreground">
                      score: {event.threat_score}
                    </span>
                  )}
                </div>
                {event.raw_log && (
                  <p className="text-xs text-muted-foreground mt-1 truncate">
                    {event.raw_log}
                  </p>
                )}
              </div>
              <span className="text-[10px] text-muted-foreground shrink-0">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
