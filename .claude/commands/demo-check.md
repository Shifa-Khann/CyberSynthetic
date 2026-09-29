---
description: Run the 5-minute demo checklist
---

1. `pytest tests/ -q` is green.
2. Start `streamlit run app.py`.
3. Enter the demo NL request; confirm the plan JSON shows and generation completes.
4. Quality page: integrity 100%, fidelity, TSTR/TRTS/TRTR, privacy shown with reference source.
5. Explore page: charts render.
6. Lineage: pick an incident; same IDs appear in CSV, SQLite query, and PDF.
7. Switch language to Urdu; open the Urdu PDF and check glyphs and LTR IDs.
8. Set difficulty to hard, regenerate; a new Runs row appears with lower utility.
9. Rerun the same seed; dataset hash matches.
10. Turn the LLM off and generate again.
11. Upload a CSV; generate similar data; scorecard appears.

Report any step that fails, with the error.
