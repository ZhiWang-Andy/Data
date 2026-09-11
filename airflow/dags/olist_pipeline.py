from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {"owner": "analytics-engineering", "retries": 2}

with DAG(
    dag_id="olist_cloud_analytics",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule="0 7 * * 1",
    catchup=False,
    tags=["spark", "aws", "ab-test", "data-quality"],
) as dag:
    ingest = BashOperator(
        task_id="download_kaggle_data",
        bash_command="python -m src.ingestion.download_kaggle --output data/raw",
    )
    transform = BashOperator(
        task_id="spark_bronze_silver_gold",
        bash_command=(
            "python -m src.etl.spark_pipeline --input data/raw --output data/lakehouse "
            "--quality-report artifacts/data_quality_report.json"
        ),
    )
    experiment = BashOperator(
        task_id="analyze_experiment",
        bash_command=(
            "python -m src.analytics.experiment "
            "--fact-orders data/lakehouse/gold/fact_orders "
            "--output data/lakehouse/gold/experiment_results"
        ),
    )
    retention = BashOperator(
        task_id="retention_cleanup",
        bash_command="python -m src.maintenance.retention --keep 20",
    )

    ingest >> transform >> experiment >> retention
