"use client";

import { useEffect, useMemo, useState } from "react";
import { Analysis, modelLabel } from "@/lib/types";
import { PriorityTable } from "@/components/PriorityTable";
import { Alerts, BiasPanel, Drilldown, EvalSummary, Limitations, ReleaseStrip, Requirements, ResearchBasis } from "@/components/Panels";

const SAMPLES = [
  { id: "kestrel", label: "Kestrel Budget (held-out set)" },
  { id: "tallynote", label: "Tallynote (development set)" },
];

function validate(x: unknown): x is Analysis {
  const a = x as Analysis;
  return !!a && Array.isArray(a.releases) && Array.isArray(a.features) && !!a.priority?.tables && Array.isArray(a.flags);
}

export default function Page() {
  const [source, setSource] = useState<string>(SAMPLES[0].id);
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [k, setK] = useState<number | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (source === "upload") return;
    let live = true;
    setError(null);
    fetch(`data/${source}.json`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((j) => { if (live) { setData(j); setK(null); setSelected(null); } })
      .catch((e) => live && setError(`Could not load the sample data (${e.message}).`));
    return () => { live = false; };
  }, [source]);

  const onFile = (file: File) => {
    file.text().then((t) => {
      try {
        const j = JSON.parse(t);
        if (!validate(j)) throw new Error("not a ReleasePulse analysis file");
        setSource("upload"); setData(j); setK(null); setSelected(null); setError(null);
      } catch (e) {
        setError(`Could not read that file: ${(e as Error).message}.`);
      }
    });
  };

  const winK = k ?? data?.priority.default ?? 1;
  const table = data?.priority.tables[String(winK)];
  const feature = useMemo(() => {
    if (!data || !table) return null;
    const id = selected ?? table.rows[0]?.feature;
    return data.features.find((f) => f.id === id) ?? null;
  }, [data, table, selected]);

  const select = (fid: string, scroll = true) => {
    setSelected(fid);
    if (scroll) {
      requestAnimationFrame(() => document.getElementById("drilldown")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  };

  return (
    <main className="wrap">
      <header className="top">
        <div>
          <h1>ReleasePulse</h1>
          <p className="lede">
            App-store reviews and issue tickets turned into per-release, per-feature evidence for prioritisation.
            Rates over de-duplicated volume, a 95% interval on every number, and a quote behind every row.
          </p>
        </div>
      </header>

      <div className="controls" role="group" aria-label="Data">
        <span className="small muted">Sample data, no API key needed:</span>
        <div className="seg">
          {SAMPLES.map((s) => (
            <button key={s.id} aria-pressed={source === s.id} onClick={() => setSource(s.id)}>{s.label}</button>
          ))}
        </div>
        <label className="btn small">
          Load your own analysis.json
          <input type="file" accept="application/json,.json" style={{ display: "none" }}
                 onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
        </label>
      </div>

      {error && <div className="notice" role="alert">{error}</div>}
      {!data && !error && <p className="muted">Loading…</p>}

      {data && table && (
        <>
          <div className="notice">
            {data.notice ? <><strong>Synthetic data:</strong> a fictional app and fictional feedback, generated for evaluation. </> : null}
            {data.app.name}: {Object.keys(data.items).length} feedback items, {data.releases.length} releases. Output of a real
            pipeline run (run 1 of the evaluation, not selected for its score) with <code>{modelLabel(data.model)}</code> and{" "}
            {data.embedding_model.replace("openai:", "")} on{" "}
            {data.generated.slice(0, 10)}
            {data.llm.cost_usd != null && <> (cost ${data.llm.cost_usd.toFixed(3)})</>}. {data.extraction.aspects} aspects,
            every quote verified against its item.
            {source === "upload" && " Loaded from your file, in your browser."}
          </div>

          <Alerts a={data} onSelect={select} />
          <ReleaseStrip a={data} />

          <div className="card">
            <h2>Prioritisation</h2>
            <div className="controls" style={{ marginTop: 8 }} role="group" aria-label="Release window">
              <span className="small muted">Window:</span>
              <div className="seg">
                {Object.values(data.priority.tables).map((t) => (
                  <button key={t.k} aria-pressed={t.k === winK} onClick={() => setK(t.k)}
                          title={`${t.volume} feedback items`}>
                    {t.k === 1 ? `Latest (${t.window[0]})` : `Last ${t.k}`}{t.k === data.priority.default ? " · default" : ""}
                  </button>
                ))}
              </div>
              <span className="small muted">
                Releases {table.window.join(", ")}: {table.volume} items.
                {table.k === data.priority.default && " The default is the shortest window with at least 100 items."}
              </span>
            </div>
            <PriorityTable table={table} selected={feature?.id ?? null} onSelect={select} />
          </div>

          {feature && <Drilldown a={data} feature={feature} onSelect={(f) => select(f, false)} />}

          <BiasPanel a={data} />
          <Requirements a={data} />
          <EvalSummary a={data} />
        </>
      )}

      <ResearchBasis />
      <Limitations />

      <p className="small muted" style={{ marginTop: 24 }}>
        Claims here say &ldquo;grounded in&rdquo; the research, not &ldquo;validated&rdquo;: the evaluation uses synthetic data.
        Run your own feedback through the command line (<code>releasepulse run your.csv</code>) and load the resulting
        analysis.json above.
      </p>
    </main>
  );
}
