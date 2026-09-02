select
    round(sum(line_revenue), 0)                                        as net_revenue,
    count(distinct invoice_no) filter (where not is_cancellation)       as orders,
    count(distinct customer_id)                                        as customers,
    round(100.0 * sum(line_revenue) filter (where is_guest)
          / sum(line_revenue), 1)                                      as guest_revenue_pct,
    round(-100.0 * sum(line_revenue) filter (where is_cancellation)
          / sum(line_revenue) filter (where not is_cancellation), 1)   as return_rate_pct
from marts.fct_order_lines
