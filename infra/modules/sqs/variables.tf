variable "project" { type = string }
variable "env" { type = string }

variable "lambda_ingest_timeout_sec" {
  type    = number
  default = 60
}

variable "lambda_transform_timeout_sec" {
  type    = number
  default = 300
}

variable "max_receive_count" {
  type    = number
  default = 5
}

variable "tags" {
  type    = map(string)
  default = {}
}
