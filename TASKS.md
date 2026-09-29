# TASKS

Tick items as they pass tests. Work top to bottom. One slice at a time.

## Slice 0: setup
- [x] venv, `pip install -r requirements.txt`, `streamlit run app.py` shows hello
- [x] LLM key test (`.env`): one JSON call, one Urdu paragraph
- [x] Urdu PDF spike: render "سکیورٹی واقعے کی رپورٹ INC-007 192.0.2.5"; check ٹ ڈ ڑ ں ھ ے join, IDs stay LTR; pick ReportLab vs WeasyPrint

## Slice 1: upload mode, single table (earliest scored metrics)
- [x] `upload/infer.py`: types, PK guess
- [x] `upload/classify.py`: id/categorical/numeric/datetime/name/text (heuristics, LLM optional on names only)
- [x] `upload/fit.py` + `sample.py`: GaussianCopula, seeded
- [x] `evaluate/fidelity.py`
- [x] `evaluate/utility.py` (TSTR/TRTS/TRTR)
- [x] `evaluate/privacy.py`
- [x] `evaluate/runs.py`: scorecard row per run
- [x] Streamlit Create page: upload -> generate -> scorecard

## Slice 2: scenario core (auth)
- [x] `rng.py`, `plan.py` (models, presets, clamps)
- [x] `world.py`, `background.py` (auth)
- [x] `attacks.py`: 3 auth scenarios + hard negatives, difficulty dial
- [x] `detect.py`: rules, alerts, correlator, incidents, indicators
- [x] `validate.py` + `tests/test_integrity.py`
- [x] `export.py`: CSV, JSON, SQLite, manifest, dataset hash, `test_repro.py`

## Slice 3: cross-domain
- [x] Email + email_events (thin), endpoint process_events (thin)
- [x] Kill chain scenario across all three
- [x] Off-hours privilege change, impossible travel

## Slice 4: documents and LLM
- [x] `llm.py`: client, cache, fallback, output validation
- [x] LLM planner + preset plans
- [x] `report.py`: English incident PDF (facts from DB, narrative from LLM/template)
- [x] Phishing text generation

## Slice 5: Urdu
- [x] `data/names_ur.json`, `data/enums_ur.json` (proofread by hand)
- [x] `localize.py`: `_ur` columns, Urdu CSV view (`utf-8-sig`)
- [x] Urdu incident PDF
- [x] Urdu narrative + validation (script present, IDs preserved)
- [x] UI language toggle (RTL CSS)

## Slice 6: UI polish
- [x] Data, Explore (describe, nulls, Plotly charts, overlays), Quality, Runs pages
- [x] Lineage page
- [x] Dataset card + downloads

## Slice 7: extras (in order)
- [x] NL query (`query.py`) + canned queries
- [x] Multi-table upload with confirmed PK/FK
- [x] Calibration from upload/public stats
- [x] CTGAN/TVAE baseline on scorecard
- [x] Membership inference, run comparison chart

## Final
- [x] Two clean full demo run-throughs
- [x] README with run steps and demo script
- [x] LLM-off run verified
