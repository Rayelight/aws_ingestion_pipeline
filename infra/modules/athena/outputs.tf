output "workgroup_name" {
  value = aws_athena_workgroup.this.name
}

output "results_s3_location" {
  value = "s3://${var.monitoring_bucket_name}/${trim(var.athena_results_prefix, "/")}/"
}
