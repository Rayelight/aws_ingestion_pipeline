locals {
  name_prefix = "${var.project}-${var.env}"
  rule_name   = "${local.name_prefix}-${var.rule_name_suffix}"
}

resource "aws_cloudwatch_event_rule" "this" {
  name                = local.rule_name
  schedule_expression = var.schedule_expression
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "to_sqs" {
  rule      = aws_cloudwatch_event_rule.this.name
  arn       = var.target_sqs_queue_arn
  target_id = "sqs-ingest"

  # input est un ATTRIBUT, pas un bloc
  input = var.default_message == null ? null : jsonencode(var.default_message)
}


# Autoriser EventBridge à pousser dans la queue SQS
data "aws_iam_policy_document" "sqs_allow_eventbridge" {
  statement {
    sid     = "AllowEventBridgeSendMessage"
    effect  = "Allow"
    actions = ["sqs:SendMessage"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    resources = [var.target_sqs_queue_arn]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.this.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "allow_eventbridge" {
  queue_url = var.target_sqs_queue_url
  policy    = data.aws_iam_policy_document.sqs_allow_eventbridge.json
}
