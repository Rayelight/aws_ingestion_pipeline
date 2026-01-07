output "ingest_queue_url" { value = aws_sqs_queue.ingest.url }
output "ingest_queue_arn" { value = aws_sqs_queue.ingest.arn }
output "ingest_queue_name" { value = aws_sqs_queue.ingest.name }

output "ingest_dlq_url" { value = aws_sqs_queue.ingest_dlq.url }
output "ingest_dlq_arn" { value = aws_sqs_queue.ingest_dlq.arn }
output "ingest_dlq_name" { value = aws_sqs_queue.ingest_dlq.name }

output "transform_queue_url" { value = aws_sqs_queue.transform.url }
output "transform_queue_arn" { value = aws_sqs_queue.transform.arn }
output "transform_queue_name" { value = aws_sqs_queue.transform.name }

output "transform_dlq_url" { value = aws_sqs_queue.transform_dlq.url }
output "transform_dlq_arn" { value = aws_sqs_queue.transform_dlq.arn }
output "transform_dlq_name" { value = aws_sqs_queue.transform_dlq.name }
