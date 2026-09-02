select
    cohort_month,
    cohort_size,
    max(months_observable)                              as months_observable,
    max(retention_pct) filter (where months_since = 1)  as month_1_pct,
    max(retention_pct) filter (where months_since = 3)  as month_3_pct,
    max(retention_pct) filter (where months_since = 6)  as month_6_pct
from marts.mart_cohort_retention
group by cohort_month, cohort_size
order by cohort_month
