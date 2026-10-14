"use client";

import { useEffect, useState } from "react";
import { api, type Honeypot } from "@/lib/api";

export default function HoneypotsPage() {
  const [honeypots, setHoneypots] = useState<Honeypot[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("ssh");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = () => {
    api.honeypots.list({ limit: "100" }).then((r) => {
      setHoneypots(r.items);
      setLoading(false);
    }).catch((e) => { setLoading(false); setError(e instanceof Error ? e.message : "Unable to load local decoys."); });
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, []);

  const create = async () => {
    if (!newName.trim()) return;
    setCreating(true); setError("");
    try {
      await api.honeypots.create({
        name: newName,
        honeypot_type: newType as Honeypot["honeypot_type"],
      });
      setNewName("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Deployment failed.");
    } finally { setCreating(false); }
    load();
  };

  const remove = async (id: string) => {
    try {
      await api.honeypots.delete(id);
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to remove decoy."); }
    load();
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "running":
        return "bg-emerald-500";
      case "deploying":
        return "bg-sky-500 animate-pulse";
      case "paused":
        return "bg-amber-500";
      case "stopped":
        return "bg-muted-foreground";
      case "error":
        return "bg-red-500";
      default:
        return "bg-muted-foreground";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Honeypots</h2>
          <p className="text-sm text-muted-foreground">
            Deploy and manage deception services
          </p>
        </div>
      </div>

      {error && <p role="alert" className="rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-200">{error}</p>}

      <div className="bg-card border border-border rounded-lg p-4 flex gap-3 items-end">
        <div className="flex-1">
          <label className="text-xs text-muted-foreground block mb-1">Name</label>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="prod-web-server"
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
            onKeyDown={(e) => e.key === "Enter" && create()}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground block mb-1">Type</label>
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
          >
            <option value="ssh">SSH</option>
            <option value="http">HTTP</option>
            <option value="database">Database</option>
            <option value="smb">SMB</option>
          </select>
        </div>
        <button
          onClick={create}
          disabled={creating || !newName.trim()}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium hover:opacity-90 transition-opacity"
        >
          {creating ? "Deploying…" : "Deploy"}
        </button>
      </div>

      {loading ? (
        <div className="text-center text-muted-foreground py-12">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {honeypots.map((hp) => (
            <div
              key={hp.id}
              className="bg-card border border-border rounded-lg p-4 hover:border-primary/20 transition-colors"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${statusColor(hp.status)}`} />
                  <span className="font-semibold text-sm">{hp.name}</span>
                </div>
                <span className="text-[10px] uppercase bg-accent px-2 py-0.5 rounded text-muted-foreground">
                  {hp.honeypot_type}
                </span>
              </div>
              <div className="space-y-1 text-xs text-muted-foreground">
                <p className="mb-2">Status: {hp.status}{hp.status === "error" ? " — check backend deployment logs" : ""}</p>
                <div className="flex justify-between">
                  <span>IP</span>
                  <span className="font-mono">{hp.ip_address || "pending..."}</span>
                </div>
                <div className="flex justify-between">
                  <span>Ports</span>
                  <span className="font-mono">{hp.ports || "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span>Connections</span>
                  <span>{hp.total_connections}</span>
                </div>
                <div className="flex justify-between">
                  <span>Attackers</span>
                  <span>{hp.unique_attackers}</span>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-border flex gap-2">
                <button
                  onClick={() => remove(hp.id)}
                  className="text-xs text-red-400 hover:text-red-300 transition-colors"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
          {honeypots.length === 0 && (
            <div className="col-span-full text-center text-muted-foreground py-12 text-sm">
              No honeypots deployed. Create one above.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
