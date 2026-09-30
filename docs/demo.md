# Hackathon demo walkthrough

## Before presenting

1. Follow [local setup](setup.md) and start with `python scripts/run_dev.py`.
2. Open `http://127.0.0.1:8000/ui/` and confirm the status reads **API connected**.
3. For a live demonstration, configure valid `TAVILY_API_KEY` and choose a working real geocoder. For durable saved records, configure Supabase and apply all four migrations. Restart the app after environment changes.
4. Submit a small research question and inspect the returned execution mode, skipped/completed stages, limitations, source links, map, charts, and report. Use only information and coordinates actually returned by configured providers.

## Demo question

```text
Analyze cardiac healthcare infrastructure within 10 km of Whitefield and identify potential service gaps.
```

The area and radius are parsed from this wording. Do not claim that the default local setup found real facilities: with no Tavily key, it returns `unconfigured`, zero search sources, skipped search/extraction, and geocoding may be unavailable. The app must not fill those gaps with invented hospital records or coordinates.

## Test-only synthetic pipeline

The automated end-to-end test injects synthetic provider and page content and labels the run `mock`. This validates the request, pipeline stages, IDs, source traceability, explicit conflict retention, geographic calculations, report, and in-memory table writes without network access:

```bash
python -m pytest backend/tests/test_pipeline_e2e.py -q
```

These mock fixtures are not demo facts and must not be shown or described as real research. The frontend’s “clearly-labelled demo mode” button is layout-only, contains no facility data, and is not an end-to-end data source.

## Suggested presentation flow

1. Submit the query and point out its research ID, execution mode, and per-stage status.
2. Show facilities/services only if sources support them; click source links to open original pages.
3. Show the target and distances only when backend coordinates are available; explain any coordinate/geocoding limitation.
4. Review evidence statuses and both sides of any detected conflict.
5. Explain a service-gap assessment as a cautious inference from available evidence, not proof of service absence.
6. Generate/print the dossier and call out methodology and limitations.
