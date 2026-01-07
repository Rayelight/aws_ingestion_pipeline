variable "project" { type = string }
variable "env" { type = string }
variable "region" { type = string }

# s3 monitoring variables
variable "monitoring_bucket_name" {
  type = string
}
variable "monitoring_force_destroy" {
  type    = bool
  default = false
}

# s3 datalake variables
variable "datalake_bucket_name" {
  type = string
}
variable "datalake_force_destroy" {
  type    = bool
  default = false
}

# sqs variables
variable "lambda_ingest_timeout_sec" {
  type    = number
  default = 60
}
variable "lambda_transform_timeout_sec" {
  type    = number
  default = 300
}
variable "sqs_max_receive_count" {
  type    = number
  default = 5
}

# event bridge ingest scheduler
variable "ingest_schedule_expression" {
  type        = string
  default     = "rate(1 hour)"
  description = "Fréquence d’envoi des requêtes d’ingestion vers SQS"
}

variable "ingest_default_message" {
  type        = any
  default     = null
  description = "Payload par défaut envoyé à la queue ingest (JSON)."
}

# lambdas variables
variable "use_layer" {
  type    = bool
  default = true
}

variable "lambda_layers_list" {
  type = list(string)
}

variable "log_retention_days" {
  type    = number
  default = 30
}

# dynamo db varibales
variable "tracking_table_name" {
  type        = string
  default     = null
  description = "Si null, on génère un nom par défaut <project>-<env>-ingestion-runs"
}


# tags
variable "tags" {
  type    = map(string)
  default = {}
}

