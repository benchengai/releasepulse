### tallynote: 1 runs per model

Mean across successful runs, range in brackets. Cost and time are per full pipeline run (every item extracted, aspects embedded and clustered, requirements worded). Time is the sum of call latencies; wall time is with 4 extraction calls in flight.

**Extraction and clustering**

| Model | Mention F1 | Mention precision | Strict precision | Mention recall | Item×feature F1 | Polarity agr. | Hard: recall | Hard: polarity | Hard: feature | Quotes verified | Cues verified | Items not returned | Cluster purity | Inverse purity | Features found |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 1.00 | 1.00 | 0.99 | 1.00 | 0.99 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.99 | 0.89 | 21 |
| `openai:gpt-6.1-terra` | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 0.0 | 0.99 | 0.90 | 23 |
| `openai:gpt-6.1-sol` | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | 0.0 | 1.00 | 0.92 | 21 |

**Regression detection** (release and feature must both match the planted truth)

| Model | Regression precision | Regression recall | Improvement precision | Improvement recall | Traps flagged (of 3) | Raw-count baseline precision | Raw-count recall | Raw-count traps flagged | Cost (USD) | Time (s) | Wall (s) | Failed runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.40 | 1.00 | 2.0 | 0.015 | 252 | 78 | 0 of 1 |
| `openai:gpt-6.1-terra` | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.50 | 1.00 | 2.0 | 0.111 | 228 | 68 | 0 of 1 |
| `openai:gpt-6.1-sol` | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.50 | 1.00 | 2.0 | 0.294 | 215 | 69 | 0 of 1 |

Oracle (planted labels into the same detector): regression precision 1.00, recall 1.00; improvement precision 1.00, recall 1.00. Without de-duplication: regression precision 0.67. Raw-count rule: precision 0.50, recall 1.00 (false alarms: 2.2 dark_mode, 2.3 search).
