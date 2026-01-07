output "ingest_function_name" { value = aws_lambda_function.ingest.function_name }
output "ingest_function_arn" { value = aws_lambda_function.ingest.arn }

output "transform_function_name" { value = aws_lambda_function.transform.function_name }
output "transform_function_arn" { value = aws_lambda_function.transform.arn }
