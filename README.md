# CyberSynthetic Platform

Enterprise synthetic data engine for generating high-fidelity, RFC-compliant cybersecurity datasets from natural language prompts or uploaded CSV files. Features built-in statistical quality scoring, machine learning utility metrics, automated data profiling, and incident lineage tracing.

---

## Key Features

- **Dual Generation Modes**:
  - **Natural Language & Presets**: Synthesize complex cybersecurity scenarios from plain-text descriptions or pre-configured attack templates (e.g., APT lateral movement, brute-force authentication, ransomware).
  - **CSV Upload Mode**: Infer column schemas, data types, and roles locally from uploaded CSVs and fit generative architectures (Gaussian Copula, CTGAN, TVAE) for distribution-matched synthesis.

- **Multi-Modal Output Formats**:
  - **Tabular CSVs**: Single-table event logs.
  - **Relational Databases**: Multi-table SQLite databases enforcing primary and foreign key referential integrity across 7 core schemas (`users`, `devices`, `auth_events`, `process_events`, `email_events`, `alerts`, `incidents`, `indicators`).
  - **PDF Incident Reports**: Bilingual (English & Urdu) structured security incident reports.

- **Quantitative Quality Scorecard**:
  - **Fidelity Evaluation**: Kolmogorov-Smirnov (KS) complement, Total Variation (TV) distance, and pairwise correlation matrix similarity.
  - **Machine Learning Utility**: Train-on-Synthetic / Test-on-Real (TSTR), TRTS, and TRTR evaluation measuring classification F1, PR-AUC, and AUROC.
  - **Privacy Risk Protection**: Distance-to-Closest-Record (DCR) nearest-neighbor distance metrics and exact match verification.
  - **Safety Compliance**: Reserved IANA IP ranges (`10.0.0.0/8`, `192.168.0.0/16`, `203.0.113.0/24`) and domain placeholders (`example.com`). Zero real credentials or working attack payloads.

- **Incident Lineage Explorer**:
  - End-to-end 5-stage attack chain visualization tracing initial telemetry events through correlated detection alerts, incident impact, targeted entity context (users and assets), and indicators of compromise (IOCs).

- **Deterministic Reproducibility**:
  - Seeded generation tree using NumPy `SeedSequence`. Identical seed and plan parameters guarantee exact dataset SHA-256 signatures.

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Git

### Quickstart

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Shifa-Khann/CyberSynthetic.git
   cd CyberSynthetic
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration** *(Optional)*:
   ```bash
   copy .env.example .env
   ```
   Add your LLM API credentials if enabling optional LLM prompt planning.

5. **Run the Application**:
   ```bash
   streamlit run app.py
   ```
   Open `http://localhost:8501` in your browser.

---

## Running Tests

Run the unit test suite with pytest:

```bash
pytest tests/ -q
```

---

## Project Structure

```
app.py              Streamlit platform entry point
pages/              Streamlit page modules (Create, Data, Quality, Runs, Ask, Lineage)
engine/             Core generation, validation, export, LLM, and evaluation logic
engine/upload/      CSV schema inference, column classification, and model fitting
engine/evaluate/    Statistical fidelity, ML utility, privacy risk, and run audit logs
data/               Name banks, enum dictionaries, and calibration profiles
tests/              Pytest test suite
```

---

## Documentation

- **`PRD.md`**: Product Requirements Document (Goals, Scenarios, Safety Requirements)
- **`TRD.md`**: Technical Requirements Document (Schemas, Data Pipeline Architecture)
- **`TASKS.md`**: Development Checklist and Implementation History
