variable "project" { type = string }
variable "env" { type = string }

variable "schedule_expression" {
  type        = string
  description = "Expression EventBridge: rate(...) ou cron(...)"
}

variable "target_sqs_queue_arn" {
  type        = string
  description = "ARN de la queue SQS ingest"
}

variable "target_sqs_queue_url" {
  type        = string
  description = "URL de la queue SQS ingest (pour la queue policy)"
}

variable "rule_name_suffix" {
  type        = string
  default     = "ingest-schedule"
  description = "Suffixe du nom de la rule"
}

# Optionnel: payload par défaut envoyé à la queue
variable "default_message" {
  type        = any
  default     = null
  description = "Objet JSON encodé envoyé à SQS (ex: {source, entity, params...}). Si null, pas d'input."
}

variable "tags" {
  type    = map(string)
  default = {}
}
