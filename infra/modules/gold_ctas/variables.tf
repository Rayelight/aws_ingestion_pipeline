variable "project" { type = string }
variable "env" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

variable "datalake_bucket_name" { type = string }
variable "monitoring_bucket_name" { type = string }

variable "glue_database_name" { type = string }    # ex: ingesteur_dev
variable "athena_workgroup_name" { type = string } # ex: ingesteur-dev

# Où tu mets tes SQL gold (dans S3)
variable "gold_sql_prefix" {
  type    = string
  default = "configs/gold/sql/"
}

# Où tu écris les tables gold
variable "gold_s3_prefix" {
  type    = string
  default = "data/gold/"
}

variable "lambda_runtime" {
  type    = string
  default = "python3.12"
}

variable "lambda_timeout" {
  type    = number
  default = 900
}

variable "lambda_memory_size" {
  type    = number
  default = 512
}

# Layers optionnelles si tu veux (boto3 suffit en général)
variable "lambda_layers" {
  type    = list(string)
  default = []
}
