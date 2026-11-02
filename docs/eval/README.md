# ReleasePulse evaluation report

What this measures: how well each step of the pipeline recovers a planted
ground truth in two synthetic feedback sets, and how the choice of LLM changes
quality, cost and speed. Every number comes from `releasepulse bench` runs;
the per-run files are in `runs/` (not committed), and the tables linked below
are generated from them.

**Read these numbers as a smoke test, not a benchmark.** The data is synthetic
and was written from templates by the same person who wrote the gold labels
and the prompts (see [Limitations of this evaluation](#limitations-of-this-evaluation)).

## Setup

| | |
|---|---|
| Development set | `tallynote`, a fictional notes app: 5 releases, 365 items (361 after de-duplication), 318 planted mentions of 12 features, 39 of them deliberately hard. Planted: 2 regressions, 3 improvements, 3 traps. Prompts, the clustering threshold and the regression rule were tuned on it. |
| Held-out set | `kestrel`, a fictional budgeting app: 5 releases, 345 items (341), 292 planted mentions of 11 features, 37 hard. Planted: 2 regressions, 2 improvements, 3 traps. Written before any model ran on it; revised once (harder phrasings added) after the development results, still before any model ran on it. |
| Traps | *Volume spike*: a release with about twice the reviews, so one feature's complaint count doubles at a flat rate. *Duplicate burst*: one message posted five times. *Small sample*: a new feature with 3 complaints in a 40- or 50-item release. |
| Hard phrasings | Sarcasm ("Love waiting ten minutes for my notes to show up"), no feature name ("I typed my password five times today and I'm still looking at the welcome screen"), negated praise ("It's not sluggish anymore"), typos ("reciept scaner crashs"), emoji ("sync 🐌🐌🐌"). |
| LLM steps | Extraction (batches of 20 items, strict JSON schema, item ids restricted to the batch), feature normalisation (one call per run), requirement wording (one call per run). |
| Embeddings | `text-embedding-3-small`, average-linkage clustering at cosine similarity 0.55 |
| Models | `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.1-sol` (OpenAI Responses API, default reasoning settings), and two routed configurations: `gpt-6-luna` extracts, `gpt-6.1-terra` or `gpt-6.1-sol` normalises and words. |
| Runs | Held-out: 3 full runs per configuration. Development: 1 run per configuration. |
| Cost | Published standard prices as of 2026-11-01 ([pricing.py](../../releasepulse/pricing.py)): `gpt-6.1-sol` $2 / $0.10 / $10, `gpt-6.1-terra` $1 / $0.05 / $5, `gpt-6-luna` $0.10 / $0.01 / $0.50 per million input / cached input / output tokens; embeddings $0.02 per million. |

### How things are scored

- **Mentions.** Within each item, extracted aspects and planted mentions are
  paired one-to-one by the character spans of the verified quotes (exact
  search: most pairs, then most coverage). An unpaired aspect whose quote
  overlaps a paired mention is a *split* (counted as grounded for precision,
  as wrong for strict precision); anything else unpaired is *extra*. This
  scores extraction independently of how features are named.
- **Features.** Each predicted feature is mapped to the planted feature most
  of its paired aspects belong to. *Purity*: share of paired aspects whose
  feature maps to their own planted feature. *Inverse purity*: share that sit
  in the predicted feature holding most of their planted feature (low when a
  feature is split into several rows). Item×feature F1 is computed after the
  mapping.
- **Regressions and improvements.** A flag is correct only if both the
  release and the (mapped) feature match the planted truth.
- **Traps.** A trap counts as flagged if the detector raised a regression for
  that release and feature.
- **Baselines on the same extraction.** The *raw-count rule* flags a rise of
  at least 4 complaint posts and at least 1.5×, counting every post. The
  *oracle* runs the detector and the raw-count rule on the planted labels.
- **Quotes verified**: share of proposed aspects whose quote was found in the
  item (the rest are dropped before counting). Cues are checked the same way.

## Results

### Held-out set, blind run (embedding clusters only)

Full table: [kestrel.md](kestrel.md). Mean of 3 runs, range in brackets.

| | `gpt-6-luna` | `gpt-6.1-terra` | `gpt-6.1-sol` |
|---|---|---|---|
| Mention F1 | 1.00 (0.997–1.00) | 0.995 | 0.996 (0.995–0.997) |
| Hard mentions found | 1.00 | 1.00 | 1.00 |
| Polarity agreement | 1.00 | 1.00 | 1.00 |
| Quotes verified | 1.00 | 1.00 | 1.00 |
| Cluster purity / inverse purity | 0.97 / 0.66 | 0.96 / 0.62 | 0.97 / 0.65 |
| Features found (11 planted) | 31 (28–32) | 33 (32–34) | 29 (28–31) |
| Regression precision / recall | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| Improvement precision / recall | 0.89 / 1.00 | 1.00 / 0.67 | 0.56 / 0.67 |
| Traps flagged (of 3) | 0 | 0 | 0 |
| Cost per run (USD) | 0.015 | 0.093 (0.088–0.103) | 0.257 (0.245–0.276) |
| Sum of call latencies / wall time (s) | 262 / 78 | 212 / 64 | 218 / 68 |

### Held-out set, second look: feature normalisation and routing

Added after the blind run (see [what changed](#what-changed-during-development-and-why)),
developed on the development set, then run on the held-out set **with the
extraction outputs of the blind runs reused**, so only the later steps
differ. The held-out set is no longer blind for this comparison. Full table:
[kestrel-normalised.md](kestrel-normalised.md).

| Extract → organise | Purity / inverse purity | Features | Regression P / R | Improvement P / R | Traps flagged | Cost per run (USD) |
|---|---|---|---|---|---|---|
| `gpt-6-luna` | 0.97 / 0.83 | 17 | 1.00 / 1.00 | 1.00 / 0.83 | 0 | 0.016 |
| `gpt-6.1-terra` | 0.95 / 0.84 | 18 | 1.00 / 1.00 | 1.00 / 1.00 | 0 | 0.097 |
| `gpt-6.1-sol` | 0.96 / 0.86 | 17 | 1.00 / 1.00 | 1.00 / 1.00 | 0 | 0.264 |
| `gpt-6-luna` → `gpt-6.1-terra` | 0.97 / 0.81 | 18 | 1.00 / 1.00 | 1.00 / 0.83 | 0 | 0.021 |
| `gpt-6-luna` → `gpt-6.1-sol` (default) | 0.97 / 0.87 | 17 | 1.00 / 1.00 | 1.00 / 0.83 | 0 | 0.027 |

### Development set

One run per configuration. Full tables: [tallynote.md](tallynote.md)
(embedding clusters only) and [tallynote-normalised.md](tallynote-normalised.md).

| | `gpt-6-luna` | `gpt-6.1-terra` | `gpt-6.1-sol` | `luna` → `sol` |
|---|---|---|---|---|
| Mention F1, hard mentions found | 1.00, 1.00 | 1.00, 1.00 | 1.00, 1.00 | 1.00, 1.00 |
| Inverse purity, clusters only → normalised | 0.89 → 0.96 | 0.90 → 0.94 | 0.92 → 0.97 | 0.96 |
| Regression P / R | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| Improvement recall, clusters only → normalised | 1.00 → 0.67 | 1.00 → 1.00 | 1.00 → 1.00 | 0.67 |
| Cost per run (USD) | 0.015 | 0.111 | 0.294 | 0.025 |

### Loudness and volume: the detector against the raw-count rule

| | Development | Held out |
|---|---|---|
| Raw-count rule on the planted labels: precision / recall | 0.50 / 1.00 (false alarms: the duplicate burst, the volume spike) | 0.50 / 1.00 (same two traps) |
| The detector without de-duplication, planted labels: precision | 0.67 (falls for the duplicate burst) | 0.67 (same) |
| The detector, planted labels | 1.00 / 1.00 | 1.00 / 1.00 |
| The detector on model outputs, every run and configuration | 1.00 / 1.00, no trap flagged | 1.00 / 1.00, no trap flagged |
| Raw-count rule on model outputs: precision | 0.40–0.50 | 0.50–0.67 |

Deterministic steps, both sets: release assignment (by version, else by date)
1.00 accurate; duplicate detection precision and recall 1.00.

## Findings

1. **Extraction does not separate the models on this data.** Every model
   finds 0.995 to 1.00 of the planted mentions with the right polarity,
   including every deliberately hard phrasing, and every kept quote verifies.
   `gpt-6-luna` does it for a seventeenth of the cost of `gpt-6.1-sol`
   ($0.015 against $0.257 per 341-item run). The synthetic texts are cleaner
   than real reviews, so this is a ceiling, not a measurement of the gap.
2. **Grouping aspects into features is where the pipeline was weakest.** With
   embedding clusters alone, the threshold chosen on the development set
   (inverse purity 0.89 to 0.92 there) split the held-out features into
   sub-features: "performance", "startup", "loading speed" and "dashboard"
   for one planted feature, "price", "free version", "premium" and
   "subscription" for another. Inverse purity fell to 0.62 to 0.66, and the
   held-out set ended up with about 30 features against 11 planted.
3. **A split feature produces false and missed flags.** A fragment's counts
   are small and swing between releases: all three `gpt-6.1-sol` runs and one
   `gpt-6-luna` run flagged a spurious "speed improved in 3.1" from one
   fragment, and two of three `gpt-6.1-terra` and two of three `gpt-6.1-sol`
   runs missed the planted speed improvement in 3.2. Regressions, which were planted large, were found in
   every run regardless.
4. **One normalisation call fixes most of it.** On identical extraction
   outputs, merging clusters with one LLM call raised held-out inverse purity
   to 0.81 to 0.87 (features 15 to 20), removed every spurious improvement
   (precision 1.00 for all configurations) and brought improvement recall to
   1.00 for `gpt-6.1-terra` and `gpt-6.1-sol`. Purity stayed at 0.95 to 0.97.
   The call costs $0.006 to $0.009 on `gpt-6.1-sol` and under $0.001 on
   `gpt-6-luna`.
5. **A cheap extractor in front of a strong organiser keeps the quality at a
   tenth of the cost.** `gpt-6-luna` → `gpt-6.1-sol` had the highest held-out
   inverse purity (0.87), perfect regression detection and no trap flagged,
   for $0.027 per run against $0.264 for `gpt-6.1-sol` alone. It is the
   default.
6. **Improvement flags are fragile at these sample sizes, and that shows up
   as one missed flag per few runs.** Every `gpt-6-luna`-extracted held-out
   configuration missed the 3.2 speed improvement in run 1: one complaint was
   named "dashboard" and stayed outside the merged feature, and with the
   planted labels the improvement clears significance by only three
   percentage points. On the development set, the normaliser (all models)
   merged a crash ticket that `gpt-6-luna` had labelled "notes" into
   reminders, and that one extra complaint in a 40-item release made the
   planted 2.4 reminders improvement no longer significant.
7. **Normalising volume and de-duplicating is what removes the false alarms.**
   On the planted labels, a raw-count rule raises two false alarms per set
   (precision 0.50): the volume spike and the duplicate burst. Without
   de-duplication the significance test still falls for the duplicate burst.
   On model outputs the detector raised no trap in any run of any
   configuration. The small-sample trap was flagged by neither method: the
   point is ranking, not detection (finding 9).
8. **The cheapest model is not the fastest.** `gpt-6-luna` spends about half
   its output tokens on reasoning (14k of 28k per held-out run, against 2k to
   3k for the other two), so its median batch takes 14.7 s against 11.4 s
   (`gpt-6.1-terra`) and 12.0 s (`gpt-6.1-sol`). With four batches in flight a
   full run takes 64 to 78 s either way.
9. **Ordering by an interval's lower bound did not do what it claimed, so it
   was replaced.** Within one window every feature shares the same
   denominator, so ranking by the Wilson lower bound orders rows exactly as
   counts do. The table now groups features into bands: a new band starts
   only where a rate is significantly lower than the top of the band above.
   On the held-out demo run the top band holds four features (13, 13, 5 and 5
   complaints of 160), which a rank alone would have presented as a strict
   order. This is a presentation change and does not affect any score above.

## What changed during development, and why

In order, so the held-out numbers can be read with their history:

1. One planted development phrase ("offline edits vanish when I reconnect")
   was ambiguous between offline mode and sync; both probe models read it as
   sync. Replaced.
2. Prompt rule added on the development set: name features at the level a
   product team tracks. Development inverse purity 0.86 → 0.89 (`gpt-6-luna`).
3. Clustering threshold swept on the development set
   (`releasepulse sweep`, no LLM calls): 0.55 kept. Embedding a context
   template ("app feature: …") with the label compressed all similarities
   and made the threshold fragile; bare labels kept.
4. The development results were at the ceiling, so harder phrasings were
   added to both sets, before any model ran on the held-out set.
5. The scorer first paired aspects and mentions greedily; a quote spanning
   two sentences could take the wrong mention. Replaced by exact per-item
   search. This changed no model output.
6. A model miscounted the evidence in a free-text rationale ("Twenty-two"
   for 24), so rationales are now computed from the counts and the model
   words only the statement and type.
7. Prompts, threshold and rules frozen; held-out blind run.
8. After seeing finding 2, feature normalisation was added and tested on the
   development set (inverse purity +0.04 to +0.07, regressions unchanged, one
   borderline improvement lost for `gpt-6-luna`), then run on the held-out
   set as a second look on the same extraction outputs. Routing was tested
   the same way.
9. Priority ordering changed to bands (finding 9).

## Limitations of this evaluation

- Synthetic, templated data from one author. Real reviews are longer, vaguer,
  multilingual and off-topic far more often; extraction recall on them will
  be lower and the model differences larger.
- Two apps, five releases each, 4 or 5 planted changes per app: one flag
  moves precision or recall by 0.25 to 0.50.
- Planted changes are mostly large. The two that are near the significance
  line (finding 6) show how a single mislabelled mention changes the outcome.
- The development set has one run per configuration; differences there are
  anecdotes.
- The held-out set was seen once (blind) before the normalisation step was
  added; the second-look numbers are not blind.
- Feature mapping by majority favours fine-grained clusters on purity, which
  is why both purity and inverse purity are reported.

## Spend

About $2.17 of OpenAI usage in total for development and evaluation:
extraction $1.93 (352 batch calls), requirement wording $0.12 (36 calls,
plus about $0.01 in two calls whose logs were overwritten), feature
normalisation $0.08 (20 calls), two probe calls $0.02, embeddings under
$0.001 (every aspect name embedded once and cached).

## Reproduce

```bash
export RELEASEPULSE_ENV_FILE=/path/to/.env   # or put OPENAI_API_KEY in ./.env
uv run releasepulse synth                     # regenerates data/synthetic byte for byte
uv run releasepulse bench data/synthetic/kestrel --runs 3 --no-normalise -o runs/bench/kestrel \
  -m openai:gpt-6-luna openai:gpt-6.1-terra openai:gpt-6.1-sol
uv run releasepulse bench data/synthetic/kestrel --runs 3 -o runs/bench/kestrel-norm \
  --reuse-extraction runs/bench/kestrel --report docs/eval/kestrel-normalised.md \
  -m openai:gpt-6-luna openai:gpt-6.1-terra openai:gpt-6.1-sol \
     "openai:gpt-6-luna>openai:gpt-6.1-terra" "openai:gpt-6-luna>openai:gpt-6.1-sol"
uv run releasepulse sweep runs/<run>/analysis.json data/synthetic/tallynote
```

The blind held-out run was made before `--no-normalise` existed; the flag
reproduces it. Model outputs vary between runs, so reruns give numbers close
to, not equal to, these.
