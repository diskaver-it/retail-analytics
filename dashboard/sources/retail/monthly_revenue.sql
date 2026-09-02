select
    month_start,
    gross_revenue,
    returned_revenue,
    net_revenue,
    orders,
    identified_customers,
    units,
    avg_order_value,
    return_rate_pct,
    mom_growth_pct,
    is_partial_month
from marts.mart_monthly_revenue
order by month_start
