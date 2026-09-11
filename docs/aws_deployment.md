# AWS deployment guide

## Services

- Amazon S3: raw, curated, scripts, and Athena result zones
- AWS Glue: managed Spark ETL, Data Catalog database, and crawler
- Amazon Athena: serverless SQL for BI clients
- Scheduled Glue trigger: weekly pipeline execution
- Tableau / Power BI: connect through Athena using the appropriate driver

## Deploy

```bash
cd aws/terraform
terraform init
terraform fmt -check
terraform plan
terraform apply
```

Upload the Kaggle CSV files to the Terraform output bucket under `raw/`, then start the Glue job. After a successful job, the conditional trigger runs the gold crawler so Athena can query the new tables.

## Suggested production improvements

- Use separate development and production accounts.
- Put Terraform state in an encrypted S3 backend with state locking.
- Use KMS customer-managed keys.
- Add CloudWatch alarms for Glue failures and data-quality metrics.
- Use AWS Secrets Manager for external API credentials.
- Add Lake Formation permissions for governed access.
