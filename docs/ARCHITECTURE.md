# Architecture and Data Flow

## Processing stages

1. **Generate / extract:** `src/generate_data.py` creates deterministic synthetic CSV files. `src/extract.py` checks file existence and required columns.
2. **Normalize:** `src/transform.py` standardizes column names, whitespace, categories, timestamps, and numeric fields.
3. **Canonicalize:** Duplicate versions are grouped by non-empty `call_id`. The latest valid `updated_at` is preferred; source row order resolves ties.
4. **Validate:** `src/validate.py` applies record-level rules and creates a delimited `validation_reasons` field for rejected rows.
5. **Quarantine:** Rejected canonical records are written to `data/quarantine/calls_quarantine.csv` for review.
6. **Load:** `src/load.py` replaces the SQLite snapshot transactionally and writes `fact_calls` and `dim_agents`.
7. **Reconcile:** `src/pipeline.py` checks that canonical rows equal accepted plus rejected rows, and accepted rows equal loaded rows.
8. **Analyze:** SQL scripts calculate KPIs, team/agent performance, time trends, and reconciliation checks.

## Data model

- `fact_calls`: one accepted canonical record per call ID.
- `dim_agents`: one row per agent ID.
- `fact_calls.agent_id` joins to `dim_agents.agent_id` for assigned/handled calls. Abandoned and IVR-contained calls may have no agent.

## Repeatability

The generator uses a fixed random seed. Each ETL run replaces the database tables in a transaction rather than appending duplicate records. This creates a repeatable snapshot from the current source files.

## Failure handling

Missing files or required columns fail fast. Record-level data defects are quarantined with reason codes. Pipeline-level reconciliation failures raise an error instead of being treated as a successful run.
