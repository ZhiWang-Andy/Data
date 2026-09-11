output "data_lake_bucket" {
  value = aws_s3_bucket.lake.id
}

output "glue_job_name" {
  value = aws_glue_job.olist_etl.name
}

output "glue_database_name" {
  value = aws_glue_catalog_database.analytics.name
}

output "athena_workgroup" {
  value = aws_athena_workgroup.analytics.name
}

output "gold_crawler_name" {
  value = aws_glue_crawler.gold.name
}
