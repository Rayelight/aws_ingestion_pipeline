variable "project" { type = string }
variable "env" { type = string }

variable "bucket_name" {
  type        = string
  description = "Nom du bucket S3 de monitoring (doit être globalement unique)"
}

variable "force_destroy" {
  type        = bool
  default     = false
  description = "Autorise la suppression du bucket même s'il contient des objets (utile en dev)"
}

variable "tags" {
  type    = map(string)
  default = {}
}
