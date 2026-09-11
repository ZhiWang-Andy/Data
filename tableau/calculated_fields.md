# Tableau layer

Connect Tableau to the Athena workgroup or to the exported gold tables.

## Recommended worksheets

1. Executive KPI cards: revenue, orders, AOV, and on-time delivery
2. Revenue and order trend
3. Seller performance scatterplot: revenue vs. review score
4. Customer RFM segment distribution
5. Experiment decision panel

## Calculated fields

```text
// Revenue per Customer
SUM([Revenue]) / COUNTD([Customer Unique Id])

// Freight Share
SUM([Freight Value]) / (SUM([Item Revenue]) + SUM([Freight Value]))

// On-Time Delivery Rate
AVG([Delivered On Time])

// Positive Review Rate
AVG(IIF([Review Score] >= 4, 1, 0))

// Experiment Relative Lift
([Treatment Conversion Rate] - [Control Conversion Rate])
/ [Control Conversion Rate]
```

## Filters

- Purchase date
- Customer state
- Seller state
- Order status
- RFM segment
- Experiment variant

Use extracts for a portable portfolio workbook and a live Athena connection for the cloud version.
