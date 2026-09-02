-- Revenue by month, across every line including guests.
--
-- `is_partial_month` exists because the extract stops mid-December 2011. Without
-- the flag the last bar on every chart is a cliff, and someone will read it as
-- the business collapsing rather than the file ending.

with monthly as (

    select
        invoice_month                                                     as month_start,
        round(sum(line_revenue), 2)                                       as net_revenue,
        round(sum(line_revenue) filter (where not is_cancellation), 2)    as gross_revenue,
        round(-sum(line_revenue) filter (where is_cancellation), 2)       as returned_revenue,
        count(distinct invoice_no) filter (where not is_cancellation)     as orders,
        count(distinct customer_id)                                       as identified_customers,
        sum(quantity) filter (where not is_cancellation)                  as units
    from {{ ref('fct_order_lines') }}
    group by 1

),

coverage as (

    select
        max(invoice_date)                          as last_day,
        date_trunc('month', max(invoice_date))::date as last_month
    from {{ ref('fct_order_lines') }}

)

select
    m.month_start,
    m.gross_revenue,
    coalesce(m.returned_revenue, 0) as returned_revenue,
    m.net_revenue,
    m.orders,
    m.identified_customers,
    m.units,

    round(m.gross_revenue / nullif(m.orders, 0), 2)                        as avg_order_value,
    round(coalesce(m.returned_revenue, 0) / nullif(m.gross_revenue, 0) * 100, 2) as return_rate_pct,
    round(
        (m.net_revenue / nullif(lag(m.net_revenue) over (order by m.month_start), 0) - 1) * 100,
        1
    ) as mom_growth_pct,

    m.month_start = c.last_month
        and c.last_day != last_day(c.last_day) as is_partial_month

from monthly m
cross join coverage c
order by m.month_start
