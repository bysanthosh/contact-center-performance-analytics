-- KPI analysis queries. Run against the SQLite database produced by src/pipeline.py.
-- Definitions follow README_BATCH1.md. Rates return NULL when their denominator is zero.

-- 1. Overall operational KPI summary.
WITH eligible AS (
    SELECT *
    FROM fact_calls
    WHERE offered_flag = 1
),
summary AS (
    SELECT
        COUNT(*) AS offered_calls,
        SUM(handled_flag) AS handled_calls,
        SUM(abandoned_flag) AS abandoned_calls,
        SUM(ivr_contained_flag) AS ivr_contained_calls,
        SUM(CASE
                WHEN handled_flag = 1
                 AND wait_seconds <= sla_threshold_seconds
                THEN 1 ELSE 0
            END) AS handled_within_sla,
        SUM(CASE WHEN handled_flag = 1
                 THEN talk_seconds + hold_seconds + after_call_work_seconds
                 ELSE 0 END) AS total_handle_seconds,
        SUM(handled_flag) AS handled_denominator
    FROM eligible
)
SELECT
    offered_calls,
    handled_calls,
    abandoned_calls,
    ivr_contained_calls,
    ROUND(100.0 * handled_within_sla / NULLIF(offered_calls, 0), 2) AS service_level_pct,
    ROUND(100.0 * abandoned_calls / NULLIF(offered_calls, 0), 2) AS abandonment_rate_pct,
    ROUND(100.0 * ivr_contained_calls / NULLIF(offered_calls, 0), 2) AS ivr_containment_rate_pct,
    ROUND(1.0 * total_handle_seconds / NULLIF(handled_denominator, 0), 2) AS aht_seconds
FROM summary;

-- 2. Daily trends using a CTE.
WITH daily AS (
    SELECT
        substr(created_at, 1, 10) AS call_date,
        COUNT(*) AS offered_calls,
        SUM(handled_flag) AS handled_calls,
        SUM(abandoned_flag) AS abandoned_calls,
        SUM(ivr_contained_flag) AS ivr_contained_calls,
        SUM(CASE WHEN handled_flag = 1
                  AND wait_seconds <= sla_threshold_seconds
                 THEN 1 ELSE 0 END) AS handled_within_sla
    FROM fact_calls
    WHERE offered_flag = 1
    GROUP BY substr(created_at, 1, 10)
)
SELECT
    call_date,
    offered_calls,
    handled_calls,
    ROUND(100.0 * handled_within_sla / NULLIF(offered_calls, 0), 2) AS service_level_pct,
    ROUND(100.0 * abandoned_calls / NULLIF(offered_calls, 0), 2) AS abandonment_rate_pct,
    ROUND(100.0 * ivr_contained_calls / NULLIF(offered_calls, 0), 2) AS ivr_containment_rate_pct
FROM daily
ORDER BY call_date;

-- 3. Outcome distribution using CASE.
SELECT
    call_outcome,
    COUNT(*) AS calls,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS pct_of_valid_calls
FROM fact_calls
GROUP BY call_outcome
ORDER BY calls DESC;

-- 4. Queue performance.
SELECT
    queue_name,
    COUNT(*) AS offered_calls,
    SUM(handled_flag) AS handled_calls,
    ROUND(100.0 * SUM(abandoned_flag) / NULLIF(COUNT(*), 0), 2) AS abandonment_rate_pct,
    ROUND(
        1.0 * SUM(CASE WHEN handled_flag = 1
                       THEN talk_seconds + hold_seconds + after_call_work_seconds
                       ELSE 0 END)
        / NULLIF(SUM(handled_flag), 0),
        2
    ) AS aht_seconds
FROM fact_calls
WHERE offered_flag = 1
GROUP BY queue_name
ORDER BY offered_calls DESC;

-- 5. Hour-of-day volume and service level.
WITH hourly AS (
    SELECT
        CAST(substr(created_at, 12, 2) AS INTEGER) AS hour_of_day,
        COUNT(*) AS offered_calls,
        SUM(CASE WHEN handled_flag = 1
                  AND wait_seconds <= sla_threshold_seconds
                 THEN 1 ELSE 0 END) AS handled_within_sla
    FROM fact_calls
    WHERE offered_flag = 1
    GROUP BY CAST(substr(created_at, 12, 2) AS INTEGER)
)
SELECT
    hour_of_day,
    offered_calls,
    ROUND(100.0 * handled_within_sla / NULLIF(offered_calls, 0), 2) AS service_level_pct
FROM hourly
ORDER BY hour_of_day;
