# UI and Urdu rules (apply when editing app.py, pages/, engine/localize.py, engine/report.py)

- Streamlit only. No separate frontend build.
- Urdu is a render-time layer: never change canonical columns; add `_ur` columns and separate exports.
- CSV exports use `utf-8-sig`.
- Urdu PDFs: `arabic-reshaper` + `python-bidi`, Noto Naskh Arabic font, IDs/IPs/timestamps stay left-to-right.
- Name and enum banks in `data/*.json` are frozen and hand-proofread. Do not regenerate them at runtime.
- Urdu LLM text must contain Urdu script and preserve every ID and number from the facts; retry once, then use the template.
- RTL UI via CSS `direction: rtl` and an Urdu font inside `st.markdown(..., unsafe_allow_html=True)`.
- Show the scorecard on the Quality page with pass/warn colors; always show reference source and dataset hash.
