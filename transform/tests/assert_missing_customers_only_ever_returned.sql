-- 23 customers in this extract show up only as returns: they bought before
-- 2009-12-01, outside the window, and sent something back inside it. 87 lines,
-- -1,406 of revenue, the earliest on the very first day of the file. With no
-- purchase they have no cohort month, so they have no row in dim_customer.
--
-- That is why the relationships test on fct_order_lines.customer_id is scoped to
-- purchase lines. This is the other half of the argument: it holds the
-- explanation to account. The day a customer goes missing from dim_customer with
-- a genuine purchase attached, dim_customer is broken and this fails instead of
-- the shortfall quietly spreading through every customer-level metric.

select
    customer_id,
    count(*) filter (where not is_cancellation) as purchase_lines

from {{ ref('fct_order_lines') }}

where customer_id is not null
  and customer_id not in (select customer_id from {{ ref('dim_customer') }})

group by customer_id
having count(*) filter (where not is_cancellation) > 0
