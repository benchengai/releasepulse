### kestrel: 3 runs per model

Mean across successful runs, range in brackets. Cost and time are per full pipeline run (every item extracted, aspects embedded and clustered, requirements worded). Time is the sum of call latencies; wall time is with 4 extraction calls in flight.

**Extraction and clustering**

| Model | Mention F1 | Mention precision | Strict precision | Mention recall | Item×feature F1 | Polarity agr. | Hard: recall | Hard: polarity | Hard: feature | Quotes verified | Cues verified | Items not returned | Cluster purity | Inverse purity | Features found |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 1.00 | 1.00 (0.99–1.00) | 0.97 | 1.00 | 0.97 (0.96–0.98) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.97 (0.96–0.98) | 0.66 (0.65–0.67) | 31 (28–32) |
| `openai:gpt-6.1-terra` | 0.99 | 0.99 | 0.97 | 1.00 | 0.96 (0.95–0.97) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.96 (0.96–0.97) | 0.62 | 33 (32–34) |
| `openai:gpt-6.1-sol` | 1.00 (0.99–1.00) | 0.99 | 0.99 (0.98–0.99) | 1.00 | 0.96 (0.96–0.97) | 1.00 | 1.00 | 1.00 | 0.99 (0.97–1.00) | 1.00 | 1.00 | 0.0 | 0.97 (0.96–0.98) | 0.65 (0.65–0.66) | 29 (28–31) |

**Regression detection** (release and feature must both match the planted truth)

| Model | Regression precision | Regression recall | Improvement precision | Improvement recall | Traps flagged (of 3) | Raw-count baseline precision | Raw-count recall | Raw-count traps flagged | Cost (USD) | Time (s) | Wall (s) | Failed runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 1.00 | 1.00 | 0.89 (0.67–1.00) | 1.00 | 0.0 | 0.61 (0.50–0.67) | 1.00 | 1.0 | 0.015 | 262 (261–264) | 78 (75–80) | 0 of 3 |
| `openai:gpt-6.1-terra` | 1.00 | 1.00 | 1.00 | 0.67 (0.50–1.00) | 0.0 | 0.61 (0.50–0.67) | 1.00 | 1.0 | 0.093 (0.088–0.103) | 212 (211–212) | 64 (63–65) | 0 of 3 |
| `openai:gpt-6.1-sol` | 1.00 | 1.00 | 0.56 (0.50–0.67) | 0.67 (0.50–1.00) | 0.0 | 0.50 | 1.00 | 1.0 | 0.257 (0.245–0.276) | 218 (215–221) | 68 (66–69) | 0 of 3 |

Oracle (planted labels into the same detector): regression precision 1.00, recall 1.00; improvement precision 1.00, recall 1.00. Without de-duplication: regression precision 0.67. Raw-count rule: precision 0.50, recall 1.00 (false alarms: 3.1 ads, 3.3 pricing).
