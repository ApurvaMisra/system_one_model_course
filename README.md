# Building with Jev and System One Models

Local Jupyter companion for [Apurva Misra's O'Reilly course](https://www.oreilly.com/live-events/building-with-jev-and-system-one-models/0642572462482/).

Learn to choose typed judgments, compose support triage in Python, use screenshots, and compare Jev versions with OpenAI Decisions and Responses.

## Local setup

Use Python 3.11; tested with Python 3.11.11 on macOS. Windows/Linux setup commands are provided but have not been executed on those platforms.

Run these commands from the project folder. Choose **uv** or **pip**; both install the same pinned requirements into `.venv`.

### Option A: uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed.

macOS/Linux:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

Windows PowerShell:

```powershell
uv venv --python 3.11
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

### Option B: pip

macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Configure keys and launch Jupyter (both options)

With `.venv` still activated, register the course kernel:

```bash
python -m ipykernel install --prefix .venv --name jev-course --display-name "Python (Jev course)"
```

Copy `.env.example` to `.env` in the project folder if you have not already created it:

- macOS/Linux: `cp -n .env.example .env`
- Windows PowerShell: `if (!(Test-Path .env)) { Copy-Item .env.example .env }`

Edit `.env` locally and replace the blank values with your own keys:

```dotenv
TYPESAFE_API_KEY=your_jev_key
OPENAI_API_KEY=your_openai_key
COURSE_MODE=live
```

`OPENAI_API_KEY` is optional; leave it blank to skip the OpenAI examples in 04, 05, and 07. Do not commit credentials.

Launch JupyterLab:

```bash
python -m jupyterlab
```

Select **Python (Jev course)** and open `notebooks/00_setup.ipynb`. The environment uses TypeSafe SDK 0.7.5 and OpenAI SDK 3.35.1. Requirements pin the tested dependencies; platform-only packages use platform markers.

## Notebook order

| Notebook | Outcome |
|---|---|
| 00_setup | First request and environment check |
| 01_output_types | Choice, Score, Noul and how to interpret them |
| 02_triage_workflow | Human review, precision–recall thresholds, and normalized multi-score priority |
| 03_images_and_box | Image inputs, presence checks, bounding boxes |
| 04_openai_comparison | Both Jev versions versus OpenAI Decisions and Responses on the same input |
| 05_patterns | Tool routing, RAG relevance, output checks, hybrid generation |
| 06_reranking | Score and reorder candidate passages for the same query |
| 07_structured_information | Known fields with Jev; exact document/image text extraction with an optional LLM |

All notebooks contain worked examples, short explanatory comments, and exercises with interpretation guidance. Restart and run each independently. Output artifacts are written under ignored `work/`; source notebooks are distributed without API results or credentials.

## Model and API choices

Jev versions are pinned to `jev-1.13.0` and `jev-1.14.0`. Images require an experimental header; Box requires 1.14. OpenAI Decisions uses `gpt-6-luna`. The Responses baseline also uses `gpt-6-luna` with reasoning disabled for a focused-task comparison. The official model page provides this model ID rather than a dated snapshot; log the returned ID and execution date. Neither endpoint's name establishes better accuracy or speed.

Sources checked 2026-10-18: [TypeSafe SDK](https://docs.typesafe.ai/sdk/python), [images](https://docs.typesafe.ai/images), [models](https://docs.typesafe.ai/models), [OpenAI Decisions](https://developers.openai.com/api/docs/guides/decisions), [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

Offline verification covers tests, notebook syntax, and non-network execution. It does not establish live API integration or benchmark results; those require your own API keys.

## Run modes and charges

`COURSE_MODE=live` makes real calls and saves authentic results to `work/runs/`. `COURSE_MODE=recorded` replays those same configurations and fails clearly if files are missing. No recordings are bundled yet. See [recording instructions](recordings/README.md). Introductory notebooks 00–01 are live-only; later lessons support replay.

Notebook 04 makes up to eight requests per full run: four for one ticket and four for one screenshot, before retries. Change the selected example to explore further. Native probabilities are shown side by side; the LLM schema has no probability field.

Notebook 03 now analyses one chosen screenshot at a time. Notebook 06 scores four passages (four requests); notebook 07 makes two Jev requests and two optional OpenAI extraction requests. Counts exclude retries. Change the examples and rerun the relevant cells to explore further.

Notebook 07 reads a synthetic `.txt` document and a bundled PNG. Jev assigns known categories and probabilities; the optional LLM copies arbitrary source text into a schema. PDF/Word parsing and production OCR pipelines are outside this lesson. Inspect extracted fields against their sources; a valid schema does not prove correctness.

## Verification

```bash
python -m pytest -q
python scripts/validate_notebooks.py
# No network calls: run non-network cells in a fresh kernel per notebook.
python scripts/validate_notebooks.py --offline-check
# With keys configured; incurs API charges:
python scripts/validate_notebooks.py --execute --mode live
```

Validator exit codes: **0** requested checks complete, **1** static/execution failure, **2** notebook execution completed but API validation is incomplete. Offline-check intentionally returns 2. Executed copies and an audit summary go to `work/executed/`; source notebooks are never overwritten. A green offline run is not a live API integration test.

SDK wire-contract tests use explicitly synthetic responses in temporary test directories; these never enter course recordings or benchmark tables. Tests cover dataset splits, refusal handling, missing-answer denominators, unknown costs, review-all behavior, image geometry, and notebook request serialization.

If imports fail, check the selected kernel's `sys.executable`. If a provider returns 401/403, check account key/access. For 429, reduce calls and allow the bounded retry. For unavailable model/features, consult the linked official documentation and update configuration deliberately. `work/runs/` retains error class and HTTP status without saving potentially sensitive exception text.
