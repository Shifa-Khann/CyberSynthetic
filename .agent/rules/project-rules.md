# Project rules (always on)

Follow `AGENTS.md` at the repo root. Key points:

- LLM never generates rows, IDs, timestamps, IPs, FKs, counts, severities, or labels.
- All randomness through `engine/rng.py`.
- Everything must work with the LLM off.
- Never send uploaded rows to an external API.
- Synthetic-only: reserved IP ranges, example domains, placeholder payloads.
- Run `pytest tests/ -q` after touching `engine/`.
- Work one slice from `TASKS.md` at a time; tick it when tests pass.
- Consult `TRD.md` before changing schema or pipeline.
