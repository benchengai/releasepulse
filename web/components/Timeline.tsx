"use client";

import { useEffect, useRef, useState } from "react";
import { Feature, Flag, Release, pct } from "@/lib/types";
import { StatusIcon } from "./Status";

const H = 250;
const M = { top: 34, right: 16, bottom: 46, left: 44 };

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(300);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(300, Math.round(e.contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

function niceMax(x: number) {
  const steps = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8, 1];
  return steps.find((s) => s >= x) ?? 1;
}

type Props = { feature: Feature; releases: Release[]; flags: Flag[] };

export function Timeline({ feature, releases, flags }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const s = feature.series;
  const innerW = width - M.left - M.right;
  const innerH = H - M.top - M.bottom;
  const yMax = niceMax(Math.max(0.05, ...s.flatMap((p) => [p.complaints.high, p.praise.high])) * 1.02);
  const step = innerW / s.length;
  const x = (i: number) => M.left + step * (i + 0.5);
  const y = (v: number) => M.top + innerH * (1 - v / yMax);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * yMax);

  const line = (key: "complaints" | "praise") => s.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p[key].rate)}`).join("");
  const band = (key: "complaints" | "praise") =>
    s.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p[key].high)}`).join("") +
    s.map((_, j) => { const i = s.length - 1 - j; return `L${x(i)},${y(s[i][key].low)}`; }).join("") + "Z";

  const flagAt = (release: string) => flags.filter((f) => f.release === release);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <div className="legend" aria-hidden="true">
        <span><i style={{ background: "var(--series-complaints)" }} />Complaints</span>
        <span><i style={{ background: "var(--series-praise)" }} />Praise</span>
        <span><i className="band" style={{ background: "var(--text-secondary)" }} />95% interval</span>
      </div>
      <svg width={width} height={H} role="img"
           aria-label={`${feature.name}: share of feedback items with complaints and praise, by release`}
           onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} stroke="var(--grid)" strokeWidth={1} />
            <text x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--axis-muted)"
                  className="num">{pct(t)}</text>
          </g>
        ))}
        <line x1={M.left} x2={width - M.right} y1={y(0)} y2={y(0)} stroke="var(--baseline)" strokeWidth={1} />
        {hover !== null && (
          <line x1={x(hover)} x2={x(hover)} y1={M.top - 4} y2={M.top + innerH} stroke="var(--baseline)" strokeWidth={1} />
        )}
        <path d={band("praise")} fill="var(--series-praise)" opacity={0.1} />
        <path d={band("complaints")} fill="var(--series-complaints)" opacity={0.1} />
        <path d={line("praise")} fill="none" stroke="var(--series-praise)" strokeWidth={2} strokeLinejoin="round"
              strokeLinecap="round" />
        <path d={line("complaints")} fill="none" stroke="var(--series-complaints)" strokeWidth={2}
              strokeLinejoin="round" strokeLinecap="round" />
        {s.map((p, i) => (
          <g key={p.release}>
            <circle cx={x(i)} cy={y(p.praise.rate)} r={4} fill="var(--series-praise)" stroke="var(--surface-1)" strokeWidth={2} />
            <circle cx={x(i)} cy={y(p.complaints.rate)} r={4} fill="var(--series-complaints)" stroke="var(--surface-1)"
                    strokeWidth={2} />
            <text x={x(i)} y={H - M.bottom + 18} textAnchor="middle" fontSize={12} fill="var(--text-secondary)">
              {p.release}
            </text>
            <text x={x(i)} y={H - M.bottom + 34} textAnchor="middle" fontSize={11} fill="var(--axis-muted)" className="num">
              n = {p.volume}
            </text>
            {flagAt(p.release).map((f, k) => (
              <g key={f.kind} transform={`translate(${x(i)}, ${12 + 14 * k})`}>
                <StatusIcon kind={f.kind === "regression" ? "regression" : "improved"} x={-38} y={-6} size={12} />
                <text x={-22} y={0} dy="0.32em" fontSize={11} fill="var(--text-secondary)">
                  {f.kind === "regression" ? "regression" : "improved"}
                </text>
              </g>
            ))}
            <rect x={x(i) - step / 2} y={M.top - 6} width={step} height={innerH + 6} fill="transparent" tabIndex={0}
                  aria-label={`${p.release}: complaints ${pct(p.complaints.rate, 1)}, praise ${pct(p.praise.rate, 1)}, ${p.volume} items`}
                  onMouseMove={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
          </g>
        ))}
      </svg>
      {hover !== null && (
        <div className="tooltip" style={{
          left: hover >= s.length / 2 ? Math.max(0, x(hover) - 272) : Math.min(x(hover) + 12, width - 260),
          top: M.top + 8, width: 260,
        }}>
          <div className="small muted">Release {s[hover].release} · {s[hover].volume} items</div>
          {(["complaints", "praise"] as const).map((k) => (
            <div key={k} style={{ marginTop: 4 }}>
              <div className="t-row">
                <span className="t-key" style={{ background: `var(--series-${k})` }} />
                <strong>{pct(s[hover][k].rate, 1)}</strong>
                <span className="muted">{k}</span>
              </div>
              <div className="muted small" style={{ paddingLeft: 20 }}>
                {s[hover][k].count} of {s[hover][k].n} items · 95% CI {pct(s[hover][k].low)}–{pct(s[hover][k].high)}
              </div>
            </div>
          ))}
        </div>
      )}
      <details className="small" style={{ marginTop: 6 }}>
        <summary>Show as table</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr><th>Release</th><th className="r">Items</th><th className="r">Complaints</th><th>95% CI</th>
                <th className="r">Praise</th><th>95% CI</th><th className="r">Requests</th></tr>
            </thead>
            <tbody>
              {s.map((p) => (
                <tr key={p.release} className="num">
                  <td>{p.release} <span className="muted">{releases.find((r) => r.version === p.release)?.date}</span></td>
                  <td className="r">{p.volume}</td>
                  <td className="r">{p.complaints.count} ({pct(p.complaints.rate, 1)})</td>
                  <td>{pct(p.complaints.low, 1)}–{pct(p.complaints.high, 1)}</td>
                  <td className="r">{p.praise.count} ({pct(p.praise.rate, 1)})</td>
                  <td>{pct(p.praise.low, 1)}–{pct(p.praise.high, 1)}</td>
                  <td className="r">{p.requests.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
