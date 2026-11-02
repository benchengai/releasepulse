# ReleasePulse

Turn app-store reviews and issue tickets into per-release, per-feature
evidence for prioritisation: which features users complain about or praise,
whether a release made something worse, how sure that is, and the quotes
behind every number. The top issues export as candidate requirements for an
[ElicitSense](../elicitsense) register.

Portfolio app 3 of 5 built from the systematic mapping study *Emotions in
Software Engineering* (57 studies). It targets the map's decision-making ×
requirements-engineering cell.

## The problem

Product teams read feedback to decide what to fix next, and feedback
dashboards push those decisions towards two biases:

- **Loudness.** Raw counts reward whoever posts most and whichever release got
  the most reviews. One rant posted on two stores and the tracker counts
  three times; a release that was featured in the store looks twice as broken
  because it got twice the reviews.
- **Recency.** The newest release has the fewest reviews, so its numbers swing
  most. Three complaints in a two-week-old release look alarming next to
  steadier, older evidence.

ReleasePulse is designed against both: it counts a repeated message once,
divides by de-duplicated review volume, shows a 95% interval on every rate,
reads a thin latest release together with the one before it, calls a change
a regression only when it is statistically clear, and groups features into
bands instead of presenting small rank differences as real. It never ranks by
raw counts; the raw-count rank is shown next to each row only so the
difference is visible.

## Research basis

ReleasePulse is grounded in, not validated by, this research:

- **The mapping study.** Its emotion-category × lifecycle-phase map has one
  study in the decision-making × requirements cell (Iqbal et al., *Theory of
  constructed emotion meets RE*, JSS 197, 2023), and the decision-making
  studies it found are almost all post-hoc analyses of maintenance artefacts.
  ReleasePulse moves that evidence to the moment a prioritisation decision is
  made.
- **App-review mining for requirements.** Feature-level opinion mining of app
  reviews: Guzman & Maalej, *How Do Users Like This Feature? A Fine Grained
  Sentiment Analysis of App Reviews*, RE 2014. User emotion in app reviews and
  tweets: Martens & Johann, SEmotion 2017; Williams & Mahmoud, SEmotion 2017
  (both in the mapping study).
- **The biases.** Judging frequency by how easily examples come to mind:
  Tversky & Kahneman, *Availability: A heuristic for judging frequency and
  probability*, Cognitive Psychology 5, 1973. Cognitive biases in software
  engineering, where mitigation is rarely studied: Mohanani et al., IEEE TSE
  46(12), 2020.
- **The statistics.** Wilson score intervals for rates (Wilson, JASA 22,
  1927); Newcombe's hybrid score interval for a difference of two proportions
  (Statistics in Medicine 17, 1998), checked in the tests against the paper's
  worked example.
- **Cues, not emotions.** The model reports polarity and the complaint or
  praise cues it relied on, quoted from the text, rather than emotion labels:
  inferring emotions from expressions is unreliable (Barrett et al.,
  Psychological Science in the Public Interest 20, 2019).

## What it does

```
feedback.csv ─► ingest ─► extract (LLM) ─► cluster (embeddings) ─► normalise (LLM)
   text, date,   release by    aspects, polarity,   text-embedding-3-small,   merge clusters into
   version,      version or    quote, cues; every   average linkage           tracked features,
   source        date; dedupe  quote verified                                  ids checked by code
                                                        │
      ┌─────────────────────────────────────────────────┘
      ▼
  per-release rates ─► regression and improvement flags ─► prioritisation table ─► candidate requirements
  complaints / volume,  Newcombe interval excludes zero      bands, intervals,          ElicitSense register
  Wilson 95% intervals  and at least 5 complaints            latest-release rate,       shape, status "proposed"
                                                              quotes on every row
```

- **Ingest.** CSV with `text, date, version, source` (optional `id`,
  `rating`). An item belongs to the release its version names (`2.1.3` → `2.1`);
  without a usable version, to the latest release on or before its date.
  Releases come from a `releases.csv` (`version, date, notes`) or are inferred
  from the versions seen. A text repeated with near-identical wording (eight
  words or more) counts once; short texts like "Great app!" are never merged.
- **Extract.** Batches of 20 items, strict JSON schema, item ids restricted to
  the batch. Per item: the features it comments on, polarity (negative,
  positive, mixed, neutral), a quote and up to three complaint or praise
  cues. Every quote and cue is checked against the item text; aspects whose
  quote is not there are dropped and recorded.
- **Cluster and normalise.** Aspect names are embedded and clustered; one LLM
  call then merges sub-features ("startup", "loading speed" → "performance")
  and names the features. Cluster ids in that call are restricted to the ones
  shown, and the grouping is applied and checked by code.
- **Trends and flags.** Per release and feature: share of items that complain,
  praise or request, with Wilson intervals. A regression is flagged when the
  95% interval of the rise excludes zero and at least 5 items complain; an
  improvement the same way downwards.
- **Prioritisation.** For a window of recent releases (by default the shortest
  with at least 100 items): complaint rate and interval, the latest release's
  own rate and interval, change since the release before, status, raw-count
  rank, and up to five verified quotes per row. Rows are grouped into bands; a
  new band starts only where a rate is significantly lower than the top of the
  band above.
- **Export.** The top issues with at least 3 complaints become candidate
  requirements in ElicitSense's register shape (`id, type, statement,
  rationale, acceptance, stakeholder, status: "proposed", evidence[{meeting,
  segment_id, speaker, quote}], quality, uncertainty, history, …`). The model
  only words the statement and picks the type; evidence, rationale and the
  "needs confirmation" flag come from the counts.

Model calls go through one provider-neutral function with strict JSON output
and a cost log per call. Steps can be routed: `openai:gpt-6-luna>openai:gpt-6.1-sol`
extracts with the first model and normalises and words with the second (the
default).

## Quick start

Requires Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 24, and an
OpenAI API key for new analyses. The demo needs no key.

```bash
uv sync
uv run pytest
```

Web demo with the sample data (no API key; loads in a few seconds):

```bash
cd web && npm install && npm run build
python3 -m http.server 4317 --directory out    # then open http://localhost:4317
```

Analyse your own feedback. Put `OPENAI_API_KEY=...` in a `.env` file at the
repository root (git-ignored), or point `RELEASEPULSE_ENV_FILE` at an env
file; existing environment variables are not overridden.

```bash
uv run releasepulse run data/synthetic/tallynote                 # a folder with feedback.csv and releases.csv
uv run releasepulse run my_feedback.csv --releases releases.csv --product "Acme, a recipe app"
uv run releasepulse eval runs/tallynote/<model>/analysis.json data/synthetic/tallynote/gold.json
uv run releasepulse bench data/synthetic/kestrel --runs 3 -m openai:gpt-6-luna openai:gpt-6.1-sol
uv run releasepulse web-export runs/.../analysis.json -o web/public/data/myapp.json
uv run releasepulse synth                                         # regenerate the synthetic sets
```

`run` prints the flags and the priority table and writes `analysis.json`
(load it in the web demo with "Load your own analysis.json"; it is read in the
browser and not uploaded). Extraction batches and the other model calls are
cached in the run folder, so an interrupted run resumes without paying again.

## Results

Two synthetic apps: `tallynote` (development set, prompts tuned on it) and
`kestrel` (held out). Full method, tables and history:
[docs/eval](docs/eval/README.md). Held-out set, three runs per model, mean:

| | `gpt-6-luna` | `gpt-6.1-terra` | `gpt-6.1-sol` | `luna` → `sol` (default) |
|---|---|---|---|---|
| Aspect extraction F1 (planted mentions, by quote span) | 1.00 | 0.995 | 0.996 | 1.00 |
| Deliberately hard phrasings found (sarcasm, typos, no feature name) | 1.00 | 1.00 | 1.00 | 1.00 |
| Quotes verified against the item | 1.00 | 1.00 | 1.00 | 1.00 |
| Cluster purity / inverse purity, embeddings only (blind run) | 0.97 / 0.66 | 0.96 / 0.62 | 0.97 / 0.65 | – |
| Cluster purity / inverse purity, with normalisation (second look) | 0.97 / 0.83 | 0.95 / 0.84 | 0.96 / 0.86 | 0.97 / 0.87 |
| Regressions, release and feature: precision / recall | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| Improvements: precision / recall, with normalisation | 1.00 / 0.83 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 0.83 |
| Traps flagged (volume spike, duplicate burst, small sample) | 0 of 3 | 0 of 3 | 0 of 3 | 0 of 3 |
| Cost per run, 341 items (USD) | 0.016 | 0.097 | 0.264 | 0.027 |
| Wall time per run, 4 calls in flight (without / with normalisation) | 78 / 99 s | 64 / 77 s | 68 / 86 s | 94 s |

On the planted labels themselves, a naive raw-count rule ("complaints up by 4
and by half") raises two false alarms per app, precision 0.50: the volume
spike and the duplicate burst. Without de-duplication the significance test
still falls for the duplicate burst (0.67).

What this shows: on short review text, extracting grounded aspects is within
reach of the cheapest model; the weak step was grouping aspects into
features, where an embedding threshold tuned on one app split the other
app's features into fragments small enough to produce false and missed
flags. One normalisation call on a stronger model fixes most of that, and a
cheap extractor in front of it costs a tenth of the strongest model alone.
The normalisation step and routing were added after the blind held-out run,
so their held-out numbers are a second, not blind, look on the same
extraction outputs.

Total OpenAI spend for development and evaluation: about $2.17.

## Privacy and compliance

- ReleasePulse analyses customer feedback about a product. It produces no
  per-person scores and infers no emotions about anyone: it reports polarity
  and quoted cues about product features. Do not point it at employee
  communication: the EU AI Act (Art. 5(1)(f)) prohibits AI emotion inference
  in the workplace.
- Feedback text is sent to the model provider you configure. Strip personal
  data you do not need before running it.
- The web demo is static. A file you load into it stays in your browser.
- All sample data is synthetic: fictional apps, fictional reviews, generated
  by `releasepulse synth` and labelled as such in every file and on the page.
  No public review dataset is included; the CLI accepts any CSV with the
  four columns.

## Limitations

- **Synthetic, templated evaluation data** written by the same person who
  wrote the prompts and gold labels. Real reviews are messier; treat the
  results as a smoke test, not a benchmark.
- **Rates are shares of feedback items, not of users.** Reviewers are
  self-selected and lean negative.
- Reviews and tickets share one denominator per release; release assignment
  by date (for items without a version) is approximate.
- Duplicate detection is lexical: a paraphrased campaign counts several times.
- Feature grouping is the weakest step. Even with normalisation, a feature can
  be split or two can be merged, which moves its counts and can flip a
  borderline flag (see finding 6 in the report).
- Every feature is tested at every release change at 95%, with no correction
  for multiple comparisons; the 5-complaint minimum limits but does not
  remove false alarms. Only consecutive releases are compared, so a slow drift
  is not flagged. Bands treat two rates from the same items as independent,
  an approximation.
- Polarity and feature assignment are the model's and are not verified, only
  the quotes are.
- Candidate requirements are proposals worded by a model; confirm them with
  stakeholders.

## Repository

```
releasepulse/          pipeline: ingest, extract, cluster, normalise, trends, prioritise, requirements
releasepulse/synthetic generator and the two fictional app specs (planted truth)
data/synthetic/        generated feedback.csv, releases.csv, gold.json per app
docs/eval/             evaluation report and generated tables
tests/                 pytest suite (no network)
web/                   Next.js static demo (output: 'export')
```
