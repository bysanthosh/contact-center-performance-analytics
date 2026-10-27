# Contact Center Operational Analytics & ETL Pipeline

A reproducible portfolio project that simulates a contact-center analytics workflow using **Python, pandas, SQL, SQLite, pytest, and Power BI**. All input data is synthetic; no employer or customer data is used.

See `DATASET_SUMMARY.md` for the verified dataset totals, ASA range, and Power BI import instructions.

## Business problem

Contact-center teams need reliable reporting on call volume, handling efficiency, service level, abandonment, IVR containment, and team performance. Before producing KPIs, source data must be normalized, deduplicated, validated, reconciled, and loaded consistently.

## Architecture

```text
Synthetic raw CSVs
       |
       v
Extract + required-column checks
       |
       v
Normalize fields and timestamps
       |
       v
Choose latest version per call_id
       |
       v
Validate business rules ---- invalid records ---> Quarantine CSV
       |
       v
Accepted records
       |
       v
SQLite snapshot: fact_calls + dim_agents
       |
       +---- SQL KPI / agent / time / reconciliation analysis
       |
       +---- Power BI dashboard (see powerbi/ when available)
```

## Technology

- Python 3.10+
- pandas
- SQLAlchemy
- SQLite
- SQL
- pytest
- Power BI Desktop (dashboard layer)

## Quick start (Windows CMD)

Run commands from the project root (the folder containing `src`, `sql`, and `data`).

```cmd
python -m pip install -r requirements.txt
python src\generate_data.py --calls-per-month 5000 --start-year 2024 --months 36
python src\pipeline.py
python -m pytest -q
```

The data generator is deterministic and creates **180,000 base calls** (5,000 per month) from **January 2024 through December 2026**, plus approximately 1% duplicate versions and 0.5% intentional data-quality defects. Handled-call wait times are generated to produce an ASA generally around 60–90 seconds. All records are synthetic. The ETL pipeline writes:
- `data/processed/calls_validated.csv`
- `data/quarantine/calls_quarantine.csv`
- `data/contact_center.sqlite`
- `reports/data_quality_report.json`
- `logs/pipeline.log`

Runtime outputs are excluded from Git by `.gitignore`; regenerate them with the commands above.

## Database tables

| Table | Grain | Purpose |
|---|---|---|
| `fact_calls` | One accepted canonical call per `call_id` | Call timestamps, outcome flags, wait and handling durations |
| `dim_agents` | One row per agent | Agent, team, and site attributes |

Example query:

```sql
SELECT
    a.team_name,
    COUNT(*) AS handled_calls,
    ROUND(AVG(f.talk_seconds + f.hold_seconds + f.after_call_work_seconds), 2)
        AS avg_handling_seconds
FROM fact_calls AS f
JOIN dim_agents AS a ON f.agent_id = a.agent_id
WHERE f.handled_flag = 1
GROUP BY a.team_name
ORDER BY handled_calls DESC;
```

Run the prepared queries in `sql/` against the SQLite database. See `sql/README.md` for details.

## Data-quality and reconciliation rules

- Normalize column names, whitespace, categories, timestamps, and numeric fields.
- For duplicate versions of a non-empty `call_id`, select the latest valid `updated_at`; when timestamps tie, the last source row wins.
- Retain rows without a call ID for record-level validation so they can be quarantined rather than silently discarded.
- Quarantine invalid timestamps, invalid outcomes/channels, inconsistent flags, invalid durations, and invalid agent references.
- A handled call must reference an agent in `dim_agents`.
- Abandoned and IVR-contained calls can have no agent assigned.
- Reconcile canonical rows to accepted plus rejected rows.
- Reconcile accepted rows to rows loaded into `fact_calls`.

## KPI definitions

| KPI | Definition used in this project |
|---|---|
| Offered calls | Sum of `offered_flag` across accepted calls |
| Handled calls | Sum of `handled_flag` |
| Abandonment rate | Abandoned calls / offered calls |
| IVR containment rate | IVR-contained calls / offered calls |
| Average handling time (AHT) | Average of talk + hold + after-call work seconds for handled calls |
| Service level | Handled calls meeting the configured wait threshold / all offered calls; abandoned calls remain in the denominator |

Rates should be treated as undefined when the denominator is zero. These are explicit portfolio definitions, not universal definitions for every contact center.

## Example run results

With the included deterministic synthetic data and current validation rules, the expected pipeline summary is:

| Measure | Expected value |
|---|---:|
| Base calls generated | 180,000 (5,000/month) |
| Raw source rows | 181,800 (includes duplicate versions) |
| Duplicate versions removed | 1,800 |
| Canonical rows evaluated | 180,000 |
| Expected rejected canonical rows | 892 |
| Expected accepted / loaded rows | Approximately 179,100 |
| Agent dimension rows | 100 |

Outcome proportions are generated to approximate 72% handled, 16% abandoned, and 12% IVR-contained before intentional data-quality defects. ASA is based on answered/handled calls and is designed to average approximately 60–90 seconds. For this included seed, overall accepted handled-call ASA is 76.60 seconds, monthly ASA ranges from 75.82 to 77.21 seconds, and accepted offered volume averages about 4,975 calls per month after quarantine. Exact totals may differ if the seed or generator settings change. Results are synthetic and intended only to demonstrate analysis patterns.

## Testing

Run:

```cmd
python -m pytest -q
```

The test suite checks normalization, canonical record selection, validation/quarantine behavior, and SQLite loading. See `docs/TESTING.md`.

## Repository layout

```text
.
├── data/
│   ├── raw/                 # Synthetic input CSVs
│   ├── processed/           # Generated accepted records (ignored by Git)
│   └── quarantine/          # Generated rejected records (ignored by Git)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_DICTIONARY.md
│   └── TESTING.md
├── logs/                    # Runtime logs (ignored by Git)
├── powerbi/                 # Dashboard assets/instructions added in next phase
├── reports/                 # Runtime quality report (ignored by Git)
├── sql/                     # KPI, agent, time, and reconciliation queries
├── src/                     # ETL implementation
└── tests/                   # Automated tests
```

## Limitations and next steps

- This is a local, synthetic-data portfolio project, not a production service.
- SQLite is used to make the project easy to run without a database server or credentials.
- Power BI refresh and dashboard configuration are environment-specific.
- A production implementation would add orchestration, alerting, incremental loads, access controls, and monitoring.
