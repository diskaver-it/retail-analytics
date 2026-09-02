-- What the pipeline removed, in disjoint buckets so the arithmetic closes:
-- bookkeeping lines first, then duplicates among what is left.
select 1 as step, 'Rows in source' as stage, count(*) as rows
from staging.stg_transactions

union all
select 2, 'Bookkeeping lines', count(*)
from staging.stg_transactions
where not is_product

union all
select 3, 'Duplicate rows', count(*)
from staging.stg_transactions
where is_product and is_duplicate_line

union all
select 4, 'Rows in fct_order_lines', count(*)
from marts.fct_order_lines

order by step
