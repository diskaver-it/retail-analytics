-- One row per invoice line: typed, flagged, still not filtered.
--
-- Every flag here is a decision that would otherwise end up buried in a WHERE
-- clause in whichever mart happened to need it first. As columns they are stated
-- once, each mart says out loud which rows it wanted, and any total can still be
-- reconciled against raw.

with typed as (

    select
        invoice_no,
        stock_code,
        nullif(trim(description), '')            as description,
        quantity,
        unit_price,
        invoice_ts,
        invoice_ts::date                         as invoice_date,
        date_trunc('month', invoice_ts)::date    as invoice_month,
        customer_id::bigint                      as customer_id,
        country,
        source_sheet,
        round(quantity * unit_price, 2)          as line_revenue

    from {{ source('retail_raw', 'transactions') }}

)

select
    typed.*,

    starts_with(invoice_no, 'C')                 as is_cancellation,

    -- 243,007 rows have no customer id - 22.8% of the file, and 13.6% of net
    -- revenue. They are real money, so they belong in revenue, but they cannot
    -- appear in anything cohort- or retention-shaped. Dropping them at the top of
    -- the pipeline is how this dataset usually gets analysed, and it silently
    -- removes an eighth of the revenue before anyone has asked a question.
    customer_id is null                          as is_guest,

    -- Genuine product codes are five digits with an optional letter suffix
    -- (85123A, 22633). The rest are the shop's own bookkeeping: POST, DOT,
    -- BANK CHARGES, AMAZONFEE, ADJUST, M for manual. Those lines carry money but
    -- nobody bought them, so a "top products" chart that keeps them ranks postage
    -- in first place.
    regexp_matches(stock_code, '^[0-9]{5}[A-Za-z]*$') as is_product,

    unit_price <= 0                              as is_zero_priced,

    -- The source contains rows that are identical in every field. Impossible to
    -- tell a genuine repeated scan from a duplicated export, so they are marked
    -- rather than deleted and the fact table decides.
    row_number() over (
        partition by invoice_no, stock_code, invoice_ts, quantity, unit_price
        order by invoice_no
    ) > 1                                        as is_duplicate_line

from typed
