"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Brand } from "@/components/brand";
import { Activity, Bell, FlaskConical, Gauge, Radio, Server, Settings, ShieldCheck } from "lucide-react";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const router = useRouter(); const [ready, setReady] = useState(pathname === "/login");
  useEffect(() => { if (pathname === "/login") { setReady(true); return; } api.auth.me().then(() => setReady(true)).catch(() => router.replace("/login")); }, [pathname, router]);
  if (!ready) return <main className="min-h-screen grid place-items-center"><div className="space-y-5"><Brand large /><p className="text-center text-sm text-muted-foreground">Checking secure session…</p></div></main>;
  if (pathname === "/login") return <>{children}</>;
  const links = [
    { href: "/", label: "Overview", icon: Gauge },
    { href: "/demo", label: "Live Showcase", icon: FlaskConical },
    { href: "/events", label: "Events", icon: Activity },
    { href: "/alerts", label: "Alerts", icon: Bell },
    { href: "/honeypots", label: "Local Decoys", icon: Server },
    { href: "/canaries", label: "Canaries", icon: Radio },
    { href: "/settings", label: "Settings", icon: Settings },
  ];
  return <div className="flex h-screen"><aside className="w-56 border-r border-border bg-card flex flex-col p-4 shrink-0"><div className="mb-8 mt-1"><Brand /></div><p className="mb-3 px-3 text-[10px] uppercase tracking-[.2em] text-slate-500">Analyst workspace</p><nav className="flex flex-col gap-1">{links.map(({ href, label, icon: Icon }) => <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined} className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${pathname === href ? "bg-cyan-300/10 text-cyan-200" : "text-muted-foreground hover:bg-accent hover:text-foreground"}`}><Icon size={16} />{label}</Link>)}</nav><div className="mt-auto rounded-lg border border-emerald-300/15 bg-emerald-300/[.03] p-3"><p className="flex items-center gap-2 text-xs text-emerald-300"><ShieldCheck size={14} />Protected analyst session</p><p className="mt-1 text-[10px] text-slate-400">Insider-threat detection lab</p></div></aside><main className="flex-1 overflow-auto p-6">{children}</main></div>;
}
