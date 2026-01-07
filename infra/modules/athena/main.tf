resource "aws_athena_workgroup" "this" {
  name        = var.athena_workgroup_name
  description = "Athena workgroup for ${var.project}/${var.env}"
  state       = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.monitoring_bucket_name}/${trim(var.athena_results_prefix, "/")}/"
    }
  }

  tags = var.tags
}
