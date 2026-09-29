# PRD: CyberSynthetic

## Problem
Real security data is sensitive, scarce, and slow to obtain. Detection teams need labeled, realistic, shareable data. Generic synthetic tools produce valid-looking rows but no coherent story across tables or documents.

## Product
A schema-aware synthetic data platform with a deep cybersecurity domain pack and a generic CSV-upload mode. Outputs tabular, relational, and document data in English and Urdu, and scores every generation.

## Users
- Hackathon judges (fidelity, TSTR/TRTS, system design, features, UI, AI).
- Security engineers testing detections.
- Developers who need safe test data.

## Modes
### Scenario mode
- NL request -> validated plan -> consistent world.
- Domains: authentication (full depth), email/phishing (thin), endpoint (thin).
- Records link: user -> device -> events -> alerts -> incident -> report.
- One incident appears identically in CSV, SQLite, and PDF.

### Upload mode
- Upload one or more CSVs.
- Infer types, PKs, FKs; user confirms in the UI.
- Fit generator (GaussianCopula default; CTGAN/TVAE optional), generate N rows with a seed.
- Multi-file uploads keep FK validity.

## Shared capabilities
- Seeded reproducibility with dataset hash.
- Normal / suspicious / malicious ratios, difficulty dial (easy/medium/hard) with benign look-alikes.
- Calibration profile (fitted from upload/public data, or expert priors; scorecard states which).
- Urdu output: tabular (`_ur` columns, Urdu CSV view), relational, documents (Urdu PDF), UI toggle.
- Evaluation per run: integrity, fidelity, utility (TSTR/TRTS/TRTR), privacy, label balance. Runs history.
- EDA and charts on any generated table.
- Natural-language query over generated data: SQL shown, results as table and chart, canned fallback queries.
- Lineage explorer: incident -> alerts -> events -> user -> device -> report.
- Exports: CSV, JSON, SQLite, PDF, flat evaluation-ready table with train/test split, manifest.
- Fallback without LLM.

## Must build
1. Upload mode single-table: infer, fit GaussianCopula, generate, score.
2. Scorecard: fidelity, TSTR/TRTS/TRTR, privacy, integrity; saved per run.
3. Scenario world: auth, alerts, incidents, labels, hard negatives.
4. Email and endpoint thin streams and the kill chain.
5. CSV + SQLite + PDF export; English and Urdu PDF.
6. Urdu localization layer (name bank, enum dictionary).
7. LLM planner with preset fallback.
8. Streamlit UI: Create, Data, Explore, Quality, Runs.
9. Charts and EDA.

## If time allows
Lineage polish, NL query, multi-table upload, CTGAN/TVAE baseline comparison, membership inference, run comparison chart, DP-noised calibration.

## Cut
SDV multi-table HMA, RTL beyond the PDF, API mock server, GraphQL, Docker/cloud, other domains.

## Success criteria
- Demo in 5 minutes: request -> generate -> scorecard -> explore -> lineage -> Urdu PDF -> rerun same seed (same hash) -> LLM off still works.
- Integrity checks at 100%.
- TSTR/TRTR ratio reported honestly; proxy references labeled as proxy.

## Risks
- Fidelity vs own assumptions proves little; label calibration source.
- Utility inflated by label leakage; use hard negatives and exclude leaking columns.
- CTGAN slow on CPU; cap rows/epochs.
- Urdu PDF shaping; do the rendering spike first.
- Multi-table FK auto-detection; user confirms.
