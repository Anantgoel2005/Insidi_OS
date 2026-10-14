"use client";
import { useEffect, useState } from "react";
import { api, type Alert } from "@/lib/api";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]); const [loading, setLoading] = useState(true);
  const load = () => api.alerts.list({ limit: "100" }).then((r) => setAlerts(r.items)).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);
  const change = async (id: string, status: Alert["status"]) => { await api.alerts.update(id, { status }); load(); };
  return <div className="space-y-6"><div><h2 className="text-2xl font-bold">Alerts</h2><p className="text-sm text-muted-foreground">Triage high-confidence deception signals.</p></div>{loading ? <p>Loading…</p> : alerts.length === 0 ? <div className="rounded border border-border p-8 text-center text-muted-foreground">No open alerts. Run the Live Showcase to see the response workflow.</div> : <div className="space-y-3">{alerts.map((alert) => <article key={alert.id} className="rounded-lg border border-border bg-card p-4"><div className="flex justify-between gap-4"><div><span className={`text-xs uppercase font-semibold ${alert.severity === "critical" ? "text-red-400" : "text-amber-400"}`}>{alert.severity} · {alert.status}</span><h3 className="font-semibold mt-1">{alert.title}</h3><p className="text-sm text-muted-foreground mt-2 whitespace-pre-line">{alert.description}</p>{alert.recommendation && <p className="mt-3 rounded bg-accent p-2 text-sm"><b>Recommended:</b> {alert.recommendation}</p>}</div><div className="flex shrink-0 flex-col gap-2"><button onClick={() => change(alert.id, "acknowledged")} className="text-xs text-primary">Acknowledge</button><button onClick={() => change(alert.id, "resolved")} className="text-xs text-emerald-400">Resolve</button></div></div></article>)}</div>}</div>;
}
