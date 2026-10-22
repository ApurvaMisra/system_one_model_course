# Authentic recordings only

No provider responses are bundled because no API credentials were available during authoring. Do not interpret hypothetical math examples or unit-test fixtures as inference results.

Notebooks 02–07 call `run_case` with a visible callback containing the actual SDK request. Live runs write one JSONL record per request under `work/runs/`. Records include endpoint, requested/resolved model, timestamp, task/input configuration hash, raw response, answers/statuses, usage, trial, warmup and elapsed time. Authentication headers and keys are never part of the recording contract.

For replay, retain those files and set `COURSE_MODE=recorded` in `.env`, then restart the kernel. For a distributed class recording set, copy verified files to `recordings/runs/` and choose that directory in the notebook configuration cell. A missing or configuration-mismatched recording raises a visible error; there is no silent live fallback. Changed text, images, rubrics, model, or timing trial requires a new recording.

Replay retains original recorded elapsed time for provenance but is excluded from live latency summaries. Do not average playback speed into API latency. Share only records from synthetic course data, after inspecting them; never share private customer content.
