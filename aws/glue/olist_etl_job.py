"""AWS Glue PySpark entrypoint for the Olist analytics lakehouse."""

from __future__ import annotations

import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME", "RAW_S3_URI", "CURATED_S3_URI"])
sc = SparkContext.getOrCreate()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

spark.conf.set("spark.sql.session.timeZone", "UTC")
raw = args["RAW_S3_URI"].rstrip("/")
curated = args["CURATED_S3_URI"].rstrip("/")


def read_csv(filename: str):
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .option("mode", "PERMISSIVE")
        .csv(f"{raw}/{filename}")
    )


orders = read_csv("olist_orders_dataset.csv")
items = read_csv("olist_order_items_dataset.csv")
payments = read_csv("olist_order_payments_dataset.csv")
customers = read_csv("olist_customers_dataset.csv")
reviews = read_csv("olist_order_reviews_dataset.csv")

orders = (
    orders.withColumn("order_purchase_timestamp", F.to_timestamp("order_purchase_timestamp"))
    .withColumn(
        "order_delivered_customer_date",
        F.to_timestamp("order_delivered_customer_date"),
    )
    .withColumn(
        "order_estimated_delivery_date",
        F.to_timestamp("order_estimated_delivery_date"),
    )
)

for name, frame in {
    "orders": orders,
    "order_items": items,
    "payments": payments,
    "customers": customers,
    "reviews": reviews,
}.items():
    frame.withColumn("_ingested_at", F.current_timestamp()).write.mode("overwrite").parquet(
        f"{curated}/silver/{name}"
    )
    frame.createOrReplaceTempView(name)

fact_orders = spark.sql(
    """
    WITH item_agg AS (
      SELECT order_id,
             SUM(CAST(price AS DOUBLE)) item_revenue,
             SUM(CAST(freight_value AS DOUBLE)) freight_value,
             COUNT(*) item_count,
             COUNT(DISTINCT seller_id) seller_count
      FROM order_items GROUP BY order_id
    ), payment_agg AS (
      SELECT order_id, SUM(CAST(payment_value AS DOUBLE)) payment_value
      FROM payments GROUP BY order_id
    ), review_agg AS (
      SELECT order_id, AVG(CAST(review_score AS DOUBLE)) review_score
      FROM reviews GROUP BY order_id
    )
    SELECT o.order_id,
           c.customer_unique_id,
           c.customer_state,
           o.order_status,
           o.order_purchase_timestamp,
           YEAR(o.order_purchase_timestamp) purchase_year,
           MONTH(o.order_purchase_timestamp) purchase_month,
           COALESCE(i.item_revenue, 0.0) item_revenue,
           COALESCE(i.freight_value, 0.0) freight_value,
           COALESCE(p.payment_value, 0.0) payment_value,
           i.item_count,
           i.seller_count,
           r.review_score,
           CASE
             WHEN o.order_delivered_customer_date IS NULL THEN NULL
             WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN 1
             ELSE 0
           END delivered_on_time,
           CASE
             WHEN o.order_delivered_customer_date IS NULL THEN NULL
             ELSE DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp)
           END delivery_days,
           CURRENT_TIMESTAMP() _transformed_at
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN item_agg i ON o.order_id = i.order_id
    LEFT JOIN payment_agg p ON o.order_id = p.order_id
    LEFT JOIN review_agg r ON o.order_id = r.order_id
    """
)

fact_orders.write.mode("overwrite").partitionBy("purchase_year", "purchase_month").parquet(
    f"{curated}/gold/fact_orders"
)

fact_orders.createOrReplaceTempView("fact_orders")
daily_kpis = spark.sql(
    """
    SELECT TO_DATE(order_purchase_timestamp) order_date,
           COUNT(*) orders,
           COUNT(DISTINCT customer_unique_id) customers,
           ROUND(SUM(payment_value), 2) revenue,
           ROUND(AVG(payment_value), 2) average_order_value,
           ROUND(AVG(delivered_on_time), 4) on_time_delivery_rate,
           ROUND(AVG(delivery_days), 2) average_delivery_days,
           ROUND(AVG(review_score), 2) average_review_score
    FROM fact_orders
    WHERE order_status = 'delivered'
    GROUP BY TO_DATE(order_purchase_timestamp)
    """
)
daily_kpis.write.mode("overwrite").parquet(f"{curated}/gold/daily_sales_kpis")
job.commit()
