.PHONY: setup download etl experiment dashboard test lint clean

setup:
	python -m pip install -r requirements.txt

download:
	python -m src.ingestion.download_kaggle --dataset olistbr/brazilian-ecommerce --output data/raw

etl:
	python -m src.etl.spark_pipeline --input data/raw --output data/lakehouse --quality-report artifacts/data_quality_report.json

experiment:
	python -m src.analytics.experiment --fact-orders data/lakehouse/gold/fact_orders --output data/lakehouse/gold/experiment_results

dashboard:
	streamlit run src/dashboard/app.py -- --data-root data/lakehouse/gold

test:
	pytest -q

lint:
	ruff check .

clean:
	rm -rf data/lakehouse data/exports artifacts .pytest_cache .ruff_cache
