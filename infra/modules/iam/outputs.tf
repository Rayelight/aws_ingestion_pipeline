output "lambda_ingest_role_arn" { value = aws_iam_role.lambda_ingest.arn }
output "lambda_transform_role_arn" { value = aws_iam_role.lambda_transform.arn }
output "glue_role_arn" { value = aws_iam_role.glue.arn }

output "lambda_ingest_role_name" { value = aws_iam_role.lambda_ingest.name }
output "lambda_transform_role_name" { value = aws_iam_role.lambda_transform.name }
output "glue_role_name" { value = aws_iam_role.glue.name }
