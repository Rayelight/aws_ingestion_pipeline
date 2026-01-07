locals {
  name_prefix = "${var.project}-${var.env}"
}

# ----------------------------
# Assume role policies
# ----------------------------
data "aws_iam_policy_document" "assume_lambda" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "assume_glue" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

# ----------------------------
# Roles
# ----------------------------
resource "aws_iam_role" "lambda_ingest" {
  name               = "${local.name_prefix}-lambda-ingest-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
  tags               = var.tags
}

resource "aws_iam_role" "lambda_transform" {
  name               = "${local.name_prefix}-lambda-transform-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
  tags               = var.tags
}

resource "aws_iam_role" "glue" {
  name               = "${local.name_prefix}-glue-role"
  assume_role_policy = data.aws_iam_policy_document.assume_glue.json
  tags               = var.tags
}

# ----------------------------
# Common Lambda Logs policy
# ----------------------------
data "aws_iam_policy_document" "lambda_logs" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda_logs" {
  name   = "${local.name_prefix}-lambda-logs"
  policy = data.aws_iam_policy_document.lambda_logs.json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_ingest_logs" {
  role       = aws_iam_role.lambda_ingest.name
  policy_arn = aws_iam_policy.lambda_logs.arn
}

resource "aws_iam_role_policy_attachment" "lambda_transform_logs" {
  role       = aws_iam_role.lambda_transform.name
  policy_arn = aws_iam_policy.lambda_logs.arn
}

# ----------------------------
# DynamoDB tracking permissions (shared)
# ----------------------------
data "aws_iam_policy_document" "tracking" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem"
    ]
    resources = [var.ingestion_tracking_table_arn]
  }
}

resource "aws_iam_policy" "tracking" {
  name   = "${local.name_prefix}-ingestion-tracking"
  policy = data.aws_iam_policy_document.tracking.json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_ingest_tracking" {
  role       = aws_iam_role.lambda_ingest.name
  policy_arn = aws_iam_policy.tracking.arn
}

resource "aws_iam_role_policy_attachment" "lambda_transform_tracking" {
  role       = aws_iam_role.lambda_transform.name
  policy_arn = aws_iam_policy.tracking.arn
}

# ----------------------------
# Lambda INGEST permissions
# ----------------------------
data "aws_iam_policy_document" "lambda_ingest" {
  # Consume from ingest queue
  statement {
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility"
    ]
    resources = [var.sqs_ingest_queue_arn]
  }

  # Send to transform queue
  statement {
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [var.sqs_transform_queue_arn]
  }

  # Read contracts + schema from datalake configs
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${var.datalake_bucket_arn}/${var.configs_contracts_prefix}*",
      "${var.datalake_bucket_arn}/${var.configs_schema_prefix}*"
    ]
  }

  # Write bronze in datalake
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:AbortMultipartUpload",
      "s3:ListBucketMultipartUploads",
      "s3:ListMultipartUploadParts"
    ]
    resources = [
      "${var.datalake_bucket_arn}/${var.bronze_prefix}*"
    ]
  }

  # ListBucket for relevant prefixes (optional but helps)
  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.datalake_bucket_arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        "${var.configs_contracts_prefix}*",
        "${var.configs_schema_prefix}*",
        "${var.bronze_prefix}*"
      ]
    }
  }
}

resource "aws_iam_policy" "lambda_ingest" {
  name   = "${local.name_prefix}-lambda-ingest"
  policy = data.aws_iam_policy_document.lambda_ingest.json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_ingest_attach" {
  role       = aws_iam_role.lambda_ingest.name
  policy_arn = aws_iam_policy.lambda_ingest.arn
}

# ----------------------------
# Lambda TRANSFORM permissions
# ----------------------------
data "aws_iam_policy_document" "lambda_transform" {
  # Consume from transform queue
  statement {
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility"
    ]
    resources = [var.sqs_transform_queue_arn]
  }

  # Read schema from datalake configs
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${var.datalake_bucket_arn}/${var.configs_schema_prefix}*"
    ]
  }

  # Read bronze
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${var.datalake_bucket_arn}/${var.bronze_prefix}*"
    ]
  }

  # Write silver
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:AbortMultipartUpload",
      "s3:ListBucketMultipartUploads",
      "s3:ListMultipartUploadParts"
    ]
    resources = [
      "${var.datalake_bucket_arn}/${var.silver_prefix}*"
    ]
  }

  # ListBucket relevant prefixes
  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.datalake_bucket_arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        "${var.configs_schema_prefix}*",
        "${var.bronze_prefix}*",
        "${var.silver_prefix}*"
      ]
    }
  }
}

resource "aws_iam_policy" "lambda_transform" {
  name   = "${local.name_prefix}-lambda-transform"
  policy = data.aws_iam_policy_document.lambda_transform.json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_transform_attach" {
  role       = aws_iam_role.lambda_transform.name
  policy_arn = aws_iam_policy.lambda_transform.arn
}

# ----------------------------
# Glue permissions (silver->gold later)
# (adapted to data/silver + data/gold)
# ----------------------------
data "aws_iam_policy_document" "glue" {
  # Read silver + write gold
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload",
      "s3:ListBucketMultipartUploads",
      "s3:ListMultipartUploadParts"
    ]
    resources = [
      "${var.datalake_bucket_arn}/${var.silver_prefix}*",
      "${var.datalake_bucket_arn}/${var.gold_prefix}*"
    ]
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.datalake_bucket_arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${var.silver_prefix}*", "${var.gold_prefix}*"]
    }
  }

  # Temp/logs/results in monitoring bucket
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload",
      "s3:ListBucket"
    ]
    resources = [
      var.monitoring_bucket_arn,
      "${var.monitoring_bucket_arn}/*"
    ]
  }

  # Glue Catalog (broad for now)
  statement {
    effect = "Allow"
    actions = [
      "glue:*Database*",
      "glue:*Table*",
      "glue:*Partition*",
      "glue:GetCrawler",
      "glue:StartCrawler",
      "glue:GetCrawlers",
      "glue:UpdateCrawler"
    ]
    resources = ["*"]
  }

  # CloudWatch logs for Glue
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "glue" {
  name   = "${local.name_prefix}-glue"
  policy = data.aws_iam_policy_document.glue.json
  tags   = var.tags
}

resource "aws_iam_role_policy_attachment" "glue_attach" {
  role       = aws_iam_role.glue.name
  policy_arn = aws_iam_policy.glue.arn
}
