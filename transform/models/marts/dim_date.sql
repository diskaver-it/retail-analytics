-- Calendar spine covering the days the shop actually traded.
--
-- Built so that a month with no sales shows up as a zero instead of vanishing
-- from a chart. A line that skips from March to May because April is missing
-- reads as "flat", which is the opposite of what happened.

with bounds as (

    select
        min(invoice_date) as first_day,
        max(invoice_date) as last_day
    from {{ ref('fct_order_lines') }}

),

spine as (

    select unnest(generate_series(first_day, last_day, interval 1 day))::date as date_day
    from bounds

)

select
    date_day,
    date_trunc('month',   date_day)::date as month_start,
    date_trunc('quarter', date_day)::date as quarter_start,
    year(date_day)                        as year,
    month(date_day)                       as month_of_year,
    monthname(date_day)                   as month_name,
    dayofweek(date_day)                   as day_of_week,
    dayname(date_day)                     as day_name,
    isodow(date_day) >= 6                 as is_weekend
from spine
