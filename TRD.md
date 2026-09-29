# TRD: CyberSynthetic

## 1. Stack
Python 3.11, pandas, NumPy, SciPy, scikit-learn, Pydantic v2, Faker, SDV (GaussianCopula; CTGAN/TVAE optional), SDMetrics (scoring only), SQLite, ReportLab + arabic-reshaper + python-bidi (+ Noto Naskh Arabic), Plotly, Streamlit, `openai` SDK pointed at Gemini's OpenAI-compatible endpoint (OpenRouter secondary). Verify current model names and limits before use.

## 2. Pipeline
```
NL request -> LLM planner (fallback: preset) -> Plan JSON -> Pydantic validator
seed -> SeedSequence(seed).spawn(n): one child RNG per stage
1 WORLD       users, devices, per-user baselines
2 BACKGROUND  auth_events, email_events, process_events (normal)
3 ATTACKS     kill chains + benign look-alikes
4 DETECTION   rules -> alerts; correlator -> incidents, indicators
5 LABELS      label, scenario_id, MITRE tag
6 VALIDATE    PK/FK, temporal order, derived values (fail loudly)
7 LOCALIZE    Urdu columns from name bank + enum dictionary
8 RENDER      CSV/JSON, SQLite, PDF (facts + narrative)
9 EVALUATE    integrity, fidelity, utility, privacy
10 RUN RECORD runs table: seed, plan hash, dataset hash, calibration source, scores
```
Upload mode: CSV -> infer schema -> classify columns -> fit -> sample -> validate -> evaluate -> export.

## 3. Schema (SQLite, real PK/FK)
```
users(user_id PK, username, full_name, full_name_ur, email, department, role,
      privilege_level, home_country, home_city, home_city_ur)
devices(device_id PK, hostname, os, ip_address, owner_user_id FK, criticality)
auth_events(event_id PK, ts, user_id FK, device_id FK, src_ip, geo_country, geo_city,
            auth_method, outcome, label, scenario_id)
emails(email_id PK, ts, sender, recipient_user_id FK, subject, body_text, language, label, scenario_id)
email_events(email_event_id PK, email_id FK, user_id FK, ts, event_type)
process_events(event_id PK, ts, device_id FK, user_id FK, process_name, parent_process,
               command_line, label, scenario_id)
alerts(alert_id PK, ts, rule_id, alert_type, severity, user_id FK, device_id FK,
       source_table, source_event_id, incident_id FK NULL, status)
incidents(incident_id PK, start_time, end_time, severity, status, victim_user_id FK,
          primary_device_id FK, mitre_tactics, scenario_id)
indicators(indicator_id PK, incident_id FK, type, value)
runs(run_id PK, created_at, seed, plan_hash, dataset_hash, mode, calibration_source, scores_json)
```
Rules:
- `event.ts <= alert.ts`; `incident.start_time = min(alert.ts)`; `end_time >= max(alert.ts)`; `severity = max(alert severity)`. All derived in code.
- `alerts.source_event_id` spans several tables: SQLite cannot enforce it, `validate.py` does.
- One event may trigger several alerts.

## 4. Plan schema (Pydantic)
Fields: `mode`, `seed`, `duration_days` (1-90), `users` (1-2000), `devices` (1-1000), `ratios` (normal/suspicious/malicious, sum to 1), `difficulty` (easy|medium|hard), `domains` (auth/email/endpoint), `scenarios[]`, `language` (en|ur|both), `generate_documents`, `use_llm`, `calibration_profile`. Clamp out-of-range values; reject unknown fields.

## 5. Generation
- Background: per-user hour-of-day profile (weekday/weekend), Poisson counts, failure rate about 2-5%, mostly own device. Parameters come from `calibration_profile.json`.
- Scenarios: failed-login burst then success (T1110); impossible travel; new device at odd hour on privileged account; phish -> click -> encoded PowerShell placeholder -> new service -> new-IP login; off-hours privilege change.
- Hard negatives: business travel, forgotten password, new laptop, admin patch window, newsletter click.
- Difficulty dial: stealth and hard-negative rate.
- Detection: 6 simple rules; correlator groups alerts by user/device inside a time window.

## 6. Calibration profile
`data/calibration_profile.json`: hour histograms, per-user rates, failure rate, category frequencies, correlations, `source` field (`upload|public:<name>|expert_prior`). Only statistics, never raw rows.

## 7. LLM
`engine/llm.py`: one client, JSON mode, retry once, cache in `cache/{sha256(prompt+facts)}.json`, template fallback. Jobs: plan, column semantics (names/stats only), phishing text, incident narrative (en/ur), expert priors, NL-to-SQL. Validate outputs: Urdu text must contain Urdu script and every ID/number from the facts unchanged.

## 8. Urdu
- Frozen JSON banks: `data/names_ur.json` (English/Urdu name and city pairs, about 200, hand-proofread), `data/enums_ur.json` (about 50 terms).
- CSV: `utf-8-sig`. Urdu view export with Urdu headers.
- PDF: ReportLab + reshaper + bidi + Noto Naskh; IDs/IPs stay LTR. Spike first; fallback on Windows: render HTML to PDF with headless Edge (`msedge --headless --print-to-pdf=out.pdf file.html`). Avoid WeasyPrint on Windows (GTK/Pango).
- UI: RTL CSS and Urdu font via `st.markdown(unsafe_allow_html=True)`.

## 9. Evaluation (`engine/evaluate/`)
- integrity: PK uniqueness, FK validity, temporal order, derived values, label ratios.
- fidelity: KS complement, TV complement, correlation similarity, pair-trend (SDMetrics or SciPy).
- utility: per-event malicious-vs-not; features from rolling stats; TSTR, TRTS, TRTR; F1, PR-AUC, AUROC; TSTR/TRTR ratio. Real reference = uploaded data / public dataset stats; otherwise a differently seeded proxy labeled "proxy".
- privacy: exact-match rate, DCR with holdout baseline, nearest-neighbor ratio, synthetic-safety lint. Wording: "empirical risk indicators", never guarantees.
- runs: each generation saves a scorecard row.

## 10. Exports
`outputs/{run_id}/`: `csv/`, `csv_ur/`, `json/`, `db.sqlite`, `reports/INC-*.pdf` (+ `_ur`), `eval_flat.csv` with train/test split, `manifest.json`. Dataset hash = SHA-256 over sorted CSV bytes.

## 11. NL query
Schema + table descriptions + few-shot examples in prompt; validate with `sqlglot` or a regex allowlist; run read-only (`file:...?mode=ro`); forced LIMIT; show SQL; canned queries as fallback.

## 12. UI (Streamlit)
Tabs/pages: Create (NL box or CSV upload, seed, difficulty, language, LLM toggle) | Data | Explore | Quality | Ask | Lineage | Runs. Language toggle in sidebar.

## 13. Modules
```
engine/plan.py       Pydantic models, presets, LLM planner
engine/rng.py        SeedSequence tree
engine/world.py      users, devices, profiles
engine/background.py normal auth/email/endpoint
engine/attacks.py    scenarios + hard negatives
engine/detect.py     rules, alerts, correlator, indicators
engine/validate.py   integrity checks
engine/localize.py   Urdu layer
engine/export.py     CSV, JSON, SQLite, manifest
engine/report.py     PDFs
engine/llm.py        client, cache, fallback
engine/query.py      NL-to-SQL
engine/upload/       infer.py, classify.py, fit.py, sample.py
engine/evaluate/     fidelity.py, utility.py, privacy.py, runs.py
```

## 14. Testing
`tests/test_integrity.py` (PK/FK/temporal/derived), `test_repro.py` (same seed same hash, different seed different hash), `test_llm_off.py`, `test_urdu.py` (script present, IDs preserved), `test_safety.py` (reserved IPs, example domains), `test_query.py` (rejects non-SELECT).
