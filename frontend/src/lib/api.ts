const API_BASE = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: optHeaders, ...rest } = options || {};
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(options?.method && options.method !== "GET" ? { "X-CSRF-Token": getCookie("csrf_token") || "" } : {}),
      ...optHeaders,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function getCookie(name: string): string | undefined {
  return document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=").slice(1).join("=");
}

export interface DashboardStats {
  active_honeypots: number;
  total_honeypots: number;
  active_canaries: number;
  tripped_canaries: number;
  total_events: number;
  events_last_24h: number;
  open_alerts: number;
  critical_alerts: number;
  unique_attackers_24h: number;
  deployment_mode: string;
  demo_mode: boolean;
  local_decoys_enabled: boolean;
}

export interface Honeypot {
  id: string;
  name: string;
  honeypot_type: "ssh" | "http" | "database" | "smb";
  status: "deploying" | "running" | "paused" | "stopped" | "error";
  container_id: string | null;
  ip_address: string | null;
  ports: string | null;
  total_connections: number;
  total_commands: number;
  unique_attackers: number;
  active_connections: number | null;
  connection_tracking: "live" | "unavailable" | "disabled" | "inactive";
  created_at: string;
  updated_at: string;
}

export interface Canary {
  id: string;
  canary_type: "url" | "dns" | "aws_key" | "document";
  status: "active" | "tripped" | "revoked" | "expired";
  token_value: string;
  token_metadata: Record<string, unknown> | null;
  planted_location: string | null;
  tripped_at: string | null;
  trip_source_ip: string | null;
  trip_user_agent: string | null;
  trip_extra: Record<string, unknown> | null;
  created_at: string;
  expires_at: string | null;
  callback_url: string | null;
}

export interface Alert {
  id: string;
  title: string;
  description: string | null;
  severity: "low" | "medium" | "high" | "critical";
  status: "new" | "acknowledged" | "investigating" | "resolved" | "false_positive";
  recommendation: string | null;
  ai_analysis: string | null;
  assigned_to: string | null;
  created_at: string;
}

export interface Investigation {
  session_id: string;
  source_ip: string;
  alert_ids: string[];
  events: (Pick<AttackEvent, "id" | "event_type" | "source_ip" | "username" | "raw_log" | "parsed_data" | "mitre_technique" | "mitre_tactic" | "threat_score" | "timestamp"> & { simulated: boolean })[];
}

export interface AttackEvent {
  id: string;
  honeypot_id: string | null;
  canary_id: string | null;
  event_type: string;
  source_ip: string;
  source_port: number | null;
  username: string | null;
  raw_log: string | null;
  parsed_data: (Record<string, unknown> & {
    insider?: { actor_id: string; role: string; resource: string };
    insider_assessment?: { score: number; findings: { rule: string; reason: string }[] };
  }) | null;
  mitre_technique: string | null;
  mitre_tactic: string | null;
  threat_score: number;
  session_id: string | null;
  timestamp: string;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}

export type DemoScenario = "employee-misuse" | "administrator-misuse" | "credential-to-exfiltration";
export interface LiveStep {
  index: number; title: string; narrative: string; event_id: string; event_type: string;
  raw_log: string; actor_id: string; timestamp: string; score: number;
  mitre_technique: string | null; mitre_tactic: string | null;
  findings: { rule: string; reason: string; score: number }[];
  alert: { id: string; title: string; severity: string; recommendation: string } | null;
  responses: { code: string; title: string; detail: string; scope: string }[];
  outcome: string; response_at: string; processing_ms: number; sandbox: LiveRun["sandbox"];
}
export interface LiveRun {
  session_id: string; scenario: DemoScenario; status: "running" | "paused" | "completed" | "stopped";
  cursor: number; total_steps: number; interval_seconds: number;
  plan: { title: string; narrative: string }[]; steps: LiveStep[];
  sandbox: { account_contained: boolean; egress_blocked: boolean; audit_enabled: boolean; privileges_locked: boolean; decoy_isolated: boolean; blocked_attempts: number };
  created_at: string; next_step_at: string;
}

export const api = {
  auth: {
    login: (username: string, password: string) => request<{ username: string }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
    logout: () => request<void>("/auth/logout", { method: "POST" }),
    me: () => request<{ username: string }>("/auth/me"),
  },
  dashboard: {
    stats: () => request<DashboardStats>("/dashboard/stats"),
  },
  honeypots: {
    list: (params?: Record<string, string>) => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      return request<ListResponse<Honeypot>>(`/honeypots${qs}`);
    },
    get: (id: string) => request<Honeypot>(`/honeypots/${id}`),
    create: (data: Partial<Honeypot>) =>
      request<Honeypot>("/honeypots", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/honeypots/${id}`, { method: "DELETE" }),
  },
  canaries: {
    list: (params?: Record<string, string>) => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      return request<ListResponse<Canary>>(`/canaries${qs}`);
    },
    generate: (data: { canary_type: string; count: number; planted_location?: string }) =>
      request<Canary[]>("/canaries/generate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/canaries/${id}`, { method: "DELETE" }),
  },
  alerts: {
    list: (params?: Record<string, string>) => request<ListResponse<Alert>>(`/alerts${params ? "?" + new URLSearchParams(params) : ""}`),
    update: (id: string, data: { status?: Alert["status"] }) => request<Alert>(`/alerts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    analyze: (id: string) => request<Alert>(`/alerts/${id}/analyze`, { method: "POST" }),
  },
  events: {
    list: (params?: Record<string, string>) => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      return request<ListResponse<AttackEvent>>(`/events${qs}`);
    },
    session: (sessionId: string) =>
      request<AttackEvent[]>(`/events/session/${sessionId}`),
  },
  engagement: {
    decide: (honeypotId: string) =>
      request<{ success: boolean; action: string; message: string }>(
        `/engagement/decide/${honeypotId}`,
        { method: "POST" }
      ),
  },
  investigations: { get: (sessionId: string) => request<Investigation>(`/investigations/${sessionId}`) },
  demo: {
    run: (scenario = "credential-to-exfiltration") => request<{ session_id: string; events_created: number; message: string }>("/demo/run", { method: "POST", body: JSON.stringify({ scenario }) }),
    startLive: (scenario: DemoScenario, interval_seconds: number, autoplay = true) => request<LiveRun>("/demo/live", { method: "POST", body: JSON.stringify({ scenario, interval_seconds, autoplay }) }),
    live: (session: string) => request<LiveRun>(`/demo/live/${encodeURIComponent(session)}`),
    control: (session: string, action: "pause" | "resume" | "step" | "stop" | "speed", expected_cursor: number, interval_seconds?: number) => request<LiveRun>(`/demo/live/${encodeURIComponent(session)}/control`, { method: "POST", body: JSON.stringify({ action, expected_cursor, interval_seconds }) }),
  },
};
