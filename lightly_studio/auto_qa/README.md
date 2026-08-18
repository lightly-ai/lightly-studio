# Automatic QA

This package screens video deliveries stored in GCS.

Run commands from the Python project directory:

```bash
cd lightly_studio
```

```text
GCS discovery -> download -> optional Whisper -> deterministic QA -> result upload -> cleanup
```

## Modules

- `pipeline.py`: CLI and batch lifecycle.
- `storage.py`: GCS discovery, download, and local cleanup.
- `transcribe.py`: Optional faster-whisper subprocess.
- `screen.py`: Video ingestion and deterministic QA checks.
- `results.py`: Result JSON construction and upload.

`sample_gcs_review.py` is a separate workflow. Automatic QA does not import it.

Results use the existing flat `<stem>_results.json` contract. If the same bucket and stem
exist under multiple prefixes, the first requested prefix wins. With the defaults, `review`
takes priority over `pool`.

## Usage

Preview work without downloading anything:

```bash
uv run --extra cloud-storage python -m auto_qa --dry-run
```

Process and publish results using existing transcripts:

```bash
uv run --extra cloud-storage python -m auto_qa --apply
```

Generate transcripts when they are missing:

```bash
uv run --extra cloud-storage python -m auto_qa --apply --transcribe-missing
```

Whisper is off unless `--transcribe-missing` is present. Qwen classification is not part of
this pipeline. Uploaded records retain the existing schema-v2 contract; Qwen-related checks
are reported as `not_run` when no historical classification metadata exists.

Python 3.9 still runs the pipeline, but current Google libraries print end-of-life warnings.
Use Python 3.10 or newer when the project environment is next upgraded.

Downloads use four concurrent workers by default. Override the bounded concurrency with
`--download-workers`; phase timings in the command output report download, screening, result
building, and result upload separately.
