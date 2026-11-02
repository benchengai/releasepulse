### kestrel: 3 runs per model

Mean across successful runs, range in brackets. `a>b` extracts with a, and merges features and words requirements with b. Cost and time are per full pipeline run (every item extracted, aspects embedded and clustered, clusters merged and named, requirements worded). Time is the sum of call latencies; wall time is with 4 extraction calls in flight. Extraction outputs reused from `runs/bench/kestrel` (cost and time include the original extraction calls).

**Extraction and clustering**

| Model | Mention F1 | Mention precision | Strict precision | Mention recall | Item×feature F1 | Polarity agr. | Hard: recall | Hard: polarity | Hard: feature | Quotes verified | Cues verified | Items not returned | Cluster purity | Inverse purity | Features found |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 1.00 | 1.00 (0.99–1.00) | 0.97 | 1.00 | 0.97 (0.95–0.97) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.96 (0.95–0.98) | 0.83 (0.80–0.84) | 17 (15–18) |
| `openai:gpt-6.1-terra` | 0.99 | 0.99 | 0.97 | 1.00 | 0.95 (0.94–0.95) | 1.00 | 1.00 | 1.00 | 0.95 (0.92–1.00) | 1.00 | 1.00 | 0.0 | 0.95 (0.95–0.96) | 0.84 (0.81–0.88) | 18 (16–20) |
| `openai:gpt-6.1-sol` | 1.00 (0.99–1.00) | 0.99 | 0.99 (0.98–0.99) | 1.00 | 0.96 (0.94–0.97) | 1.00 | 1.00 | 1.00 | 0.97 (0.95–1.00) | 1.00 | 1.00 | 0.0 | 0.96 (0.95–0.97) | 0.86 (0.82–0.91) | 17 (15–18) |
| `openai:gpt-6-luna>openai:gpt-6.1-terra` | 1.00 | 1.00 (0.99–1.00) | 0.97 | 1.00 | 0.97 (0.95–0.98) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.97 (0.95–0.98) | 0.81 (0.80–0.84) | 18 (16–20) |
| `openai:gpt-6-luna>openai:gpt-6.1-sol` | 1.00 | 1.00 (0.99–1.00) | 0.97 | 1.00 | 0.97 (0.96–0.98) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.97 (0.96–0.98) | 0.87 (0.85–0.88) | 17 (15–18) |

**Regression detection** (release and feature must both match the planted truth)

| Model | Regression precision | Regression recall | Improvement precision | Improvement recall | Traps flagged (of 3) | Raw-count baseline precision | Raw-count recall | Raw-count traps flagged | Cost (USD) | Time (s) | Wall (s) | Failed runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `openai:gpt-6-luna` | 1.00 | 1.00 | 1.00 | 0.83 (0.50–1.00) | 0.0 | 0.50 | 1.00 | 1.7 (1.0–2.0) | 0.016 (0.015–0.016) | 274 (270–276) | 21 (19–23) | 0 of 3 |
| `openai:gpt-6.1-terra` | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.50 | 1.00 | 2.0 | 0.097 (0.092–0.107) | 219 (218–220) | 12 (12–13) | 0 of 3 |
| `openai:gpt-6.1-sol` | 1.00 | 1.00 | 1.00 | 1.00 | 0.0 | 0.50 | 1.00 | 1.7 (1.0–2.0) | 0.264 (0.250–0.284) | 228 (225–232) | 18 (16–20) | 0 of 3 |
| `openai:gpt-6-luna>openai:gpt-6.1-terra` | 1.00 | 1.00 | 1.00 | 0.83 (0.50–1.00) | 0.0 | 0.50 | 1.00 | 1.7 (1.0–2.0) | 0.021 (0.020–0.021) | 265 (262–269) | 13 (12–13) | 0 of 3 |
| `openai:gpt-6-luna>openai:gpt-6.1-sol` | 1.00 | 1.00 | 1.00 | 0.83 (0.50–1.00) | 0.0 | 0.50 | 1.00 | 2.0 | 0.027 (0.027–0.028) | 269 (266–274) | 16 (15–17) | 0 of 3 |

Oracle (planted labels into the same detector): regression precision 1.00, recall 1.00; improvement precision 1.00, recall 1.00. Without de-duplication: regression precision 0.67. Raw-count rule: precision 0.50, recall 1.00 (false alarms: 3.1 ads, 3.3 pricing).
