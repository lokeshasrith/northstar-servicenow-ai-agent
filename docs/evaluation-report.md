# Evaluation report

**Run date:** 2026-10-02 · **Model:** deterministic mock rules · **Dataset:** 11 labeled examples

| Measure | Result |
|---|---:|
| Classification accuracy | 100% (11/11) |
| Priority accuracy | 100% (11/11) |
| Escalation accuracy | 100% (11/11) |
| Confidence Brier score | 0.053 (lower is better) |
| Mean confidence | 84.4% |
| False autonomous resolutions | 0/11 |
| Human escalation or review | 10/11 |
| Simulated verified resolutions | 1/11 |
| Average resolution time | Not measured |

These are deterministic checks against a tiny, hand-labeled sample, not a statistically meaningful model evaluation. The false-autonomous measure here checks policy predictions against expected class and escalation labels; the one simulated verified case includes explicit recovery evidence. Neither is proof of real remediation. All actions and verification are mock-only. Expand the dataset with local incident examples and independently reviewed expected outcomes before drawing operational conclusions. The API endpoint `/api/evaluation` recomputes these values from the included dataset.
