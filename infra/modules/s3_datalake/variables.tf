variable "project" { type = string }
variable "env" { type = string }

variable "bucket_name" {
  type        = string
  description = "Nom du bucket S3 data lake (globalement unique)"
}

variable "force_destroy" {
  type        = bool
  default     = false
  description = "Autorise la suppression du bucket même s'il contient des objets (utile en dev)"
}

variable "monitoring_bucket_name" {
  type        = string
  description = "Nom du bucket de monitoring qui recevra les access logs du datalake"
}

variable "access_logs_prefix" {
  type        = string
  default     = "s3-access/datalake/"
  description = "Préfixe dans le bucket monitoring pour stocker les access logs"
}

variable "tags" {
  type    = map(string)
  default = {}
}
