# Architecture and design decisions

## Layering

| Layer | Purpose | Storage format | Typical consumers |
|---|---|---|---|
| Bronze | Immutable source-shaped data plus ingestion timestamp | Parquet | audit, replay |
| Silver | Typed, normalized, deduplicated entities | Parquet | analytics engineering |
| Gold | Business-grain facts, KPI marts, and experiment outputs | partitioned Parquet | Athena, Tableau, Power BI, Streamlit |

## Why Spark SQL

The project uses SQL for business transformations and PySpark for orchestration, IO, typing, partitioning, and quality checks. This separation makes metric logic easier for analysts to review while retaining distributed processing and cloud portability.

## Data flow

1. Kaggle files land in the raw zone.
2. The Spark pipeline validates expected files and normalizes source tables.
3. Bronze stores source-shaped data with ingestion metadata.
4. Silver stores typed and deduplicated entities.
5. Gold publishes an order fact table, daily KPI mart, seller mart, customer RFM mart, and experiment results.
6. Athena exposes cataloged gold tables to Tableau and Power BI.
7. Quality checks block publication when reconciliation or integrity rules fail.

## Idempotency and maintenance

- Raw ingestion uses deterministic filenames.
- Bronze, silver, and gold outputs use overwrite semantics for the static Kaggle snapshot.
- Gold facts are partitioned by purchase year and month.
- A state file records successful partitions and the last successful run.
- S3 versioning supports recovery from accidental overwrite.
- Retention code removes stale run artifacts while preserving the latest runs.

## Semantic model

`fact_orders` has one row per order. Item, payment, and review tables are aggregated to order grain before joining, preventing fan-out and double counting. Seller and customer RFM marts remain at their own grains.

## Production extensions

For a live source, replace full overwrite with merge-on-key using Apache Iceberg, Hudi, or Delta; add CDC ingestion; catalog table-level lineage; and use incremental event-time watermarks.
