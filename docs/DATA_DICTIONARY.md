# Data Dictionary

The raw call CSV contains one or more source versions per call. After canonical selection and validation, `fact_calls` contains accepted canonical records.

## `fact_calls`

| Column | Meaning |
|---|---|
| `call_id` | Unique call identifier after canonical selection |
| `created_at` | Call creation timestamp |
| `updated_at` | Timestamp of the source version |
| `agent_id` | Assigned agent identifier; may be blank for abandoned/IVR-contained calls |
| `channel` | Interaction channel (synthetic values such as VOICE or IVR) |
| `call_outcome` | HANDLED, ABANDONED, or IVR_CONTAINED |
| `queue_name` | Synthetic queue name |
| `offered_flag` | 1 when the call is counted as offered |
| `handled_flag` | 1 when handled by an agent |
| `ivr_contained_flag` | 1 when contained in the IVR |
| `abandoned_flag` | 1 when abandoned |
| `wait_seconds` | Wait duration used for service-level evaluation |
| `talk_seconds` | Talk duration |
| `hold_seconds` | Hold duration |
| `after_call_work_seconds` | Post-call work duration |
| `sla_threshold_seconds` | Per-record wait threshold used by this project |

## `dim_agents`

| Column | Meaning |
|---|---|
| `agent_id` | Agent identifier |
| `agent_name` | Synthetic agent display name |
| `team_name` | Synthetic team assignment |
| `site_name` | Synthetic work site |

## Derived KPIs

- **AHT seconds:** average of `talk_seconds + hold_seconds + after_call_work_seconds` for handled calls only.
- **Abandonment rate:** abandoned calls divided by offered calls.
- **IVR containment rate:** IVR-contained calls divided by offered calls.
- **Service level:** handled calls whose wait time is at or below their threshold divided by all offered calls. This project deliberately retains abandoned calls in the denominator.
- **Reconciliation:** canonical = accepted + rejected; accepted = loaded.

Definitions are project-specific and should be stated when comparing results with other reports.


## Dataset scale and realism (Batch 5 data refresh)

- Coverage: January 2024 through December 2026, inclusive.
- Volume: 5,000 base offered calls per month (180,000 base calls total).
- Raw file includes approximately 1% later duplicate versions for deduplication practice.
- Approximately 0.5% of base records contain intentional validation defects and should be quarantined.
- Handled-call queue wait values are generated to produce an ASA generally around 60–90 seconds; exact averages vary by month and seed.
- Data is entirely synthetic and must not be represented as actual employer/customer data.
