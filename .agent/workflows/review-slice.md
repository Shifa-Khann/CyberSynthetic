---
description: Review the latest changes against the hard rules
---

Check the diff against `AGENTS.md` hard rules:

1. Any LLM output used for rows, IDs, timestamps, IPs, FKs, counts, severities, or labels? Flag it.
2. Any `random`, `np.random.*` global, `uuid4`, or `time`-based seed outside `engine/rng.py`? Flag it.
3. Does the feature work with the LLM off?
4. Is any uploaded data sent to an external API?
5. Are IPs, emails, and command lines synthetic-safe?
6. Do utility features leak labels?
7. Do tests cover the change, and does `pytest tests/ -q` pass?
8. Same seed twice gives the same dataset hash?

Report findings as a short list: rule, file, line, fix. Do not modify code.
