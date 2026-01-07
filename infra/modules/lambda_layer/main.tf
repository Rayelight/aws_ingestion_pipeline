locals {
  layer_name = "${var.project}-${var.env}-${var.name}"
  zip_path   = "${path.module}/layers/outputs/${var.name}.zip"
}

resource "aws_lambda_layer_version" "this" {
  layer_name          = local.layer_name
  filename            = local.zip_path
  source_code_hash    = filebase64sha256(local.zip_path)
  compatible_runtimes = ["python3.12"]
}
