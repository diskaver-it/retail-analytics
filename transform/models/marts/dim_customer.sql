-- One row per identified customer.
--
-- Guest lines cannot be here: with no id there is no way to know whether two
-- guest baskets are one person coming back or two people. That is why revenue
-- and customer counts are reported from different models in this project - the
-- revenue denominator is every line, the retention denominator is only the ones
-- that can be followed over time. Quietly using the identified subset for both
-- is the mistake this split exists to prevent.

with lines as (

    select * from {{ ref('fct_order_lines') }}
    where not is_guest

),

invoices as (

    select
        customer_id,
        invoice_no,
        min(invoice_date)        as order_date,
        bool_or(is_cancellation) as is_cancellation,
        sum(line_revenue)        as invoice_revenue,
        sum(quantity)            as invoice_units
    from lines
    group by 1, 2

),

purchases as (

    select * from invoices where not is_cancellation

),

activity as (

    select
        customer_id,
        min(order_date)                                       as first_order_date,
        max(order_date)                                       as last_order_date,
        date_trunc('month', min(order_date))::date            as cohort_month,
        count(*)                                              as orders,
        round(sum(invoice_revenue), 2)                        as gross_revenue,
        sum(invoice_units)                                    as units
    from purchases
    group by 1

),

returns as (

    select
        customer_id,
        count(*)                       as returned_orders,
        round(sum(invoice_revenue), 2) as returned_revenue   -- already negative
    from invoices
    where is_cancellation
    group by 1

),

-- A handful of customers order from more than one country. Take the one they
-- spent the most in rather than the first seen, so the country breakdown adds up
-- to something a person would recognise.
home_country as (

    select customer_id, country
    from (
        select
            customer_id,
            country,
            row_number() over (
                partition by customer_id
                order by sum(line_revenue) desc, country
            ) as rank
        from lines
        group by 1, 2
    )
    where rank = 1

)

select
    a.customer_id,
    h.country,
    a.cohort_month,
    a.first_order_date,
    a.last_order_date,
    a.orders,
    a.units,
    a.gross_revenue,
    coalesce(r.returned_orders, 0)                          as returned_orders,
    coalesce(r.returned_revenue, 0)                         as returned_revenue,
    round(a.gross_revenue + coalesce(r.returned_revenue, 0), 2) as net_revenue,
    round(a.gross_revenue / a.orders, 2)                    as avg_order_value,
    date_diff('day', a.first_order_date, a.last_order_date) as lifespan_days,
    a.orders > 1                                            as is_repeat_customer

from activity a
left join returns r using (customer_id)
left join home_country h using (customer_id)
