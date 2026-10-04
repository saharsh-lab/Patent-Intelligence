# EPO OPS test fixtures

These JSON files are **hand-made** to follow the OPS v3.2 JSON format
(XML converted to JSON: text under `"$"`, attributes under `"@name"`, single-item
lists collapsed to objects). The patents they describe are fictional.

Once EPO credentials are configured, run

    cd backend && .venv/bin/python -m scripts.record_epo_fixtures

to save real responses next to these (`recorded_*.json`) and check that the parser
handles them; the tests then also run against the recorded files.
