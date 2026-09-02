-- Staging promises to flag rather than filter. This is that promise, enforced:
-- if someone later adds a WHERE clause to stg_transactions, the build fails here
-- instead of quietly shrinking every total downstream.

with counts as (
    select
        (select count(*) from {{ source('retail_raw', 'transactions') }}) as raw_rows,
        (select count(*) from {{ ref('stg_transactions') }})              as staged_rows
)

select *
from counts
where raw_rows != staged_rows
