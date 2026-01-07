#!/bin/bash

secret=$(aws secretsmanager get-secret-value \
  --secret-id aws_access_keys \
  --query SecretString \
  --output text)

export AWS_ACCESS_KEY_ID=$(echo "$secret" | jq -r .access_key)
export AWS_SECRET_ACCESS_KEY=$(echo "$secret" | jq -r .secret_key)

set -e  # Arrêter si erreur

TFVARS_FILE="terraform.tfvars"
LAMBDA_BUILD_SCRIPT="modules/lambda/package_lambda_new.py"
LAMBDA_LAYER_BUILD_LAYER_SCRIPT="modules/lambda_layer/build_layer_new.py"

echo "📦 Packaging Lambda function..."
python3 "$LAMBDA_BUILD_SCRIPT"

# To run only when packages are changed in DEPENDENCIES of package_lambda.py
# echo "📦 Packaging Lambda Layer..."
# python3 "$LAMBDA_LAYER_BUILD_LAYER_SCRIPT"

echo "🚀 Initialisation de Terraform..."
terraform init

echo "Format terraform files"
terraform fmt -recursive

echo "🔍 Planification..."
terraform plan -var-file="$TFVARS_FILE" -out=tfplan

echo "✅ Application du plan..."
terraform apply tfplan

echo "🎉 Déploiement terminé avec succès !"
