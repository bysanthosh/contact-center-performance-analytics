# Testing Guide

## Install dependencies

From the project root:

```cmd
python -m pip install -r requirements.txt
```

## Run automated tests

```cmd
python -m pytest -q
```

To see individual test names:

```cmd
python -m pytest -v
```

## What is covered

- Header/category normalization and timestamp parsing.
- Selecting the latest version for a call ID and retaining missing-ID rows for validation.
- Quarantining invalid records and accepting valid records.
- Creating SQLite fact and dimension tables and verifying loaded row counts.
- Checking repeatable snapshot loading (rerunning the loader does not append duplicate rows).

## Manual end-to-end check

```cmd
python src\generate_data.py
python src\pipeline.py
```

Then inspect `reports\data_quality_report.json`. Expected synthetic-data counts are documented in the root README. The generated report is a runtime artifact and is ignored by Git.

## Interpreting failures

A failing test is a signal to inspect the relevant transformation or validation rule. Do not change expected values simply to make tests pass; first determine whether the implementation or the test expectation is wrong.
