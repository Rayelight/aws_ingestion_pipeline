output "glue_database_name" {
  value = aws_glue_catalog_database.this.name
}

output "silver_crawler_name" {
  value = aws_glue_crawler.silver.name
}

output "crawler_role_arn" {
  value = aws_iam_role.crawler.arn
}

