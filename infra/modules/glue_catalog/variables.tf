variable "project" { type = string }
variable "env" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

variable "datalake_bucket_name" { type = string }

variable "silver_s3_prefix" {
  type    = string
  default = "data/silver/"
}

variable "glue_database_name" {
  type = string
  # ex: ingesteur_dev
}

variable "crawler_schedule_expression" {
  type    = string
  default = null
  # ex: "cron(0 * * * ? *)" si tu veux hourly plus tard
}

variable "enable_eventbridge_crawler_trigger" {
  type    = bool
  default = false
}

variable "eventbridge_crawler_schedule_expression" {
  type    = string
  default = null
  # ex: "rate(15 minutes)" ou "cron(0 * * * ? *)"
}

