locals {
  name_prefix = "${var.project}-${var.env}"
}

# Ingest DLQ
resource "aws_sqs_queue" "ingest_dlq" {
  name = "${local.name_prefix}-ingest-dlq"
  tags = var.tags
}

# Ingest queue
resource "aws_sqs_queue" "ingest" {
  name                       = "${local.name_prefix}-ingest"
  visibility_timeout_seconds = var.lambda_ingest_timeout_sec * 2

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingest_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = var.tags
}

# Transform DLQ
resource "aws_sqs_queue" "transform_dlq" {
  name = "${local.name_prefix}-transform-dlq"
  tags = var.tags
}

# Transform queue
resource "aws_sqs_queue" "transform" {
  name                       = "${local.name_prefix}-transform"
  visibility_timeout_seconds = var.lambda_transform_timeout_sec * 2

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.transform_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = var.tags
}
