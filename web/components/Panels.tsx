"use client";

import { Analysis, Feature, Flag, modelLabel, pct, pts, sourceLabel } from "@/lib/types";
import { StatusIcon } from "./Status";
import { Timeline } from "./Timeline";

const nameOf = (a: Analysis, id: string) => a.features.find((f) => f.id === id)?.name ?? id;

export function Alerts({ a, onSelect }: { a: Analysis; onSelect: (f: string) => void }) {
  const order = a.releases.map((r) => r.version);
  const latest = (fid: string) =>
    a.flags.filter((f) => f.feature === fid).sort((p, q) => order.indexOf(q.release) - order.indexOf(p.release))[0];
  const open = a.flags.filter((f) => f.kind === "regression" && latest(f.feature) === f);
  const fixed = a.flags.filter((f) => f.kind === "improvement");
  const line = (f: Flag) => (
    <>
      <button className="btn small" style={{ padding: "0 6px" }} onClick={() => onSelect(f.feature)}>{nameOf(a, f.feature)}</button>{" "}
      complaints {f.kind === "regression" ? "rose" : "fell"} from {pct(f.previous_rate ?? 0)} of items in {f.previous}{" "}
      to {pct(f.rate ?? 0)} in {f.release}{" "}
      <span className="muted">({f.count} of {f.volume} items; difference {pts(f.diff ?? 0)} points, 95% CI {pts(f.low ?? 0)} to {pts(f.high ?? 0)})</span>
    </>
  );
  return (
    <section aria-label="Regression alerts">
      {open.length > 0 ? (
        <div className="alert critical" role="alert">
          {open.map((f) => (
            <div className="row" key={f.feature + f.release}>
              <svg className="icon" viewBox="0 0 12 12" aria-hidden="true"><path d="M6 1 L11 10 L1 10 Z" fill="var(--status-critical)" /></svg>
              <div><strong>Regression after release {f.release}:</strong> {line(f)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="alert"><div className="row"><span>No open regression: every flagged rise was followed by a significant fall.</span></div></div>
      )}
      {fixed.length > 0 && (
        <details className="alert good">
          <summary>
            <svg className="icon" style={{ margin: "0 6px -2px 2px", width: 14, height: 14 }} viewBox="0 0 12 12" aria-hidden="true"><path d="M6 11 L11 2 L1 2 Z" fill="var(--status-good)" /></svg>
            <span>
              {fixed.length} significant improvement{fixed.length > 1 ? "s" : ""} and {a.flags.length - fixed.length - open.length} resolved regression{a.flags.length - fixed.length - open.length === 1 ? "" : "s"}
            </span>
          </summary>
          {a.flags.filter((f) => !open.includes(f)).map((f) => (
            <div className="row small" key={f.kind + f.feature + f.release}>
              <StatusIcon kind={f.kind === "regression" ? "regression" : "improved"} />
              <div>Release {f.release}: {line(f)}</div>
            </div>
          ))}
        </details>
      )}
    </section>
  );
}

export function BiasPanel({ a }: { a: Analysis }) {
  const key = (f: Flag) => `${f.release}|${f.feature}`;
  const ours = new Set(a.flags.filter((f) => f.kind === "regression").map(key));
  const rawOnly = a.raw_flags.filter((f) => !ours.has(key(f)));
  const dupOnly = a.flags_without_dedupe.filter((f) => f.kind === "regression" && !ours.has(key(f)));
  const explain = (f: Flag) => {
    const feat = a.features.find((x) => x.id === f.feature);
    const cur = feat?.series.find((p) => p.release === f.release);
    const prev = feat?.series.find((p) => p.release === f.previous);
    const posts = (f.count ?? 0) - (cur?.complaints.count ?? 0);
    const reasons = [];
    if (cur && prev && cur.volume > prev.volume * 1.3) reasons.push(`feedback volume rose from ${prev.volume} to ${cur.volume} items`);
    if (posts > 0) reasons.push(`${posts} of the posts repeat an earlier message`);
    return (
      <li key={key(f)}>
        <strong>{nameOf(a, f.feature)}, {f.release}:</strong> complaint posts went from {f.previous_count} to {f.count}
        {cur && prev && <> but the rate went from {pct(prev.complaints.rate, 1)} to {pct(cur.complaints.rate, 1)}</>}
        {reasons.length > 0 && <> ({reasons.join("; ")})</>}. Not flagged here.
      </li>
    );
  };
  return (
    <div className="card">
      <h2>Why rates, intervals and de-duplication</h2>
      <p className="small muted">
        The mapping study this app comes from found one study on decision-making in requirements engineering, and found
        decision-bias research to be mostly post-hoc. Feedback dashboards invite two biases at decision time:
        <em> loudness</em> (whoever posts most, or the release with the most reviews, looks most broken) and
        <em> recency</em> (the newest release has the fewest reviews, so its numbers swing most). ReleasePulse counts a
        repeated message once, divides by de-duplicated volume, reads a thin latest release together with the one before
        it, shows a 95% interval on every rate, groups features into bands instead of trusting small rank differences,
        and calls a change only when the interval of the difference excludes zero and at least {a.settings.min_count} items
        complain.
      </p>
      {rawOnly.length > 0 ? (
        <>
          <h3>What a raw-count rule would also have flagged in this data</h3>
          <p className="small muted">Rule: complaint posts up by at least {a.settings.raw_min_increase} and by {a.settings.raw_min_ratio}×, every post counted.</p>
          <ul className="small">{rawOnly.map(explain)}</ul>
        </>
      ) : <p className="small">A raw-count rule would have flagged the same changes in this data.</p>}
      {dupOnly.length > 0 && (
        <p className="small">Without de-duplication this detector would also flag:{" "}
          {dupOnly.map((f) => `${nameOf(a, f.feature)} in ${f.release}`).join(", ")}.</p>
      )}
    </div>
  );
}

export function ReleaseStrip({ a }: { a: Analysis }) {
  return (
    <div className="card" style={{ padding: "12px 16px" }}>
      <h2>Releases</h2>
      <ol style={{ listStyle: "none", padding: 0, margin: "8px 0 0", display: "grid",
                   gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        {a.releases.map((r) => {
          const flags = a.flags.filter((f) => f.release === r.version);
          return (
            <li key={r.version} style={{ borderLeft: "2px solid var(--grid)", paddingLeft: 10 }}>
              <div><strong>{r.version}</strong> <span className="small muted">{r.date}</span></div>
              <div className="small num">{r.volume} items{r.duplicates ? ` (+${r.duplicates} duplicates)` : ""}</div>
              <div className="small muted">{r.notes}</div>
              {flags.map((f) => (
                <div className="chip wrap" key={f.kind + f.feature}>
                  <StatusIcon kind={f.kind === "regression" ? "regression" : "improved"} />
                  {nameOf(a, f.feature)} {f.kind === "regression" ? "regressed" : "improved"}
                </div>
              ))}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function Drilldown({ a, feature, onSelect }: { a: Analysis; feature: Feature; onSelect: (f: string) => void }) {
  const flags = a.flags.filter((f) => f.feature === feature.id);
  const labels = Object.entries(feature.labels);
  const releasesNewestFirst = [...a.releases].reverse();
  return (
    <div className="card" id="drilldown">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "baseline" }}>
        <h2>Feature drill-down: {feature.name}</h2>
        <label className="small muted">
          Feature{" "}
          <select value={feature.id} onChange={(e) => onSelect(e.target.value)}>
            {a.features.map((f) => <option key={f.id} value={f.id}>{f.name} ({f.mentions})</option>)}
          </select>
        </label>
      </div>
      <p className="small muted">
        {feature.mentions} verified mentions, merged from the aspect names{" "}
        {labels.slice(0, 8).map(([l, n]) => `“${l}” (${n})`).join(", ")}{labels.length > 8 ? ", …" : ""}.
        Share of each release&rsquo;s feedback items that complain about or praise it.
      </p>
      <Timeline feature={feature} releases={a.releases} flags={flags} />
      <div className="grid2" style={{ marginTop: 12 }}>
        {(["complaints", "praise"] as const).map((cls) => (
          <div key={cls}>
            <h3>{cls === "complaints" ? "Complaints" : "Praise"}, newest release first</h3>
            {releasesNewestFirst.flatMap((r) => (feature.quotes[r.version]?.[cls] ?? []).map((q) => (
              <div className="quote" key={cls + q.item_id}>
                <q>{q.quote}</q>
                <div className="meta">{q.item_id} · {sourceLabel(q.source)} · release {q.release} · {q.date}</div>
              </div>
            ))).slice(0, 8)}
            {releasesNewestFirst.every((r) => !(feature.quotes[r.version]?.[cls] ?? []).length) && <p className="small muted">None.</p>}
          </div>
        ))}
      </div>
      {releasesNewestFirst.some((r) => (feature.quotes[r.version]?.requests ?? []).length) && (
        <>
          <h3 style={{ marginTop: 12 }}>Requests</h3>
          {releasesNewestFirst.flatMap((r) => (feature.quotes[r.version]?.requests ?? []).map((q) => (
            <div className="quote" key={"req" + q.item_id}>
              <q>{q.quote}</q>
              <div className="meta">{q.item_id} · {sourceLabel(q.source)} · release {q.release}</div>
            </div>
          ))).slice(0, 4)}
        </>
      )}
    </div>
  );
}

export function Requirements({ a }: { a: Analysis }) {
  const reqs = a.requirements?.requirements ?? [];
  const download = () => {
    const blob = new Blob([JSON.stringify(a.requirements, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${a.app.id}-candidate-requirements.json`;
    link.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "baseline" }}>
        <h2>Candidate requirements for ElicitSense</h2>
        {reqs.length > 0 && <button className="btn small" onClick={download}>Download JSON (register shape)</button>}
      </div>
      <p className="small muted">
        The top issues with at least 3 complaints, worded by the model, with status &ldquo;proposed&rdquo;: they need
        confirming with stakeholders. Evidence, rationale and uncertainty come from the counts, not from the model.
      </p>
      {reqs.length === 0 && <p className="small">None exported in this analysis.</p>}
      {reqs.map((r) => (
        <div className="req" key={r.id}>
          <div className="small muted">{r.id} · rank {r.releasepulse.rank}, band {r.releasepulse.band} · {r.releasepulse.feature_name}</div>
          <div style={{ margin: "4px 0" }}><strong>{r.statement}</strong></div>
          <div>
            <span className="tag">{r.type.replace("_", "-")}</span>
            <span className="tag">{r.status}</span>
            {r.uncertainty.flag && <span className="tag">{r.uncertainty.label}: {r.uncertainty.cues.map((c) => c.detail).join("; ")}</span>}
          </div>
          <p className="small" style={{ margin: "6px 0" }}>{r.rationale}</p>
          <details className="small">
            <summary>{r.evidence.length} evidence quotes</summary>
            {r.evidence.map((e) => (
              <div className="quote" key={e.segment_id}>
                <q>{e.quote}</q>
                <div className="meta">{e.segment_id} · {sourceLabel(e.speaker)} · {e.meeting} · {e.date}</div>
              </div>
            ))}
          </details>
        </div>
      ))}
    </div>
  );
}

const fmt = (v: { mean: number; min: number; max: number } | undefined, f: (x: number) => string) => {
  if (!v) return "–";
  return f(v.min) === f(v.max) ? f(v.mean) : `${f(v.mean)} (${f(v.min)}–${f(v.max)})`;
};

export function EvalSummary({ a }: { a: Analysis }) {
  const e = a.evaluation;
  if (!e) return null;
  const two = (x: number) => x.toFixed(2);
  return (
    <div className="card">
      <h2>How this pipeline scores on this {e.role} set</h2>
      <p className="small muted">
        {e.runs_per_model} full pipeline run{e.runs_per_model > 1 ? "s" : ""} per model against the planted truth; mean
        with range across runs. The page above shows one of the runs.
      </p>
      <div className="table-scroll">
        <table className="small">
          <thead>
            <tr><th>Model</th><th className="r">Mention F1</th><th className="r">Hard mentions found</th>
              <th className="r">Quotes verified</th><th className="r">Cluster purity</th><th className="r">Regression P / R</th>
              <th className="r">Improvement R</th><th className="r">Cost per run (USD)</th></tr>
          </thead>
          <tbody>
            {Object.entries(e.models).map(([m, s]) => (
              <tr key={m} className="num">
                <td>{modelLabel(m)}</td>
                <td className="r">{fmt(s.mention_f1, two)}</td>
                <td className="r">{fmt(s.hard_recall, two)}</td>
                <td className="r">{fmt(s.quote_validity, two)}</td>
                <td className="r">{fmt(s.purity, two)}</td>
                <td className="r">{fmt(s.reg_precision, two)} / {fmt(s.reg_recall, two)}</td>
                <td className="r">{fmt(s.imp_recall, two)}</td>
                <td className="r">{fmt(s.cost_usd, (x) => `$${x.toFixed(3)}`)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ResearchBasis() {
  return (
    <details className="card panel">
      <summary>Research basis</summary>
      <p className="small">
        ReleasePulse is grounded in the systematic mapping study <em>Emotions in Software Engineering</em> (57 studies,
        five emotion categories × five lifecycle phases). Its map has one study in the cell decision-making ×
        requirements engineering (Iqbal et al. 2023, <em>JSS</em> 197), and the decision-making studies it found are
        almost all post-hoc analyses of maintenance artefacts. This app moves that evidence to the moment a
        prioritisation decision is made.
      </p>
      <ul className="small">
        <li>Feature-level opinion mining of app reviews for requirements work: Guzman &amp; Maalej, &ldquo;How Do Users Like This
          Feature? A Fine Grained Sentiment Analysis of App Reviews&rdquo;, RE 2014. User emotion in app reviews and tweets:
          Martens &amp; Johann, SEmotion 2017; Williams &amp; Mahmoud, SEmotion 2017 (both in the mapping study).</li>
        <li>Loudness and recency as availability effects: Tversky &amp; Kahneman, &ldquo;Availability: A heuristic for judging
          frequency and probability&rdquo;, <em>Cognitive Psychology</em> 5 (1973). Cognitive biases in software engineering,
          with mitigation rarely studied: Mohanani et al., <em>IEEE TSE</em> 46(12), 2020.</li>
        <li>Intervals: Wilson score interval (Wilson, <em>JASA</em> 22, 1927) for rates; Newcombe&rsquo;s hybrid score interval
          for a difference of proportions (<em>Statistics in Medicine</em> 17, 1998).</li>
        <li>Polarity and complaint or praise cues instead of emotion labels: inferring emotions from expressions is
          unreliable (Barrett et al., <em>Psychological Science in the Public Interest</em> 20, 2019).</li>
      </ul>
    </details>
  );
}

export function Limitations() {
  return (
    <details className="card panel">
      <summary>Limitations</summary>
      <ul className="small">
        <li>The sample apps and every review in them are synthetic, written from templates by the same person who wrote
          the gold labels and the prompts. Real feedback is messier; the scores here are a smoke test, not a benchmark.</li>
        <li>Rates are shares of <em>feedback items</em>, not of users. People who write reviews are self-selected and
          lean negative, so a 10% complaint rate does not mean 10% of users are affected.</li>
        <li>Reviews and issue tickets share one denominator per release. Release assignment by date (for items
          without a version) is approximate.</li>
        <li>Duplicate detection is lexical: a paraphrased campaign is counted several times.</li>
        <li>Clustering can split one feature into several rows (for example &ldquo;editor&rdquo; and &ldquo;checklists&rdquo;),
          which spreads its evidence and lowers its rank.</li>
        <li>Each feature is tested at every release change, at 95% each, with no correction for multiple comparisons; the
          minimum of {5} complaints limits but does not remove false alarms. Only consecutive releases are compared,
          so a slow drift is not flagged.</li>
        <li>Quotes are checked against the item text; polarity and feature assignment are the model&rsquo;s and are not.</li>
        <li>Candidate requirements are proposals worded by a model and need confirming with stakeholders.</li>
      </ul>
      <p className="small muted">
        Privacy: this analyses customer feedback text about a product. It scores no person and infers no emotions about
        anyone (EU AI Act Art. 5(1)(f) prohibits emotion inference about workers). A file you load here is read in your
        browser and not uploaded.
      </p>
    </details>
  );
}
