select
    segment,
    count(*)                                                        as customers,
    round(100.0 * count(*) / sum(count(*)) over (), 1)              as customers_pct,
    round(sum(monetary), 0)                                         as revenue,
    round(100.0 * sum(monetary) / sum(sum(monetary)) over (), 1)    as revenue_pct,
    round(avg(recency_days), 0)                                     as avg_recency_days,
    round(avg(frequency), 1)                                        as avg_orders
from marts.mart_rfm
group by segment
order by revenue desc
