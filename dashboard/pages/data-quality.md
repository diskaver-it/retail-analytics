---
title: What was removed
---

Most dashboards hide this page. It is here because every number on the other two depends on it,
and because a reader who cannot see what was thrown away has no way to judge what is left.

```sql funnel
select * from retail.pipeline_funnel
```

<DataTable data={funnel}>
    <Column id=stage title="Stage"/>
    <Column id=rows title="Rows" fmt=num0/>
</DataTable>

The staging model removes nothing at all. It reads the source, types it, and adds a boolean
column for each awkward case — cancellation, guest, product, zero-priced, duplicate. A dbt test
fails the build if its row count ever stops matching the source exactly.

That is a deliberate constraint rather than tidiness. Filtering early cannot be checked: once a
row is gone, nobody can tell whether a total came out small because the business is small or
because the pipeline ate it. As columns, each mart has to say out loud which rows it wanted.

## The two removals, and why

**Bookkeeping lines.** 62 stock codes are the shop's own admin: `POST`, `DOT`, `BANK CHARGES`,
`AMAZONFEE`, `ADJUST`, `M` for manual. Together they are worth −£95,225 net. They move money,
but nobody ordered them, so they are excluded from products, baskets and units — and left in
nothing that claims to be a best-seller list.

The rule is a shape, not a hand-maintained list: a real product code is five digits with an
optional letter suffix, like `85123A` or `22633`. A list would rot the first time the shop
invented a new charge code.

**Duplicate rows.** 34,337 rows in the source are identical to another row in every single
field; 34,224 of those are product lines, the remaining 113 being bookkeeping lines already
excluded above. There is no way to tell a genuine repeated scan from a duplicated export, so
staging marks them and the fact table drops the second and later copies. Left in, they would
inflate whatever they landed on by a little over three percent.

The two buckets in the table are disjoint and the arithmetic closes exactly:
1,067,371 − 6,093 − 34,224 = 1,027,054.

## What is kept, and surprises people

**Cancellations stay.** A return is a real event with real money attached, and removing it
overstates what the shop kept. They carry a negative quantity and negative revenue, and the
monthly mart reports the return rate separately so the two are never confused.

**Guest baskets stay in revenue.** 243,007 lines have no customer id — 22.8% of the file and
13.6% of net revenue. They are excluded from anything customer-shaped and from nothing else.

## A finding this page exists to explain

The first build against real data failed. 87 fact rows carried a `customer_id` with no matching
row in `dim_customer`, and the test that caught it was doing its job.

It was not a bug. 23 customers appear in this window **only as returns** — 87 lines, −£1,406,
the earliest on the very first day of the file. They bought before December 2009, outside the
extract, and sent something back inside it. With no purchase they have no cohort month, so they
correctly have no customer row.

The relationship test is now scoped to purchase lines, and a second test pins the explanation in
place: the day a customer goes missing from `dim_customer` with a genuine purchase attached, the
build fails again instead of the shortfall spreading quietly through every customer-level metric.
