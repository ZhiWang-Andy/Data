# Power BI semantic model

## Tables

- `Fact Orders`: order-level fact table
- `Daily Sales KPIs`: daily aggregate table
- `Seller Performance`: seller-grain mart
- `Customer RFM`: customer-grain segmentation mart
- `Experiment Metrics`: one row per experiment analysis run
- `Date`: generated calendar table

## Relationships

- Date[Date] 1:* Fact Orders[Order Purchase Date]
- Date[Date] 1:* Daily Sales KPIs[Order Date]
- Keep seller and RFM marts disconnected from Fact Orders unless dedicated dimensions are added; this avoids ambiguous many-to-many relationships.

## Recommended report pages

1. Executive overview
2. Customer and geographic analysis
3. Seller and fulfillment performance
4. Experiment monitoring
5. Data-quality operations

## Refresh

For cloud deployment, connect Power BI to Amazon Athena. Configure scheduled refresh after the Glue job, crawler, and data-quality gate complete.
