-- The triangle. months_observable travels with every row so the page can tell a
-- cohort that came back and stopped from one that has not had the chance yet.
select
    cohort_month,
    months_since,
    cohort_size,
    active_customers,
    retention_pct,
    months_observable
from marts.mart_cohort_retention
where months_since > 0
order by cohort_month, months_since
