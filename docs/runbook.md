# Data operations runbook

## Routine checks

1. Confirm the raw ingestion timestamp and expected source-file count.
2. Review `artifacts/data_quality_report.json`.
3. Verify order-row reconciliation between source orders and `fact_orders`.
4. Check duplicate keys, negative monetary values, missing customer joins, and stale partitions.
5. Review Airflow or Glue job status and logs.
6. Validate the latest gold partition through Athena before dashboard refresh.

## Failure handling

### Missing source files

Do not publish new gold tables. Re-run Kaggle ingestion, confirm all expected CSVs, then restart the pipeline.

### Data contract failure

Quarantine the changed source file, compare columns and types with `config/data_contracts.yaml`, and update the contract only after business approval.

### Quality gate failure

Keep the previous gold version available. Investigate failed checks in the JSON report, fix upstream data or transformation logic, and rerun from silver.

### Dashboard discrepancy

Confirm table grain first. Revenue should aggregate from order-level payment value; seller revenue must use the seller mart to avoid multi-seller double counting.

## Recovery

- Local: rebuild outputs from immutable raw files.
- AWS: restore the previous S3 object version, then rerun Glue from the affected layer.
- Terraform: use remote state and state locking in a production account.

## Security

- Never commit Kaggle or AWS credentials.
- Use IAM roles and least-privilege bucket policies.
- Block public S3 access and enable server-side encryption and versioning.
