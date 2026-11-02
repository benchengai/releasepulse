// Status is never colour alone: every status carries an icon shape and a text label.

type Kind = "regression" | "improved" | "thin evidence" | "ongoing";

const COLOR: Record<Kind, string> = {
  regression: "var(--status-critical)",
  improved: "var(--status-good)",
  "thin evidence": "var(--axis-muted)",
  ongoing: "var(--text-secondary)",
};

export function StatusIcon({ kind, x = 0, y = 0, size = 12 }: { kind: Kind; x?: number; y?: number; size?: number }) {
  const c = COLOR[kind];
  return (
    <svg x={x} y={y} width={size} height={size} viewBox="0 0 12 12" aria-hidden="true">
      {kind === "regression" && <path d="M6 1 L11 10 L1 10 Z" fill={c} />}
      {kind === "improved" && <path d="M6 11 L11 2 L1 2 Z" fill={c} />}
      {kind === "thin evidence" && <circle cx={6} cy={6} r={4} fill="none" stroke={c} strokeWidth={1.5} />}
      {kind === "ongoing" && <circle cx={6} cy={6} r={3} fill={c} />}
    </svg>
  );
}

export function StatusChip({ kind, since }: { kind: Kind; since?: string | null }) {
  const label = kind === "regression" ? `regression in ${since}` : kind === "improved" ? `improved in ${since}` : kind;
  return (
    <span className="chip">
      <StatusIcon kind={kind} />
      {label}
    </span>
  );
}
