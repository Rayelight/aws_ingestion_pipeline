resource "aws_glue_catalog_database" "this" {
  name = var.glue_database_name

  tags = var.tags
}

resource "aws_iam_role" "crawler" {
  name = "${var.project}-${var.env}-glue-crawler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "crawler_glue_service" {
  role       = aws_iam_role.crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "crawler_s3_access" {
  name = "${var.project}-${var.env}-glue-crawler-s3"
  role = aws_iam_role.crawler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = ["arn:aws:s3:::${var.datalake_bucket_name}"]
        Condition = {
          StringLike = {
            "s3:prefix" = ["${trim(var.silver_s3_prefix, "/")}/*"]
          }
        }
      },
      {
        Sid      = "GetObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["arn:aws:s3:::${var.datalake_bucket_name}/${trim(var.silver_s3_prefix, "/")}/*"]
      }
    ]
  })
}

resource "aws_glue_crawler" "silver" {
  name          = "${var.project}-${var.env}-silver-crawler"
  role          = aws_iam_role.crawler.arn
  database_name = aws_glue_catalog_database.this.name
  table_prefix  = "silver_"

  s3_target {
    path = "s3://${var.datalake_bucket_name}/${trim(var.silver_s3_prefix, "/")}/"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
      Tables     = { AddOrUpdateBehavior = "MergeNewColumns" }
    }
  })

  schedule = var.crawler_schedule_expression

  tags = var.tags
}
