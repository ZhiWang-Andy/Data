resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  bucket_name = "${var.project_name}-${random_id.suffix.hex}"
}

resource "aws_s3_bucket" "lake" {
  bucket        = local.bucket_name
  force_destroy = false
  tags = {
    Project = var.project_name
    Layer   = "data-lake"
  }
}

resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "glue_script" {
  bucket = aws_s3_bucket.lake.id
  key    = "scripts/olist_etl_job.py"
  source = var.glue_script_local_path
  etag   = filemd5(var.glue_script_local_path)
}

resource "aws_glue_catalog_database" "analytics" {
  name = replace("${var.project_name}_db", "-", "_")
}

resource "aws_iam_role" "glue" {
  name = "${var.project_name}-glue-role-${random_id.suffix.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_lake" {
  role = aws_iam_role.glue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.lake.arn,
        "${aws_s3_bucket.lake.arn}/*"
      ]
    }]
  })
}

resource "aws_glue_job" "olist_etl" {
  name              = "${var.project_name}-etl"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.lake.id}/${aws_s3_object.glue_script.key}"
  }

  default_arguments = {
    "--job-language"        = "python"
    "--enable-metrics"      = "true"
    "--enable-job-insights" = "true"
    "--RAW_S3_URI"          = "s3://${aws_s3_bucket.lake.id}/raw"
    "--CURATED_S3_URI"      = "s3://${aws_s3_bucket.lake.id}/curated"
  }
}

resource "aws_glue_crawler" "gold" {
  database_name = aws_glue_catalog_database.analytics.name
  name          = "${var.project_name}-gold-crawler"
  role          = aws_iam_role.glue.arn

  s3_target {
    path = "s3://${aws_s3_bucket.lake.id}/curated/gold/"
  }
}

resource "aws_athena_workgroup" "analytics" {
  name = "${var.project_name}-workgroup"
  configuration {
    enforce_workgroup_configuration = true
    result_configuration {
      output_location = "s3://${aws_s3_bucket.lake.id}/athena-results/"
    }
  }
}

resource "aws_glue_trigger" "weekly" {
  name     = "${var.project_name}-weekly"
  type     = "SCHEDULED"
  schedule = "cron(0 7 ? * MON *)"
  actions {
    job_name = aws_glue_job.olist_etl.name
  }
}

resource "aws_glue_trigger" "catalog_after_etl" {
  name              = "${var.project_name}-catalog-after-etl"
  type              = "CONDITIONAL"
  start_on_creation = true

  predicate {
    conditions {
      job_name = aws_glue_job.olist_etl.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    crawler_name = aws_glue_crawler.gold.name
  }
}
