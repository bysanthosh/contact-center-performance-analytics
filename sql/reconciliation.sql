-- Data reconciliation and quality checks against the loaded analytical tables.
-- Each query should return no rows or zero counts where noted, unless otherwise documented.

-- 1. Total rows and distinct business keys.
SELECT
    COUNT(*) AS loaded_rows,
    COUNT(DISTINCT call_id) AS distinct_call_ids,
    COUNT(*) - COUNT(DISTINCT call_id) AS duplicate_key_excess
FROM fact_calls;

-- 2. Missing required values: expected to return zero for validated rows.
SELECT COUNT(*) AS invalid_required_fields
FROM fact_calls
WHERE call_id IS NULL OR TRIM(call_id) = ''
   OR created_at IS NULL OR updated_at IS NULL
   OR channel IS NULL OR call_outcome IS NULL
   OR offered_flag IS NULL OR handled_flag IS NULL
   OR ivr_contained_flag IS NULL OR abandoned_flag IS NULL;

-- 3. Negative durations: expected to return zero.
SELECT COUNT(*) AS negative_duration_rows
FROM fact_calls
WHERE wait_seconds < 0
   OR COALESCE(talk_seconds, 0) < 0
   OR COALESCE(hold_seconds, 0) < 0
   OR COALESCE(after_call_work_seconds, 0) < 0;

-- 4. Invalid outcome/flag combinations: expected to return zero.
SELECT COUNT(*) AS outcome_flag_mismatches
FROM fact_calls
WHERE (call_outcome = 'HANDLED'
       AND (handled_flag <> 1 OR ivr_contained_flag <> 0 OR abandoned_flag <> 0))
   OR (call_outcome = 'ABANDONED'
       AND (handled_flag <> 0 OR ivr_contained_flag <> 0 OR abandoned_flag <> 1))
   OR (call_outcome = 'IVR_CONTAINED'
       AND (handled_flag <> 0 OR ivr_contained_flag <> 1 OR abandoned_flag <> 0));

-- 5. Agent references that do not match the dimension: expected to return zero.
SELECT COUNT(*) AS unmatched_agent_references
FROM fact_calls AS c
LEFT JOIN dim_agents AS a ON c.agent_id = a.agent_id
WHERE c.handled_flag = 1 AND a.agent_id IS NULL;

-- 6. Handled calls missing a duration component: expected to return zero.
SELECT COUNT(*) AS handled_calls_missing_durations
FROM fact_calls
WHERE handled_flag = 1
  AND (talk_seconds IS NULL OR hold_seconds IS NULL OR after_call_work_seconds IS NULL);

-- 7. Loaded row count compared with the Python data quality report.
-- Run the first query to get loaded_rows, then compare with:
-- reports/data_quality_report.json -> loaded_rows.
SELECT COUNT(*) AS loaded_rows FROM fact_calls;
