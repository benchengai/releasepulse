"use client";

import { Fragment, useState } from "react";
import { PriorityTable as Table, PriorityRow, pct, pts, sourceLabel } from "@/lib/types";
import { StatusChip } from "./Status";

const IW = 150;

function Interval({ row, max, which = "complaints" }: { row: PriorityRow; max: number; which?: "complaints" | "latest" }) {
  const c = row[which];
  const sx = (v: number) => 6 + (IW - 12) * (v / max);
  const base = row.change?.baseline_rate;
  return (
    <svg width={IW} height={22} aria-hidden="true" style={{ display: "block" }}>
      <line x1={sx(0)} x2={sx(max)} y1={11} y2={11} stroke="var(--grid)" strokeWidth={1} />
      {base !== undefined && which === "complaints" && (
        <line x1={sx(base)} x2={sx(base)} y1={4} y2={18} stroke="var(--axis-muted)" strokeWidth={1.5} />
      )}
      <line x1={sx(c.low)} x2={sx(c.high)} y1={11} y2={11} stroke="var(--series-complaints)" strokeWidth={2}
            strokeLinecap="round" />
      <circle cx={sx(c.rate)} cy={11} r={4} fill="var(--series-complaints)" stroke="var(--surface-1)" strokeWidth={2} />
    </svg>
  );
}

type Props = {
  table: Table;
  selected: string | null;
  onSelect: (feature: string) => void;
};

export function PriorityTable({ table, selected, onSelect }: Props) {
  const [open, setOpen] = useState<string | null>(null);
  const rows = table.rows.filter((r) => r.complaints.count > 0);
  const quiet = table.rows.length - rows.length;
  const max = Math.min(1, Math.max(0.1, ...rows.map((r) => r.complaints.high)));
  const maxLatest = Math.min(1, Math.max(0.1, ...rows.map((r) => r.latest.high)));
  const pooled = table.k > 1;
  return (
    <div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th className="r" title="Ranks in one band are not significantly different">Band</th>
              <th className="r">#</th>
              <th>Feature</th>
              <th>Complaint rate, 95% interval{table.baseline ? ` (grey tick: ${table.baseline})` : ""}</th>
              <th className="r">Complaints</th>
              {pooled && <th>Latest release only ({table.latest}, {table.latest_volume} items)</th>}
              <th className="r">Change vs {table.baseline ?? "–"}</th>
              <th>Status</th>
              <th className="r" title="Rank if sorted by raw complaint posts, duplicates included">Raw-count rank</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <Fragment key={r.feature}>
                <tr className={`feature-row ${selected === r.feature ? "sel" : ""} ${i > 0 && rows[i - 1].band !== r.band ? "band-start" : ""}`}
                    onClick={() => onSelect(r.feature)}>
                  <td className="r num">{i === 0 || rows[i - 1].band !== r.band ? r.band : ""}</td>
                  <td className="r num">{r.rank}</td>
                  <td>
                    <button className="btn" style={{ padding: "2px 8px" }} onClick={(e) => { e.stopPropagation(); onSelect(r.feature); }}
                            aria-label={`Show ${r.name} in the drill-down`}>
                      {r.name}
                    </button>
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Interval row={r} max={max} />
                      <span className="num small">{pct(r.complaints.rate, 1)} <span className="muted">({pct(r.complaints.low, 1)}–{pct(r.complaints.high, 1)})</span></span>
                    </div>
                  </td>
                  <td className="r num">{r.complaints.count} / {r.complaints.n}</td>
                  {pooled && (
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Interval row={r} max={maxLatest} which="latest" />
                        <span className="num small">{r.latest.count} / {r.latest.n} <span className="muted">({pct(r.latest.low)}–{pct(r.latest.high)})</span></span>
                      </div>
                    </td>
                  )}
                  <td className="r num small">
                    {r.change ? (
                      <span title={`95% interval of the difference: ${pts(r.change.low)} to ${pts(r.change.high)} points`}>
                        {pts(r.change.diff)} pts{r.change.significant ? "" : <span className="muted"> (n.s.)</span>}
                      </span>
                    ) : "–"}
                  </td>
                  <td><StatusChip kind={r.status} since={r.since} /></td>
                  <td className="r num">{r.raw_rank}{r.raw_rank !== r.rank && <span className="muted small"> ({r.raw_rank < r.rank ? "higher" : "lower"})</span>}</td>
                  <td>
                    <button className="btn small" style={{ whiteSpace: "nowrap" }} aria-expanded={open === r.feature}
                            onClick={(e) => { e.stopPropagation(); setOpen(open === r.feature ? null : r.feature); }}>
                      {open === r.feature ? "Hide" : `${r.evidence.length} quotes`}
                    </button>
                  </td>
                </tr>
                {open === r.feature && (
                  <tr>
                    <td colSpan={2} />
                    <td colSpan={pooled ? 8 : 7}>
                      {r.evidence.map((q) => (
                        <div className="quote" key={q.item_id}>
                          <q>{q.quote}</q>
                          <div className="meta">{q.item_id} · {sourceLabel(q.source)} · release {q.release} · {q.date}</div>
                        </div>
                      ))}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted">
        Ordered by de-duplicated complaint rate over the window; every feature shares the window&rsquo;s {table.volume} items,
        so a rank alone overstates small differences. A new <strong>band</strong> starts only where a rate is
        significantly lower than the top of the band above (95% interval of the difference excludes zero): ranks inside a
        band are not meaningfully different. The raw-count rank counts every post, duplicates included, and is shown for
        contrast only. &ldquo;n.s.&rdquo;: the change since {table.baseline ?? "the release before"} is not significant.
        {quiet > 0 && ` ${quiet} feature${quiet > 1 ? "s" : ""} with praise or requests only are not listed.`}
      </p>
    </div>
  );
}
