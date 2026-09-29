# CyberSynthetic: agent rules

Read this file first, every session. Keep changes small and slice-based.

## Project
Synthetic data platform for HackDataV2. Two modes:
1. **Scenario mode**: natural-language request -> validated plan -> one consistent cybersecurity world (auth, email, endpoint, alerts, incidents) -> CSV / JSON / SQLite / PDF (English + Urdu).
2. **Upload mode**: user uploads CSV(s) -> schema inference -> fitted generator -> similar synthetic data.

Judged on: fidelity, TSTR/TRTS utility, system design, features, UI, AI use. Every generation writes a scorecard row.

Docs: `PRD.md` (what/why), `TRD.md` (how), `TASKS.md` (checklist). Consult TRD before changing schema or pipeline.

## Hard rules (never break)
1. The LLM NEVER generates rows, IDs, timestamps, IPs, foreign keys, counts, severities, or labels. It only produces: plan JSON, column-semantics guesses (from names/stats only), free text (phishing emails, incident narrative, Urdu text), expert priors, and NL-to-SQL.
2. All randomness goes through `engine/rng.py` (SeedSequence tree, one child RNG per stage). No bare `random`, `np.random.*` globals, or `uuid4`.
3. Same seed + same plan => same dataset hash. Different seed => different valid dataset.
4. Every feature must work with the LLM OFF (presets + templates). The LLM is an enhancement.
5. Never send uploaded data rows to any external API. Column names and summary statistics only.
6. All generated security data is synthetic: reserved IP ranges (10.0.0.0/8, 192.168.0.0/16, 203.0.113.0/24, 198.51.100.0/24, 192.0.2.0/24), `example.com/.org` email domains, placeholder command lines like `powershell.exe -enc <SYNTHETIC_BLOB>`. No real credentials, keys, tokens, or working payloads.
7. Canonical-then-localize: IDs, timestamps, IPs, enums, numbers stay canonical. Urdu is a render-time layer (`_ur` columns, Urdu PDF, UI toggle).
8. NL-to-SQL runs on a read-only SQLite connection, a single SELECT only, forced LIMIT.
9. Utility features must exclude label-leaking columns (`alert_type`, `scenario_id`, `label`, incident/alert ids).
10. Report F1, PR-AUC, AUROC for imbalanced data. Never accuracy alone.
11. Run `pytest tests/` after any change to `engine/`. It must stay green before you continue.
12. Build vertical slices. Do not scaffold empty modules or add features not in `TASKS.md`.

## Workflow
- One slice at a time: implement -> test -> commit -> tick `TASKS.md`.
- Prefer existing libraries (pandas, NumPy, SciPy, scikit-learn, SDV, SDMetrics, Faker, ReportLab) over custom algorithms.
- Small functions, type hints, docstrings on public functions. Config lives in Pydantic models, not scattered constants.
- If a task will take more than about 45 minutes, stop and split it.
- If a requirement is unclear, ask instead of guessing.

## Commands
```
pip install -r requirements.txt
pytest tests/ -q
streamlit run app.py
```

## Layout
```
app.py            Streamlit entry
pages/            Streamlit pages
engine/           generation, validation, export, evaluation
engine/upload/    CSV schema inference and fitted generators
engine/evaluate/  fidelity, utility, privacy, runs
data/             name bank, enum dictionary, calibration profiles
tests/            pytest
outputs/          per-run outputs (gitignored)
cache/            LLM response cache (gitignored)
```
