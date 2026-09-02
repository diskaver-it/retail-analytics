---
title: Customers
---

Everything on this page is restricted to customers with an id, which is
[not the same population](/) as the one revenue is measured over.

## Do they come back

```sql retention_curve
select
    months_since,
    round(avg(retention_pct), 1) as retention_pct,
    count(*) as cohorts
from retail.cohort_retention
where months_observable >= 6 and months_since <= 12
group by months_since
order by months_since
```

```sql cohort_summary
select * from retail.cohort_summary order by cohort_month
```

<LineChart
    data={retention_curve}
    x=months_since
    y=retention_pct
    yFmt='0.0"%"'
    yMin=0
    xAxisTitle="Months after the first order"
    title="Average monthly retention across cohorts"
    subtitle="Cohorts with at least six months of history"
/>

Retention starts near **20% in month one**, holds through month three at 21.5%, and then drifts
down to about 15% by month ten. There is no cliff. Shops either turn into accounts or they never
order twice, and the ones that stay keep ordering at a fairly steady rate — which is what a
wholesale book looks like and not what a consumer app's decay curve looks like.

One cohort behaves nothing like the rest. **December 2009** reads 35.0%, 42.5% and 37.6% at
months one, three and six, against 15–25% for everything after it.

That is not a better cohort. It is the shop's existing account base appearing for the first time
on the day the extract begins — customers who had been ordering for years get labelled "new"
because the file starts there. It is the same left truncation that produces the
[customers who only ever appear as returns](/data-quality), and it is the reason the first row of
the table below is a floor rather than a benchmark.

<DataTable data={cohort_summary} rows=12>
    <Column id=cohort_month title="Cohort" fmt=mmm_yyyy/>
    <Column id=cohort_size title="Customers" fmt=num0/>
    <Column id=months_observable title="Months observable" fmt=num0/>
    <Column id=month_1_pct title="Month 1" fmt='0.0"%"' contentType=colorscale/>
    <Column id=month_3_pct title="Month 3" fmt='0.0"%"' contentType=colorscale/>
    <Column id=month_6_pct title="Month 6" fmt='0.0"%"' contentType=colorscale/>
</DataTable>

Blanks in the last rows are not zeros. A cohort that first bought three months before the file
ends cannot have a month-six number yet, so `months_observable` travels with every row and the
chart above drops any cohort with fewer than six months. Plotting an unobservable 0% beside a
real one would say they mean the same thing.

## Where the money actually is

```sql segments
select * from retail.rfm_segments
```

<BarChart
    data={segments}
    x=segment
    y=revenue_pct
    yFmt='0"%"'
    swapXY=true
    title="Share of revenue by RFM segment"
/>

<DataTable data={segments}>
    <Column id=segment title="Segment"/>
    <Column id=customers title="Customers" fmt=num0/>
    <Column id=customers_pct title="of base" fmt='0.0"%"'/>
    <Column id=revenue title="Revenue" fmt=gbp0/>
    <Column id=revenue_pct title="of revenue" fmt='0.0"%"'/>
    <Column id=avg_orders title="Avg orders" fmt=num1/>
    <Column id=avg_recency_days title="Days since last order" fmt=num0/>
</DataTable>

Concentration is severe even by wholesale standards: a quarter of the customer base produces
about seven pounds in ten. The practical reading is that account management and reactivation are
aimed at different rows of this table, and "At risk" — few customers, high spend, long silence —
is the row worth a phone call.

Two caveats the table cannot show. Recency is measured against the last day in the data rather
than today; scored against the real current date, every customer in a 2011 file is equally stale
and all five quintiles collapse into one. And the 5×5 cutoffs are the usual convention, not
something derived from this business — a starting point for a conversation with whoever owns the
accounts, not a finding.
