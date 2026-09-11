from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession, functions as F

from src.maintenance.quality import (
    CheckResult,
    assert_quality,
    evaluate_count,
    evaluate_rate,
    write_report,
)
from src.maintenance.state import write_success

EXPECTED_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

TIMESTAMP_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
    "order_items": ["shipping_limit_date"],
}
SQL_ROOT = Path(__file__).resolve().parents[2] / "sql"


def spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("olist-cloud-analytics")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .getOrCreate()
    )


def read_csv(spark: SparkSession, path: Path) -> DataFrame:
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .option("mode", "PERMISSIVE")
        .csv(str(path))
    )


def normalize_table(name: str, frame: DataFrame) -> DataFrame:
    normalized = frame.select(
        [F.col(column).alias(column.strip().lower()) for column in frame.columns]
    )
    for column in TIMESTAMP_COLUMNS.get(name, []):
        if column in normalized.columns:
            normalized = normalized.withColumn(column, F.to_timestamp(column))
    return normalized.withColumn("_ingested_at", F.current_timestamp())


def load_source_tables(spark: SparkSession, input_root: Path) -> dict[str, DataFrame]:
    missing = [
        filename for filename in EXPECTED_FILES.values() if not (input_root / filename).exists()
    ]
    if missing:
        raise FileNotFoundError("Missing required Olist files: " + ", ".join(sorted(missing)))
    return {
        name: normalize_table(name, read_csv(spark, input_root / filename))
        for name, filename in EXPECTED_FILES.items()
    }


def create_views(tables: dict[str, DataFrame]) -> None:
    for name, frame in tables.items():
        frame.createOrReplaceTempView(name)


def build_fact_orders(spark: SparkSession) -> DataFrame:
    return spark.sql(
        """
        WITH item_agg AS (
            SELECT
                order_id,
                SUM(CAST(price AS DOUBLE)) AS item_revenue,
                SUM(CAST(freight_value AS DOUBLE)) AS freight_value,
                COUNT(*) AS item_count,
                COUNT(DISTINCT product_id) AS distinct_products,
                COUNT(DISTINCT seller_id) AS seller_count
            FROM order_items
            GROUP BY order_id
        ),
        payment_agg AS (
            SELECT
                order_id,
                SUM(CAST(payment_value AS DOUBLE)) AS payment_value,
                MAX(CAST(payment_installments AS INT)) AS max_installments,
                CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(payment_type))) AS payment_types
            FROM payments
            GROUP BY order_id
        ),
        review_agg AS (
            SELECT order_id, AVG(CAST(review_score AS DOUBLE)) AS review_score
            FROM reviews
            GROUP BY order_id
        )
        SELECT
            o.order_id,
            c.customer_unique_id,
            c.customer_city,
            c.customer_state,
            o.order_status,
            o.order_purchase_timestamp,
            o.order_approved_at,
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date,
            YEAR(o.order_purchase_timestamp) AS purchase_year,
            MONTH(o.order_purchase_timestamp) AS purchase_month,
            COALESCE(i.item_revenue, 0.0) AS item_revenue,
            COALESCE(i.freight_value, 0.0) AS freight_value,
            COALESCE(p.payment_value, 0.0) AS payment_value,
            COALESCE(i.item_count, 0) AS item_count,
            COALESCE(i.distinct_products, 0) AS distinct_products,
            COALESCE(i.seller_count, 0) AS seller_count,
            p.max_installments,
            p.payment_types,
            r.review_score,
            CASE
                WHEN o.order_delivered_customer_date IS NULL THEN NULL
                WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN 1
                ELSE 0
            END AS delivered_on_time,
            CASE
                WHEN o.order_delivered_customer_date IS NULL THEN NULL
                ELSE DATEDIFF(
                    o.order_delivered_customer_date,
                    o.order_purchase_timestamp
                )
            END AS delivery_days,
            CURRENT_TIMESTAMP() AS _transformed_at
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        LEFT JOIN item_agg i ON o.order_id = i.order_id
        LEFT JOIN payment_agg p ON o.order_id = p.order_id
        LEFT JOIN review_agg r ON o.order_id = r.order_id
        """
    )


def build_daily_kpis(spark: SparkSession, fact_orders: DataFrame) -> DataFrame:
    fact_orders.createOrReplaceTempView("fact_orders")
    return spark.sql((SQL_ROOT / "01_daily_sales_kpis.sql").read_text(encoding="utf-8"))


def build_seller_performance(spark: SparkSession) -> DataFrame:
    return spark.sql((SQL_ROOT / "02_seller_performance.sql").read_text(encoding="utf-8"))


def build_customer_rfm(spark: SparkSession, fact_orders: DataFrame) -> DataFrame:
    fact_orders.createOrReplaceTempView("fact_orders")
    return spark.sql((SQL_ROOT / "03_customer_rfm.sql").read_text(encoding="utf-8"))


def quality_checks(
    tables: dict[str, DataFrame], fact_orders: DataFrame
) -> list[CheckResult]:
    order_count = tables["orders"].count()
    fact_count = fact_orders.count()
    duplicate_orders = (
        fact_orders.groupBy("order_id").count().filter(F.col("count") > 1).count()
    )
    negative_amounts = fact_orders.filter(
        (F.col("item_revenue") < 0)
        | (F.col("freight_value") < 0)
        | (F.col("payment_value") < 0)
    ).count()
    missing_customer = fact_orders.filter(F.col("customer_unique_id").isNull()).count()
    return [
        evaluate_count("source_order_count", order_count),
        CheckResult(
            "fact_matches_orders",
            "PASS" if fact_count == order_count else "FAIL",
            fact_count,
            f"== {order_count}",
        ),
        evaluate_rate("duplicate_order_rate", duplicate_orders, max(fact_count, 1), 0.0),
        evaluate_rate("negative_amount_rate", negative_amounts, max(fact_count, 1), 0.0),
        evaluate_rate("missing_customer_rate", missing_customer, max(fact_count, 1), 0.001),
    ]


def write_parquet(
    frame: DataFrame, path: Path, partition_by: list[str] | None = None
) -> None:
    writer = frame.write.mode("overwrite")
    if partition_by:
        writer = writer.partitionBy(*partition_by)
    writer.parquet(str(path))


def run_pipeline(input_root: Path, output_root: Path, quality_report: Path) -> None:
    spark = spark_session()
    try:
        tables = load_source_tables(spark, input_root)
        for name, frame in tables.items():
            write_parquet(frame, output_root / "bronze" / name)

        silver = {name: frame.dropDuplicates() for name, frame in tables.items()}
        for name, frame in silver.items():
            write_parquet(frame, output_root / "silver" / name)

        create_views(silver)
        fact_orders = build_fact_orders(spark)
        daily_kpis = build_daily_kpis(spark, fact_orders)
        seller_performance = build_seller_performance(spark)
        customer_rfm = build_customer_rfm(spark, fact_orders)

        report = write_report(quality_checks(silver, fact_orders), quality_report)
        assert_quality(report)

        write_parquet(
            fact_orders,
            output_root / "gold" / "fact_orders",
            partition_by=["purchase_year", "purchase_month"],
        )
        write_parquet(daily_kpis, output_root / "gold" / "daily_sales_kpis")
        write_parquet(
            seller_performance,
            output_root / "gold" / "seller_performance",
        )
        write_parquet(customer_rfm, output_root / "gold" / "customer_rfm")

        partitions = [
            f"{row.purchase_year}-{int(row.purchase_month):02d}"
            for row in fact_orders.select("purchase_year", "purchase_month")
            .distinct()
            .collect()
            if row.purchase_year is not None and row.purchase_month is not None
        ]
        write_success(output_root / "_state" / "pipeline_state.json", partitions)
    finally:
        spark.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Olist bronze/silver/gold tables")
    parser.add_argument("--input", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/lakehouse"))
    parser.add_argument(
        "--quality-report",
        type=Path,
        default=Path("artifacts/data_quality_report.json"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.input, args.output, args.quality_report)
