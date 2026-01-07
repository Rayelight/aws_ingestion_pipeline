output "gold_ctas_runner_lambda_name" {
  value = aws_lambda_function.runner.function_name
}

output "gold_ctas_runner_lambda_arn" {
  value = aws_lambda_function.runner.arn
}
