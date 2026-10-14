"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, ArrowRight, Check, ChevronRight, Database, Eye, LockKeyhole, Maximize2, Pause, Play, Radio, ShieldCheck, ShieldAlert, SkipForward, Square, Terminal, Users } from "lucide-react";
import { api, type DemoScenario, type LiveRun, type LiveStep } from "@/lib/api";
import { brand } from "@/lib/brand";

const scenarios: { id: DemoScenario; title: string; subtitle: string; icon: typeof Users }[] = [
  { id: "employee-misuse", title: "Employee data misuse", subtitle: "Valid access → decoy discovery → blocked exfiltration", icon: Users },
  { id: "administrator-misuse", title: "Administrator abuse", subtitle: "Approved change → audit evasion → account containment", icon: LockKeyhole },
  { id: "credential-to-exfiltration", title: "External attack chain", subtitle: "Credential probing → command activity → canary trip", icon: Terminal },
];
const storageKey = "insider-live-showcase";
const time = (value: string) => new Date(value).toLocaleTimeString([], { hour12: false });
const button = "inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40";

export default function DemoPage() {
  const router = useRouter();
  const [scenario, setScenario] = useState<DemoScenario>("employee-misuse");
  const [pace, setPace] = useState(4);
  const [run, setRun] = useState<LiveRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(true);
  const [presenter, setPresenter] = useState(false);
  const [choosing, setChoosing] = useState(false);
  const [focus, setFocus] = useState(0);
  const [clock, setClock] = useState(Date.now());
  const lastCursor = useRef(-1);
  const mutation = useRef(0);

  const accept = useCallback((next: LiveRun) => {
    setRun(next); setScenario(next.scenario); setPace(next.interval_seconds); setConnected(true);
    if (lastCursor.current !== next.cursor) { setFocus(Math.max(0, next.cursor - 1)); lastCursor.current = next.cursor; }
    localStorage.setItem(storageKey, next.session_id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const session = localStorage.getItem(storageKey);
    if (!session) { setRestoring(false); return; }
    api.demo.live(session).then((value) => { if (!cancelled) accept(value); }).catch(() => { localStorage.removeItem(storageKey); }).finally(() => { if (!cancelled) setRestoring(false); });
    return () => { cancelled = true; };
  }, [accept]);

  useEffect(() => {
    if (!run || !["running", "paused"].includes(run.status)) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      const revision = mutation.current;
      try { const next = await api.demo.live(run!.session_id); if (!cancelled && revision === mutation.current) accept(next); }
      catch { if (!cancelled) setConnected(false); }
      if (!cancelled) timer = setTimeout(poll, 700);
    }
    timer = setTimeout(poll, 700);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [run?.session_id, run?.status, accept]);

  useEffect(() => { const timer = setInterval(() => setClock(Date.now()), 250); return () => clearInterval(timer); }, []);
  useEffect(() => {
    document.documentElement.dataset.presenter = String(presenter);
    return () => { delete document.documentElement.dataset.presenter; };
  }, [presenter]);

  async function start(autoplay = true) {
    mutation.current += 1;
    setBusy(true); setError("");
    try {
      if (run && ["running", "paused"].includes(run.status)) await api.demo.control(run.session_id, "stop", run.cursor);
      lastCursor.current = -1;
      accept(await api.demo.startLive(scenario, pace, autoplay));
      setChoosing(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to start the showcase."); }
    finally { mutation.current += 1; setBusy(false); }
  }

  async function control(action: "pause" | "resume" | "step" | "stop" | "speed", interval?: number) {
    if (!run) return;
    mutation.current += 1;
    setBusy(true); setError("");
    try { accept(await api.demo.control(run.session_id, action, run.cursor, interval)); }
    catch (e) { setError(e instanceof Error ? e.message : "Control failed. Refresh to reconnect to the run."); }
    finally { mutation.current += 1; setBusy(false); }
  }

  async function instant(id: DemoScenario) {
    setBusy(true); setError("");
    try { const result = await api.demo.run(id); router.push(`/investigations/${result.session_id}`); }
    catch (e) { setError(e instanceof Error ? e.message : "Scenario failed."); }
    finally { setBusy(false); }
  }

  const active = !!run && ["running", "paused"].includes(run.status);
  const current = run?.steps[focus];
  const latest = run?.steps.at(-1);
  const alertCount = new Set(run?.steps.flatMap((step) => step.alert ? [step.alert.id] : [])).size;
  const peak = Math.max(0, ...(run?.steps.map((step) => step.score) ?? []));
  const seconds = run ? Math.max(0, Math.ceil((new Date(run.next_step_at).getTime() - clock) / 1000)) : 0;
  const progress = run ? (run.cursor / run.total_steps) * 100 : 0;

  return <div className="showcase mx-auto max-w-[1600px] space-y-3 pb-6">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><div className="mb-1 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.24em] text-cyan-300"><Radio size={12} /> {brand.name} / Live Showcase</div><h2 className="text-2xl font-semibold tracking-tight text-slate-100">Live attack & response</h2>{!run && <p className="mt-2 text-sm text-slate-400">Watch legitimate access turn into misuse, then see the system detect and respond.</p>}</div>
      <div className="flex flex-wrap items-center gap-2">{run && !active && <button className={button} onClick={() => setChoosing(!choosing)}>Change scenario</button>}<span className="rounded-full border border-amber-300/20 bg-amber-300/5 px-3 py-1.5 text-[11px] font-medium text-amber-200">SYNTHETIC LAB</span><button className={button} onClick={() => setPresenter(!presenter)}><Maximize2 size={15} />{presenter ? "Exit presenter view" : "Presenter view"}</button></div>
    </header>

    {(!run || choosing) && <div className="grid gap-3 md:grid-cols-3" aria-label="Scenario selection">
      {scenarios.map((item) => <button key={item.id} aria-pressed={scenario === item.id} disabled={active || busy || restoring} onClick={() => setScenario(item.id)} className={`rounded-xl border p-4 text-left transition disabled:cursor-default ${scenario === item.id ? "border-cyan-400/50 bg-cyan-400/[.07]" : "border-white/10 bg-white/[.025] hover:border-white/25"}`}><div className="flex items-center gap-3"><item.icon size={18} className={scenario === item.id ? "text-cyan-300" : "text-slate-500"} /><span className="text-sm font-semibold text-slate-100">{item.title}</span>{scenario === item.id && <Check size={15} className="ml-auto text-cyan-300" />}</div><p className="mt-3 text-xs leading-relaxed text-slate-400">{item.subtitle}</p></button>)}
    </div>}

    <section className="rounded-xl border border-white/10 bg-[#111824] p-3">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {!active ? <><button disabled={busy || restoring} onClick={() => start()} className={`${button} !border-cyan-300/30 !bg-cyan-300 !text-slate-950 hover:!bg-cyan-200`}><Play size={15} fill="currentColor" />{run ? "Replay scenario" : "Start live demo"}</button><button disabled={busy || restoring} className={button} onClick={() => start(false)}><SkipForward size={15} />Start in step mode</button></> : <><button className={button} disabled={busy || !connected} onClick={() => control(run!.status === "running" ? "pause" : "resume")}>{run!.status === "running" ? <Pause size={15} /> : <Play size={15} />}{run!.status === "running" ? "Pause" : "Resume"}</button><button className={button} disabled={busy || run!.status !== "paused" || !connected} onClick={() => control("step")}><SkipForward size={15} />Next step</button><button className={button} disabled={busy} onClick={() => control("stop")}><Square size={13} />Stop</button></>}
          <label className="ml-2 flex items-center gap-2 text-xs text-slate-400">Pace<select aria-label="Demo pace" value={pace} disabled={busy} onChange={(e) => { const value = Number(e.target.value); if (active) control("speed", value); else setPace(value); }} className="rounded-lg border border-white/10 bg-[#0a101b] px-3 py-2 text-sm text-slate-200"><option value={2}>Fast · 2s</option><option value={4}>Showcase · 4s</option><option value={7}>Explain · 7s</option></select></label>
        </div>
        <div role="status" className="flex items-center gap-2 text-xs font-mono text-slate-400"><span className={`h-2 w-2 rounded-full ${!connected ? "bg-red-400" : run?.status === "running" ? "animate-pulse bg-emerald-400" : "bg-slate-500"}`} />{restoring ? "Reconnecting…" : !connected ? "Connection interrupted · retrying" : run?.status === "running" ? `LIVE · next action in ${seconds}s` : run?.status === "paused" ? "PAUSED · ready to explain" : run?.status === "completed" ? "COMPLETE · evidence retained" : run?.status === "stopped" ? "STOPPED · evidence retained" : "READY · select a scenario"}</div>
      </div>
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/5"><div className="h-full bg-cyan-300 transition-all duration-500" style={{ width: `${progress}%` }} /></div>
      <div className="mt-2 flex justify-between text-[11px] text-slate-500"><span>{run ? `Step ${run.cursor} of ${run.total_steps}` : "Events are generated progressively, never replayed from a canned log."}</span><span className="font-mono">{run?.session_id ?? "OFFLINE ANALYSIS · NO API COST"}</span></div>
    </section>

    {error && <p role="alert" className="rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-200">{error}</p>}

    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {[{ label: "EVENTS OBSERVED", value: run?.cursor ?? 0, detail: "Persisted in the real event pipeline", color: "text-slate-100" }, { label: "ALERTS RAISED", value: alertCount, detail: "Explainable backend findings", color: "text-amber-300" }, { label: "PEAK RISK SCORE", value: `${peak}/100`, detail: peak >= 85 ? "Critical activity detected" : peak >= 60 ? "High-risk activity detected" : "No high-risk activity yet", color: peak >= 85 ? "text-rose-300" : "text-slate-100" }, { label: "SANDBOX DENIALS", value: run?.sandbox.blocked_attempts ?? 0, detail: "Synthetic account / egress controls", color: "text-emerald-300" }].map((metric) => <div key={metric.label} className="rounded-xl border border-white/10 bg-white/[.025] px-4 py-2" title={metric.detail}><p className="text-[10px] tracking-widest text-slate-500">{metric.label}</p><p className={`mt-1 text-2xl font-semibold tabular-nums ${metric.color}`}>{metric.value}</p>{!run && <p className="text-[11px] text-slate-500">{metric.detail}</p>}</div>)}
    </div>

    <div className="grid items-center gap-3 rounded-xl border border-white/10 bg-[#0d1420] p-3 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
      <FlowNode icon={Users} label="Synthetic actor" detail={run?.steps[0]?.actor_id ?? (scenario === "employee-misuse" ? "demo-employee-001" : scenario === "administrator-misuse" ? "demo-admin-001" : "deploy")} color="text-rose-300" />
      <ArrowRight className="hidden text-slate-600 md:block" size={18} />
      <FlowNode icon={Database} label="Deception & telemetry" detail={run?.sandbox.decoy_isolated ? "Decoy isolated · evidence captured" : "Marked resources · policy context"} color="text-amber-300" />
      <ArrowRight className="hidden text-slate-600 md:block" size={18} />
      <FlowNode icon={ShieldCheck} label="Detection & response" detail={run?.sandbox.account_contained ? "Synthetic account contained" : run?.sandbox.privileges_locked ? "Unapproved privileges denied" : "Rules active · monitoring"} color="text-emerald-300" />
    </div>

    <div className="grid gap-4 lg:grid-cols-3">
      <Feed title="Attacker activity" subtitle="What the synthetic actor does" icon={Terminal} tone="rose" empty="Waiting for the first action…">
        {run?.steps.slice().reverse().map((step) => <FeedCard key={step.event_id} step={step} focus={focus} onSelect={setFocus} tone="rose"><p className="text-sm font-medium text-slate-200">{step.title}</p><p className="mt-2 break-words font-mono text-[11px] leading-relaxed text-slate-400">{step.raw_log}</p></FeedCard>)}
      </Feed>
      <Feed title="Detection engine" subtitle="Real scoring, rules & alert creation" icon={ShieldAlert} tone="amber" empty="Incoming telemetry will be assessed here.">
        {run?.steps.slice().reverse().map((step) => <FeedCard key={step.event_id} step={step} focus={focus} onSelect={setFocus} tone="amber"><div className="flex justify-between gap-2"><p className="text-sm font-medium text-slate-200">{step.alert ? `${step.alert.severity.toUpperCase()} alert` : "No alert required"}</p><span className={`text-xs font-mono ${step.score >= 60 ? "text-amber-300" : "text-slate-400"}`}>Risk {step.score}</span></div>{step.findings.map((finding) => <p key={finding.rule} className="mt-2 text-xs leading-relaxed text-slate-400">{finding.reason}</p>)}{!step.findings.length && <p className="mt-2 text-xs text-slate-400">{step.score < 60 ? "Activity below the alert threshold." : "Decoy event crossed the alert threshold."}</p>}{step.mitre_technique && <p className="mt-2 text-[10px] font-mono text-amber-300/80">{step.mitre_technique} · {step.mitre_tactic}</p>}</FeedCard>)}
      </Feed>
      <Feed title="System response" subtitle="Executed in the synthetic sandbox" icon={ShieldCheck} tone="emerald" empty="Response actions will appear after detection.">
        {run?.steps.slice().reverse().map((step) => <FeedCard key={step.event_id} step={step} focus={focus} onSelect={setFocus} tone="emerald"><p className="text-sm font-medium text-emerald-200">{step.outcome}</p>{step.responses.map((response) => <p key={response.code} className="mt-2 text-xs leading-relaxed text-slate-400"><Check className="mr-1 inline text-emerald-400" size={12} />{response.title}</p>)}<p className="mt-3 text-[10px] font-mono text-slate-500">Pipeline {step.processing_ms}ms · {time(step.response_at)}</p></FeedCard>)}
      </Feed>
    </div>

    <section className="rounded-xl border border-cyan-300/15 bg-cyan-300/[.035] p-5" aria-label="Stage explanation">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[.2em] text-cyan-300">{current ? `Stage ${current.index + 1} · the story behind the signal` : "The demonstration"}</p>
      <h3 className="text-lg font-medium text-slate-100">{current?.title ?? "Start with legitimate access. Follow the evidence."}</h3>
      <p className="mt-2 max-w-4xl text-sm leading-relaxed text-slate-400">{current?.narrative ?? "The scenario begins with normal activity, introduces suspicious behavior, and tests how the response changes the outcome of the next attempt. Pause at any stage to explain the finding to your audience."}</p>
      {current && <div className="mt-4 grid gap-3 md:grid-cols-2">{current.responses.map((response) => <div key={response.code} className="rounded-lg bg-black/15 p-3"><p className="text-xs font-medium text-emerald-200">{response.title}</p><p className="mt-1 text-xs leading-relaxed text-slate-400">{response.detail}</p></div>)}</div>}
      {run && <div className="mt-4 flex flex-wrap gap-2" aria-label="Attack stages">{run.plan.map((step, index) => <button key={index} disabled={index >= run.cursor} onClick={() => setFocus(index)} className={`rounded-md border px-2.5 py-1.5 text-[11px] disabled:opacity-30 ${focus === index && current ? "border-cyan-300/50 text-cyan-200" : "border-white/10 text-slate-400"}`} aria-label={`Stage ${index + 1}: ${step.title}`} title={step.title}>{index < run.cursor ? <Check className="mr-1 inline" size={10} /> : null}{index + 1}</button>)}</div>}
    </section>

    {run && <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/10 p-4"><div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-400"><span className={run.sandbox.account_contained ? "text-emerald-300" : ""}>Account: {run.sandbox.account_contained ? "contained" : "active"}</span><span>Egress: {run.sandbox.egress_blocked ? "blocked" : "open"}</span><span>Audit: {run.sandbox.audit_enabled ? "enabled" : "disabled"}</span><span>Privileges: {run.sandbox.privileges_locked ? "locked" : "baseline"}</span></div>{run.cursor > 0 && <Link className="inline-flex items-center gap-2 text-sm text-cyan-300 hover:text-cyan-200" href={`/investigations/${run.session_id}`}>Open investigation <ChevronRight size={15} /></Link>}</section>}

    {current && <details className="rounded-lg border border-white/10 p-3 text-xs text-slate-500"><summary className="cursor-pointer">Inspect recorded evidence</summary><pre className="mt-3 max-h-60 overflow-auto whitespace-pre-wrap break-all text-[11px]">{JSON.stringify(current, null, 2)}</pre></details>}
    <p className="flex items-start gap-2 text-[11px] leading-relaxed text-slate-500"><Eye size={14} className="mt-0.5 shrink-0" />Synthetic actors, decoy resources and sandbox response controls. Events and alerts are saved by the real backend. No real account, firewall, file or external destination is changed.</p>
    <details className="rounded-lg border border-white/10 p-3 text-xs text-slate-500"><summary className="cursor-pointer">Instant investigation generator</summary><div className="mt-3 flex flex-wrap gap-2">{scenarios.map((item) => <button key={item.id} disabled={busy || active} className={button} onClick={() => instant(item.id)}>{item.id === "credential-to-exfiltration" ? "Run safe scenario" : item.id === "employee-misuse" ? "Run employee data misuse" : "Run privileged administrator misuse"}</button>)}</div></details>
    {run?.status === "completed" && latest && <p className="text-xs text-slate-500">Walkthrough complete. Replay starts a fresh run; the previous evidence is retained.</p>}
  </div>;
}

function FlowNode({ icon: Icon, label, detail, color }: { icon: typeof Users; label: string; detail: string; color: string }) {
  return <div className="flex items-center gap-3"><div className={`rounded-lg border border-white/10 bg-white/5 p-2.5 ${color}`}><Icon size={18} /></div><div><p className="text-xs font-semibold text-slate-200">{label}</p><p className="mt-1 text-[11px] text-slate-500">{detail}</p></div></div>;
}

const tones = { rose: "text-rose-300 border-rose-300/20", amber: "text-amber-300 border-amber-300/20", emerald: "text-emerald-300 border-emerald-300/20" };
function Feed({ title, subtitle, icon: Icon, tone, empty, children }: { title: string; subtitle: string; icon: typeof Users; tone: keyof typeof tones; empty: string; children: React.ReactNode }) {
  return <section className="overflow-hidden rounded-xl border border-white/10 bg-[#101621]"><div className="border-b border-white/5 px-4 py-3"><h3 className={`flex items-center gap-2 text-sm font-semibold ${tones[tone]}`}><Icon size={16} />{title}</h3><p className="mt-1.5 text-[11px] text-slate-500">{subtitle}</p></div><div className="showcase-feed h-[250px] space-y-2 overflow-y-auto p-3" role="log" aria-label={title}>{Array.isArray(children) && children.length ? children : <div className="flex h-full flex-col items-center justify-center gap-3 text-center"><Activity size={28} className="text-slate-700" /><p className="max-w-48 text-xs leading-relaxed text-slate-500">{empty}</p></div>}</div></section>;
}

function FeedCard({ step, focus, onSelect, tone, children }: { step: LiveStep; focus: number; onSelect: (value: number) => void; tone: keyof typeof tones; children: React.ReactNode }) {
  return <button onClick={() => onSelect(step.index)} className={`showcase-arrival block w-full rounded-lg border p-3 text-left transition ${focus === step.index ? `${tones[tone]} bg-white/[.045]` : "border-white/5 bg-black/10 hover:bg-white/5"}`}><div className="mb-2 flex justify-between text-[10px] font-mono text-slate-500"><span>STEP {String(step.index + 1).padStart(2, "0")}</span><span>{time(step.timestamp)}</span></div>{children}</button>;
}
