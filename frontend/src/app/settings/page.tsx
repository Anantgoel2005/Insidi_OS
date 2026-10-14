"use client";

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Settings</h2>
        <p className="text-sm text-muted-foreground">
          Configure Insidi_OS
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6 space-y-3">
        <h3 className="text-sm font-semibold">Server-managed configuration</h3>
        <p className="text-sm text-muted-foreground">Credentials and LLM settings are deliberately configured through server environment variables, never saved in this browser. Offline analysis is always available; set `DEEPSEEK_API_KEY` and `LLM_PROVIDER=deepseek` on the server to enable low-cost enrichment.</p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6 space-y-4">
        <h3 className="text-sm font-semibold">System Architecture</h3>
        <div className="grid grid-cols-2 gap-3 text-xs">
          {[
            ["Honeypot Network", "172.28.0.0/16"],
            ["Honeypot Gateway", "172.28.0.1"],
            ["Redis Streams", "deception:*"],
            ["API Base", "/api/v1"],
            ["Dashboard", "localhost:3000"],
            ["Backend", "localhost:8000"],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between py-2 border-b border-border">
              <span className="text-muted-foreground">{label}</span>
              <span className="font-mono">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
