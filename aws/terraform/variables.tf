variable "aws_region" {
  type        = string
  description = "AWS region for the analytics platform"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Prefix for AWS resources"
  default     = "olist-analytics"
}

variable "glue_script_local_path" {
  type        = string
  description = "Local path to the Glue PySpark entrypoint"
  default     = "../glue/olist_etl_job.py"
}
