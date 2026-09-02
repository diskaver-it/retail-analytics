-- Monthly cohorts: of the customers who first bought in month M, how many came
-- back in month M+n.
--
-- Identified customers only, which is a real limitation and not a rounding
-- error - guest baskets cannot be linked to a person, so they can neither form a
-- cohort nor count as a return visit. See dim_customer.
--
-- `months_observable` is what stops the triangle from lying. The cohort that
-- first bought in the final month has had no chance to come back yet; without
-- the column a dashboard will happily plot its month-6 retention as 0% next to a
-- 2009 cohort's real 0%, and the two mean completely different things.

with customer_months as (

    select distinct
        c.cohort_month,
        l.customer_id,
        l.invoice_month
    from {{ ref('fct_order_lines') }} l
    join {{ ref('dim_customer') }} c using (customer_id)
    where not l.is_guest
      and not l.is_cancellation

),

cohort_sizes as (

    select cohort_month, count(*) as cohort_size
    from {{ ref('dim_customer') }}
    group by 1

),

last_month as (

    select max(invoice_month) as final_month from {{ ref('fct_order_lines') }}

),

activity as (

    select
        cohort_month,
        invoice_month,
        date_diff('month', cohort_month, invoice_month) as months_since,
        count(distinct customer_id)                     as active_customers
    from customer_months
    group by 1, 2, 3

)

select
    a.cohort_month,
    a.invoice_month,
    a.months_since,
    s.cohort_size,
    a.active_customers,
    round(a.active_customers::double / s.cohort_size * 100, 1) as retention_pct,
    date_diff('month', a.cohort_month, l.final_month)          as months_observable

from activity a
join cohort_sizes s using (cohort_month)
cross join last_month l
where a.months_since >= 0
order by a.cohort_month, a.months_since
