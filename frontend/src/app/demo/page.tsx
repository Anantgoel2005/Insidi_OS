"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const scenarios = [
  { id: "credential-to-exfiltration", title: "SSH and HTTP attack chain", description: "Credential probing, successful access, command activity, an exploit attempt and a canary callback." },
  { id: "employee-misuse", title: "Employee data misuse", description: "A legitimate login followed by out-of-scope decoy access, a bulk sensitive download and a transfer to an unapproved destination." },
  { id: "administrator-misuse", title: "Privileged administrator misuse", description: "Compare an approved privilege update with unapproved audit disabling, privilege changes and decoy credential export." },
];

export default function DemoPage() {
  const [running, setRunning] = useState(false); const [message, setMessage] = useState(""); const router = useRouter();
  async function run(scenario: string) { setRunning(true); setMessage(""); try { const result = await api.demo.run(scenario); setMessage(`${result.events_created} simulated events created. Opening the investigation…`); setTimeout(() => router.push(`/investigations/${result.session_id}`), 650); } catch { setMessage("Scenario failed. Confirm the API and database are healthy."); } finally { setRunning(false); } }
  return <div className="max-w-2xl space-y-6"><div><h2 className="text-2xl font-bold">Demo Lab</h2><p className="text-sm text-muted-foreground">Deterministic simulations using synthetic accounts, resources and TEST-NET addresses.</p></div>{scenarios.map((scenario) => <section key={scenario.id} className="rounded-xl border border-primary/30 bg-card p-6"><h3 className="text-xl font-semibold">{scenario.title}</h3><p className="mt-2 text-sm text-muted-foreground">{scenario.description}</p><button onClick={() => run(scenario.id)} disabled={running} className="mt-5 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">{running ? "Running scenario…" : scenario.id === "credential-to-exfiltration" ? "Run safe scenario" : `Run ${scenario.title.toLowerCase()}`}</button></section>)}{message && <p role="status" className="text-sm text-emerald-400">{message}</p>}</div>;
}
