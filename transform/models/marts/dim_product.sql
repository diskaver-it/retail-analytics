-- One row per stock code.
--
-- Descriptions are not stable in the source: the same code turns up with
-- different casing, different spellings and the odd note somebody typed into the
-- field by hand. Taking the most frequent one keeps a single product from
-- appearing three times in the same chart.

with lines as (

    select * from {{ ref('fct_order_lines') }}

),

naming as (

    select stock_code, description
    from (
        select
            stock_code,
            description,
            row_number() over (
                partition by stock_code
                order by count(*) desc, description
            ) as rank
        from lines
        where description is not null
        group by 1, 2
    )
    where rank = 1

),

sales as (

    select
        stock_code,
        min(invoice_date)                                            as first_sold_date,
        max(invoice_date)                                            as last_sold_date,
        count(distinct invoice_no) filter (where not is_cancellation) as orders,
        count(distinct customer_id)                                  as identified_customers,
        sum(quantity) filter (where not is_cancellation)             as units_sold,
        -sum(quantity) filter (where is_cancellation)                as units_returned,
        round(sum(line_revenue), 2)                                  as net_revenue,
        round(avg(unit_price) filter (where unit_price > 0), 2)      as avg_unit_price
    from lines
    group by 1

)

select
    s.stock_code,
    n.description,
    s.first_sold_date,
    s.last_sold_date,
    s.orders,
    s.identified_customers,
    s.units_sold,
    coalesce(s.units_returned, 0) as units_returned,
    s.net_revenue,
    s.avg_unit_price,
    round(coalesce(s.units_returned, 0)::double / nullif(s.units_sold, 0) * 100, 2) as return_rate_pct

from sales s
left join naming n using (stock_code)
