select
    stock_code,
    description,
    units_sold,
    net_revenue,
    identified_customers,
    return_rate_pct
from marts.dim_product
where net_revenue > 0
order by net_revenue desc
limit 20
