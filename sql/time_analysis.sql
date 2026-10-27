-- Time-based analysis. Timestamps are stored as ISO-formatted text in local synthetic time.

-- Daily call volume and previous-day comparison.
WITH daily AS (
    SELECT
        substr(created_at, 1, 10) AS call_date,
        COUNT(*) AS offered_calls
    FROM fact_calls
    WHERE offered_flag = 1
    GROUP BY substr(created_at, 1, 10)
),
with_previous AS (
    SELECT
        call_date,
        offered_calls,
        LAG(offered_calls) OVER (ORDER BY call_date) AS previous_day_calls
    FROM daily
)
SELECT
    call_date,
    offered_calls,
    previous_day_calls,
    offered_calls - previous_day_calls AS change_vs_previous_day,
    ROUND(
        100.0 * (offered_calls - previous_day_calls)
        / NULLIF(previous_day_calls, 0),
        2
    ) AS pct_change_vs_previous_day
FROM with_previous
ORDER BY call_date;

-- Running total of offered calls by date.
WITH daily AS (
    SELECT substr(created_at, 1, 10) AS call_date, COUNT(*) AS offered_calls
    FROM fact_calls
    WHERE offered_flag = 1
    GROUP BY substr(created_at, 1, 10)
)
SELECT
    call_date,
    offered_calls,
    SUM(offered_calls) OVER (
        ORDER BY call_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_offered_calls
FROM daily
ORDER BY call_date;
