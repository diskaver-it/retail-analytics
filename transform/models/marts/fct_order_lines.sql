-- The grain everything else is built on: one line of merchandise on one invoice.
--
-- Two kinds of row are dropped here and nowhere else:
--   * non-product lines - postage, bank charges, manual adjustments. They move
--     money but nobody ordered them, so they distort products, baskets and units
--     while barely touching revenue.
--   * exact duplicate rows, which would double-count whatever they landed on.
--
-- Cancellations stay, with negative quantity and negative revenue, because a
-- return is a real event and removing it overstates what the shop actually kept.
-- Guest lines stay too - see dim_customer for why they cannot go any further.

select
    row_number() over (order by invoice_ts, invoice_no, stock_code) as order_line_id,

    invoice_no,
    stock_code,
    description,
    customer_id,
    country,

    invoice_ts,
    invoice_date,
    invoice_month,

    quantity,
    unit_price,
    line_revenue,

    is_cancellation,
    is_guest,
    is_zero_priced

from {{ ref('stg_transactions') }}
where is_product
  and not is_duplicate_line
