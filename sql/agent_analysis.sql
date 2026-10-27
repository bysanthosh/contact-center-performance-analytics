-- Agent-level analysis. Non-handled calls have no agent_id in the synthetic contract.

SELECT
    a.agent_id,
    a.agent_name,
    a.team_name,
    a.site_name,
    COUNT(c.call_id) AS handled_calls,
    ROUND(AVG(
        c.talk_seconds + c.hold_seconds + c.after_call_work_seconds
    ), 2) AS aht_seconds,
    ROUND(100.0 * AVG(
        CASE WHEN c.wait_seconds <= c.sla_threshold_seconds THEN 1.0 ELSE 0.0 END
    ), 2) AS within_sla_pct
FROM dim_agents AS a
LEFT JOIN fact_calls AS c
    ON a.agent_id = c.agent_id
   AND c.handled_flag = 1
GROUP BY a.agent_id, a.agent_name, a.team_name, a.site_name
ORDER BY handled_calls DESC, a.agent_id;

-- Rank agents by handled-call volume. Dense ranking preserves ties.
WITH agent_metrics AS (
    SELECT
        a.agent_id,
        a.agent_name,
        a.team_name,
        COUNT(c.call_id) AS handled_calls,
        AVG(c.talk_seconds + c.hold_seconds + c.after_call_work_seconds) AS aht_seconds
    FROM dim_agents AS a
    LEFT JOIN fact_calls AS c
        ON a.agent_id = c.agent_id
       AND c.handled_flag = 1
    GROUP BY a.agent_id, a.agent_name, a.team_name
)
SELECT
    *,
    DENSE_RANK() OVER (ORDER BY handled_calls DESC) AS handled_volume_rank
FROM agent_metrics
ORDER BY handled_volume_rank, agent_id;
