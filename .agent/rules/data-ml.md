# Data / ML rules (apply when editing engine/, engine/upload/, engine/evaluate/)

- Prefer pandas/NumPy vectorized generation over Python loops.
- Derived fields (incident start/end/severity, counts) are computed from records, never invented.
- Utility metrics: F1, PR-AUC, AUROC, TSTR/TRTR ratio. Exclude `alert_type`, `scenario_id`, `label`, incident/alert ids from features.
- Fidelity: KS complement, TV complement, correlation similarity, pair trends. Prefer SDMetrics; fall back to SciPy.
- Label the reference source on every scorecard: `upload`, `public:<name>`, `expert_prior`, or `proxy`.
- Privacy wording: "empirical risk indicators", never "guarantee" or "compliant".
- CTGAN/TVAE: cap rows and epochs (CPU only, 8 GB RAM). Default is GaussianCopula.
- Every function that samples takes an `rng: np.random.Generator` argument.
