"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Brand } from "@/components/brand";
import { Activity, ArrowRight, Fingerprint, LockKeyhole, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter(); const [username, setUsername] = useState("admin"); const [password, setPassword] = useState(""); const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try { await api.auth.login(username, password); router.replace("/"); } catch { setError("Invalid credentials or server configuration."); } finally { setBusy(false); }
  }
  return <main className="grid min-h-screen place-items-center bg-background p-6">
    <div className="grid w-full max-w-5xl overflow-hidden rounded-2xl border border-white/10 bg-card shadow-2xl md:grid-cols-[1.2fr_1fr]">
      <section className="relative overflow-hidden border-b border-white/10 bg-[radial-gradient(ellipse_at_top_left,rgba(34,211,238,.12),transparent_65%)] p-8 md:border-b-0 md:border-r md:p-12">
        <Brand large />
        <p className="mt-12 text-[10px] font-semibold uppercase tracking-[.25em] text-cyan-300">Insider-threat detection lab</p>
        <h2 className="mt-4 max-w-sm text-3xl font-semibold leading-tight tracking-tight text-slate-100">See the signal<br />behind the access.</h2>
        <p className="mt-5 max-w-sm text-sm leading-relaxed text-slate-400">Follow account activity from legitimate access to suspicious behavior, explainable findings and a visible response.</p>
        <div className="mt-8 space-y-3 text-xs text-slate-300">{[{ icon: Fingerprint, text: "Identity-aware investigations" }, { icon: Activity, text: "Live attack and response walkthroughs" }, { icon: ShieldCheck, text: "Controlled, synthetic containment" }].map(({ icon: Icon, text }) => <p key={text} className="flex items-center gap-3"><Icon size={16} className="text-cyan-300" />{text}</p>)}</div>
        <p className="mt-12 font-mono text-[10px] text-slate-500">INSIDI_OS // ANALYST WORKSPACE</p>
      </section>
      <form onSubmit={submit} className="flex flex-col justify-center gap-5 p-8 md:p-10">
        <div><LockKeyhole size={20} className="mb-4 text-cyan-300" /><h1 className="text-2xl font-semibold text-slate-100">Sign in to Insidi_OS</h1><p className="mt-2 text-sm text-muted-foreground">Your analyst session starts here.</p></div>
        <label className="block text-sm text-slate-300">Username<input autoComplete="username" required value={username} onChange={(e) => setUsername(e.target.value)} className="mt-2 w-full rounded-lg border border-border bg-background p-3 outline-none transition focus:border-cyan-300/60" /></label>
        <label className="block text-sm text-slate-300">Password<input autoComplete="current-password" required type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-2 w-full rounded-lg border border-border bg-background p-3 outline-none transition focus:border-cyan-300/60" /></label>
        {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
        <button disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-300 p-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-50">{busy ? "Signing in…" : "Sign in"}<ArrowRight size={16} /></button>
        <p className="text-center text-[11px] text-slate-500">Protected console · synthetic lab demonstrations</p>
      </form>
    </div>
  </main>;
}
