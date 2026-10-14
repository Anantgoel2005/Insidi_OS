import { brand } from "@/lib/brand";

export function Brand({ large = false, subtitle = true }: { large?: boolean; subtitle?: boolean }) {
  return <div className="flex items-center gap-3">
    {/* The mark is a native vector asset; it stays sharp at presentation scale. */}
    <img src="/brand/insidi-mark.svg" alt="" width={large ? 52 : 38} height={large ? 52 : 38} />
    <div><p className={`font-mono font-semibold tracking-tight text-slate-100 ${large ? "text-3xl" : "text-lg"}`}>Insidi<span className="text-cyan-300">_OS</span></p>{subtitle && <p className="mt-0.5 text-[10px] tracking-wide text-slate-400">{brand.tagline}</p>}</div>
  </div>;
}
