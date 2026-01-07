variable "project" { type = string }
variable "env" { type = string }

variable "table_name" {
  type        = string
  description = "Nom de la table DynamoDB"
}

variable "tags" {
  type    = map(string)
  default = {}
}
