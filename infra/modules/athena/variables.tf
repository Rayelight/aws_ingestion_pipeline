variable "project" { type = string }
variable "env" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

variable "monitoring_bucket_name" { type = string }

variable "athena_workgroup_name" {
  type = string
  # ex: ingesteur-dev
}

variable "athena_results_prefix" {
  type    = string
  default = "athena-results/"
}
