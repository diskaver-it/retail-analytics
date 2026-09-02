-- Recency / frequency / monetary scores, one row per identified customer.
--
-- Recency is measured against the last day in the data, not against today. The
-- extract ends in December 2011: score it against current_date and every
-- customer is equally, uselessly stale, the quintiles collapse and the whole
-- model says nothing. Anything that hard-codes "now" breaks the same way the
-- moment the data stops being live.
--
-- The 5x5 cutoffs below are the usual convention, not something derived from
-- this business. They are a starting point for a conversation with marketing,
-- and a real project would check them against what the segments actually go on
-- to do rather than shipping them as truth.

with as_of as (

    select max(invoice_date) as as_of_date from {{ ref('fct_order_lines') }}

),

base as (

    select
        c.customer_id,
        c.country,
        c.cohort_month,
        date_diff('day', c.last_order_date, a.as_of_date) as recency_days,
        c.orders                                          as frequency,
        c.net_revenue                                     as monetary
    from {{ ref('dim_customer') }} c
    cross join as_of a
    -- A few customers returned more than they ever bought. They are real, but
    -- they cannot be ranked on spend, so they sit out of the quintiles.
    where c.net_revenue > 0

),

scored as (

    select
        *,
        ntile(5) over (order by recency_days desc) as r_score,
        ntile(5) over (order by frequency asc)     as f_score,
        ntile(5) over (order by monetary asc)      as m_score
    from base

)

select
    *,
    case
        when r_score >= 4 and f_score >= 4 then 'Champions'
        when r_score >= 3 and f_score >= 3 then 'Loyal'
        when r_score >= 4 and f_score <= 2 then 'New'
        when r_score >= 3 and f_score <= 2 then 'Promising'
        when r_score <= 2 and f_score >= 4 then 'At risk'
        when r_score <= 2 and f_score = 3  then 'Needs attention'
        else 'Hibernating'
    end as segment

from scored
