export function SentimentBadge({ value }: { value: string }) {
  const colors: Record<string, string> = {
    positivo: "bg-emerald-100 text-emerald-800",
    neutral: "bg-stone-100 text-stone-600",
    negativo: "bg-orange-100 text-orange-800",
  };
  return <span className={`rounded-full px-2 py-0.5 ${colors[value] ?? ""}`}>{value}</span>;
}

export function RiskBadge({ value }: { value: string }) {
  const colors: Record<string, string> = {
    bajo: "bg-stone-100 text-stone-600",
    medio: "bg-amber-100 text-amber-800",
    alto: "bg-red-100 text-red-800 font-medium",
  };
  return <span className={`rounded-full px-2 py-0.5 ${colors[value] ?? ""}`}>riesgo {value}</span>;
}

export function StatusBadge({ value }: { value: string }) {
  const map: Record<string, [string, string]> = {
    draft: ["borrador", "bg-stone-100 text-stone-600"],
    requires_human: ["requiere humano", "bg-violet-100 text-violet-800"],
    approved: ["aprobada", "bg-emerald-100 text-emerald-800"],
    published: ["publicada", "bg-blue-100 text-blue-800"],
    rejected: ["rechazada", "bg-stone-200 text-stone-500"],
  };
  const [label, cls] = map[value] ?? [value, "bg-stone-100"];
  return <span className={`rounded-full px-2 py-0.5 ${cls}`}>{label}</span>;
}
