---
title: Online Retail II
---

A UK online gift wholesaler, December 2009 to December 2011. Every number on this site is
read from the dbt marts in this repository — nothing is typed in by hand, and the page rebuilds
from `dbt build`.

```sql kpis
select * from retail.kpis
```

<BigValue data={kpis} value=net_revenue fmt=gbp0 title="Net revenue"/>
<BigValue data={kpis} value=orders fmt=num0 title="Orders"/>
<BigValue data={kpis} value=customers fmt=num0 title="Identified customers"/>
<BigValue data={kpis} value=return_rate_pct fmt='0.0"%"' title="Return rate"/>

## Revenue over time

```sql complete_months
select month_start, gross_revenue, net_revenue, orders, avg_order_value, return_rate_pct
from retail.monthly_revenue
where not is_partial_month
order by month_start
```

```sql partial_month
select month_start, net_revenue, mom_growth_pct, return_rate_pct
from retail.monthly_revenue
where is_partial_month
```

<LineChart
    data={complete_months}
    x=month_start
    y=net_revenue
    yFmt=gbp0k
    title="Net revenue by month"
    subtitle="Trading is heavily seasonal: autumn builds toward Christmas, January collapses"
/>

The extract stops on **9 December 2011**, so the final month is not a month. Drawn in, it would
show a fall of <Value data={partial_month} column=mom_growth_pct fmt='0.0"%"'/> and a return rate
of <Value data={partial_month} column=return_rate_pct fmt='0.0"%"'/>, both artefacts of the same
thing: November's returns land in December while December's own orders mostly do not exist yet.
So it is left out of the chart above.

The mart carries an `is_partial_month` flag for exactly this reason. A dashboard that plots the
last bar of a truncated file has told the reader the business collapsed.

## Whose money is it

```sql attribution
select * from retail.revenue_attribution
```

<BarChart
    data={attribution}
    x=attribution
    y=net_revenue
    yFmt=gbp0k
    swapXY=true
    title="Net revenue by whether the line has a customer id"
/>

<DataTable data={attribution}>
    <Column id=attribution title="Attribution"/>
    <Column id=lines title="Lines" fmt=num0/>
    <Column id=net_revenue title="Net revenue" fmt=gbp0/>
    <Column id=revenue_pct title="Share" fmt='0.0"%"'/>
</DataTable>

Roughly a fifth of the lines carry no customer id. The usual first line of an analysis of this
dataset is `WHERE customer_id IS NOT NULL`, and it quietly removes
<Value data={kpis} column=guest_revenue_pct fmt='0.0"%"'/> of net revenue before anyone has asked
a question.

So the denominators here are deliberately different. Revenue is measured over every line.
Retention is measured only over customers who can be followed across time — because with no id
there is no way to tell two visits from two people.

## Best sellers

```sql top_products
select * from retail.top_products limit 10
```

<DataTable data={top_products}>
    <Column id=description title="Product"/>
    <Column id=units_sold title="Units" fmt=num0/>
    <Column id=net_revenue title="Net revenue" fmt=gbp0/>
    <Column id=identified_customers title="Customers" fmt=num0/>
    <Column id=return_rate_pct title="Returned" fmt='0.0"%"' contentType=colorscale/>
</DataTable>

Postage, bank charges and stock adjustments are not in this table. They are real money — 62
codes and −£95,225 of it — but nobody ordered them, and a best-seller list that keeps them
ranks postage first. They are removed once, in `fct_order_lines`, and the removal is
[shown on its own page](/data-quality).
