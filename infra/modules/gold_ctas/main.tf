data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  lambda_zip_path = "${path.module}/../lambda/functions/gold_ctas_runner/package/lambda.zip"
}

resource "aws_iam_role" "lambda" {
  name = "${var.project}-${var.env}-gold-ctas-runner"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "basic_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Permissions nécessaires :
# - lire le SQL stocké dans S3
# - écrire les outputs gold dans le datalake
# - démarrer et suivre une requête Athena
# - accéder au Glue Data Catalog (DB/tables) utilisé par Athena
resource "aws_iam_role_policy" "gold_ctas" {
  name = "${var.project}-${var.env}-gold-ctas"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Read SQL templates
      {
        Sid    = "ReadGoldSql"
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = [
          "arn:aws:s3:::${var.datalake_bucket_name}/${trim(var.gold_sql_prefix, "/")}/*"
        ]
      },
      # Write gold outputs (CTAS writes to S3 location inside the SQL)
      {
        Sid    = "WriteGold"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:AbortMultipartUpload", "s3:ListBucketMultipartUploads", "s3:ListMultipartUploadParts"]
        Resource = [
          "arn:aws:s3:::${var.datalake_bucket_name}/${trim(var.gold_s3_prefix, "/")}/*"
        ]
      },
      {
        Sid      = "ListGoldPrefix"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = ["arn:aws:s3:::${var.datalake_bucket_name}"]
        Condition = {
          StringLike = {
            "s3:prefix" = ["${trim(var.gold_s3_prefix, "/")}/*"]
          }
        }
      },
      # Athena execution
      {
        Sid    = "AthenaQueries"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution"
        ]
        Resource = ["*"]
      },
      # Glue Catalog read (Athena uses it)
      {
        Sid    = "GlueCatalogRead"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions"
        ]
        Resource = ["*"]
      }
    ]
  })
}

resource "aws_lambda_function" "runner" {
  function_name = "${var.project}-${var.env}-gold-ctas-runner"
  role          = aws_iam_role.lambda.arn

  runtime = var.lambda_runtime
  handler = "handler.lambda_handler"

  filename         = local.lambda_zip_path
  source_code_hash = filebase64sha256(local.lambda_zip_path)

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory_size

  layers = var.lambda_layers

  environment {
    variables = {
      PROJECT = var.project
      ENV     = var.env

      ATHENA_WORKGROUP   = var.athena_workgroup_name
      GLUE_DATABASE_NAME = var.glue_database_name

      DATALAKE_BUCKET = var.datalake_bucket_name
      GOLD_S3_PREFIX  = "${trim(var.gold_s3_prefix, "/")}/"

      GOLD_SQL_BUCKET = var.datalake_bucket_name
      GOLD_SQL_PREFIX = "${trim(var.gold_sql_prefix, "/")}/"

    }
  }

  tags = var.tags
}
