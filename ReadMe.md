# LinkedIn Job Extractor

Local tool that parses **LinkedIn JSON API payloads** (typically copied from browser DevTools when job search results load). It does **not** scrape LinkedIn or handle authentication; you provide JSON, and it produces structured job rows.

## What it does

- **Parses** Voyager/Dash-style responses: job cards, postings, companies, locations, descriptions, and apply metadata.
- **Normalizes** fields such as title, company, location, workplace type (remote / hybrid / onsite), apply type and URL, ATS name, posted dates, and full description text.
- **Maps Easy Apply** style flows to a stable public job URL: `https://www.linkedin.com/jobs/view/{job_id}` when internal `job-apply` links would be awkward to open directly.

Core extraction: `extract.py`. Desktop UI: `linkedin_job_extracter.py` (Tkinter). Optional Windows executable: built with PyInstaller from `LinkedInJobExtractor.spec` → `dist/LinkedInJobExtractor.exe`.

## Requirements

- **Python 3** with the standard library, including **Tkinter** (for the GUI). On some Linux distributions you may need a package such as `python3-tk`.

No third-party packages are required for the scripts as shipped.

## How to get JSON from LinkedIn

1. Open LinkedIn in a desktop browser (e.g. Jobs search).
2. Open **Developer Tools** → **Network**.
3. Filter by **Fetch/XHR** (or similar) and trigger a load or scroll so job results refresh.
4. Select a request whose **response** is JSON containing job data (structure changes over time; look for large JSON bodies with job-related keys).
5. Copy the **response body** and paste it into the GUI, or save it to a file for the CLI workflow below.

If the payload is not a jobs search shape (or LinkedIn changes the schema), extraction may return **zero jobs** until the parser is updated.

## Using the GUI

From the project directory:

```bash
python linkedin_job_extracter.py
```

Or run the built executable:

```bash
dist\LinkedInJobExtractor.exe
```

1. Paste JSON into **Input LinkedIn JSON**.
2. Click **Extract**. Re-run **Extract** to **merge** another payload; duplicates are skipped (by posting URN, card URN, job id, apply URL, etc.).
3. Use **Filters** (multi-select with Ctrl/Shift) and **Apply filters** / **Reset**.
4. Click column headers to **sort**.
5. Select a row to see the full record as JSON in the details pane.
6. **Double-click** a row to open its apply URL in the default browser.
7. **Open visible apply URLs & remove those rows** opens http(s) links for visible rows, then removes those rows from the list (useful for triage).

**Clear** resets the input, table, and merged list.

## Using the command line (`extract.py`)

Defaults at the bottom of `extract.py`:

- Input: `test.json`
- Outputs: `extracted_jobs.json`, `extracted_jobs.csv`

1. Save your captured JSON as `test.json` in the project folder, or edit `INPUT_FILE` in `extract.py` to point at your file.
2. Run:

```bash
python extract.py
```

3. Open the generated JSON/CSV in the same directory.

## Building the Windows executable (optional)

With [PyInstaller](https://www.pyinstaller.org/) installed:

```bash
pyinstaller LinkedInJobExtractor.spec
```

The spec bundles `linkedin_job_extracter.py` as a windowed app named `LinkedInJobExtractor`.

## Getting Job Payload on Linkedin Site
https://www.linkedin.com/jobs/search/?keywords=developer&location=United States

## Project layout

| Path | Role |
|------|------|
| `extract.py` | Extraction logic and CLI entry point |
| `linkedin_job_extracter.py` | Tkinter GUI |
| `LinkedInJobExtractor.spec` | PyInstaller configuration |
| `dist/LinkedInJobExtractor.exe` | Pre-built GUI (if present) |

Sample outputs `extracted_jobs.json` / `extracted_jobs.csv` may appear after a run; they are normal artifacts of `extract.py`.

## License / compliance

Use only with data you are permitted to capture and process. LinkedIn’s terms of service and robots/API policies apply to how you obtain and use network payloads.
