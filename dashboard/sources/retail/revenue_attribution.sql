-- The split the dashboard exists to keep honest: money that can be tied to a
-- customer against money that cannot. Both are revenue; only the first can be
-- used for retention.
select
    case when is_guest then 'No customer id' else 'Identified customer' end as attribution,
    count(*)                                                                as lines,
    round(sum(line_revenue), 0)                                             as net_revenue,
    round(100.0 * sum(line_revenue) / sum(sum(line_revenue)) over (), 1)    as revenue_pct
from marts.fct_order_lines
group by 1
order by net_revenue desc
