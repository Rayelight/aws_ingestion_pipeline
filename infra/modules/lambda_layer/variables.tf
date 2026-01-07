variable "project" { type = string }
variable "env" { type = string }

variable "name" {
  type        = string
  description = "Nom logique du layer (ex: pydeps)"
}

variable "tags" {
  type    = map(string)
  default = {}
}
